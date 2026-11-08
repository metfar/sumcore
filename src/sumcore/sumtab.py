#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018-2026 William Martinez Bas <metfar@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  

"""Dependency-free codec for SUMTAB, the native SUM tabular interchange format.

SUMTAB stays deliberately simple enough to implement in sumBASIC. A fixed
ASCII bootstrap line declares the one-byte field separator (FS) and record
separator (RS), after which META, FIELD, INDEX and DATA records use those
separators directly. The human-friendly default is ``|`` between fields and
LF between records, while raw streams can use ASCII US (0x1F) and RS (0x1E),
NUL, or another ASCII byte. A tiny escape set preserves backslashes, control
characters and separator bytes. The unescaped token \\N means NULL.

Readers also accept the earlier SUMTAB/1 framing ``SUMTAB<FS>1\\n`` so files
written before configurable record separators remain readable.
""";

from dataclasses import dataclass, field;
from datetime import date, datetime, time;
from decimal import Decimal;
from pathlib import Path;
import json;
import math;
import uuid;

try:
    from sumcore.schema import SUMTAB_FORMAT, canonical_type;
except ModuleNotFoundError as exc:
    if exc.name == "sumcore.schema":
        raise ImportError(
            "SUMTAB requires sumcore>=0.1.0a22; the installed sumCore is older "
            "and does not provide sumcore.schema."
        ) from exc;
    raise;


MAGIC = "SUMTAB";
VERSION = "1";
NULL_TOKEN = r"\N";
DEFAULT_FIELD_SEPARATOR = "|";
DEFAULT_RECORD_SEPARATOR = "\n";
DEFAULT_SEPARATOR = DEFAULT_FIELD_SEPARATOR;

_SEPARATOR_ALIASES = {
    "pipe": "|",
    "bar": "|",
    "vertical-bar": "|",
    "tab": "\t",
    "comma": ",",
    "semicolon": ";",
    "semi-colon": ";",
    "colon": ":",
    "space": " ",
    "nul": "\x00",
    "null": "\x00",
    "lf": "\n",
    "newline": "\n",
    "cr": "\r",
    "rs": "\x1e",
    "record-separator": "\x1e",
    "us": "\x1f",
    "unit-separator": "\x1f",
};


def _separator_value(separator: str | None, default: str) -> str:
    if separator is None:
        return (default);
    source = str(separator);
    stripped = source.strip();
    alias = _SEPARATOR_ALIASES.get(stripped.lower());
    if alias is not None:
        return (alias);
    lower = stripped.lower();
    if (lower.startswith("0x") or lower.startswith("\\x")) and len(lower) == 4:
        try:
            return (chr(int(lower[2:], 16)));
        except ValueError:
            pass;
    return (source);


def normalize_separator(separator: str | None) -> str:
    """Return one valid SUMTAB field separator byte as a one-character str.""";
    value = _separator_value(separator, DEFAULT_FIELD_SEPARATOR);
    if len(value) != 1:
        raise ValueError(
            "SUMTAB field separator must be one ASCII byte, 0xNN, or a named alias."
        );
    if ord(value) > 0x7F:
        raise ValueError("SUMTAB separators must be ASCII bytes (0x00..0x7F).");
    if value == "\\":
        raise ValueError("Backslash cannot be a SUMTAB separator because it introduces escapes.");
    return (value);


def normalize_record_separator(separator: str | None) -> str:
    """Return one valid SUMTAB record separator byte as a one-character str.""";
    value = _separator_value(separator, DEFAULT_RECORD_SEPARATOR);
    if len(value) != 1:
        raise ValueError(
            "SUMTAB record separator must be one ASCII byte, 0xNN, or a named alias."
        );
    if ord(value) > 0x7F:
        raise ValueError("SUMTAB separators must be ASCII bytes (0x00..0x7F).");
    if value == "\\":
        raise ValueError("Backslash cannot be a SUMTAB separator because it introduces escapes.");
    return (value);


def _validate_separator_pair(field_separator: str, record_separator: str) -> None:
    if field_separator == record_separator:
        raise ValueError("SUMTAB field and record separators must be different bytes.");


def separator_name(separator: str) -> str:
    value = normalize_separator(separator);
    names = {
        "|": "PIPE", "\t": "TAB", ",": "COMMA", ";": "SEMICOLON", ":": "COLON",
        " ": "SPACE", "\x00": "NUL", "\n": "LF", "\r": "CR", "\x1e": "RS", "\x1f": "US",
    };
    return (names.get(value, "0x{:02X}".format(ord(value))));


def record_separator_name(separator: str) -> str:
    value = normalize_record_separator(separator);
    return (separator_name(value));


def _separator_from_legacy_header(header: str) -> str:
    if not header.startswith(MAGIC) or not header.endswith(VERSION):
        raise ValueError("Not a SUMTAB document.");
    separator = header[len(MAGIC):len(header) - len(VERSION)];
    if len(separator) != 1:
        raise ValueError("Invalid SUMTAB header separator.");
    return (normalize_separator(separator));


def _bootstrap(field_separator: str, record_separator: str) -> str:
    return (f"{MAGIC}{VERSION} FS={ord(field_separator):02X} RS={ord(record_separator):02X}\n");


def _parse_bootstrap(text: str) -> tuple[str, str, str] | None:
    newline = text.find("\n");
    if newline < 0:
        return (None);
    header = text[:newline];
    if not header.startswith(f"{MAGIC}{VERSION} FS="):
        return (None);
    parts = header.split();
    if len(parts) != 3 or parts[0] != f"{MAGIC}{VERSION}":
        raise ValueError("Invalid SUMTAB bootstrap header.");
    values = {};
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError("Invalid SUMTAB bootstrap header.");
        key, raw = part.split("=", 1);
        if len(raw) != 2:
            raise ValueError("Invalid SUMTAB separator byte in bootstrap header.");
        try:
            values[key] = chr(int(raw, 16));
        except ValueError as exc:
            raise ValueError("Invalid SUMTAB separator byte in bootstrap header.") from exc;
    if "FS" not in values or "RS" not in values:
        raise ValueError("SUMTAB bootstrap header must declare FS and RS.");
    field_separator = normalize_separator(values["FS"]);
    record_separator = normalize_record_separator(values["RS"]);
    _validate_separator_pair(field_separator, record_separator);
    return (field_separator, record_separator, text[newline + 1:]);


@dataclass(frozen=True)
class SumColumn:
    name: str;
    logical_type: str = "TEXT";
    declared_type: str | None = None;
    length: int | None = None;
    precision: int | None = None;
    scale: int | None = None;
    nullable: bool = True;
    primary_key: bool = False;
    unique: bool = False;
    autoinum: bool = False;
    default: str | None = None;
    references: str | None = None;

    def __post_init__(self):
        object.__setattr__(self, "logical_type", canonical_type(self.logical_type));
        if self.declared_type is None:
            object.__setattr__(self, "declared_type", self.logical_type);


@dataclass(frozen=True)
class SumIndex:
    """Portable index definition, not a copy of a native index file.""";

    name: str;
    columns: tuple[str, ...] = ();
    unique: bool = False;
    expression: str | None = None;
    origin: str = "user";


@dataclass
class SumTable:
    columns: list[SumColumn];
    rows: list[tuple[object, ...]] = field(default_factory=list);
    indexes: list[SumIndex] = field(default_factory=list);
    metadata: dict[str, str] = field(default_factory=dict);

    def __post_init__(self):
        width = len(self.columns);
        for row in self.rows:
            if len(row) != width:
                raise ValueError(
                    "SUMTAB row has {} values but schema has {} columns.".format(
                        len(row), width
                    )
                );

    @property
    def column_names(self) -> tuple[str, ...]:
        return (tuple(column.name for column in self.columns));


def _escape(
    text: object,
    separator: str = DEFAULT_FIELD_SEPARATOR,
    record_separator: str = DEFAULT_RECORD_SEPARATOR,
) -> str:
    separator = normalize_separator(separator);
    record_separator = normalize_record_separator(record_separator);
    _validate_separator_pair(separator, record_separator);
    out = [];
    for char in str(text):
        if char == "\\":
            out.append("\\\\");
        elif char == "\t":
            out.append("\\t");
        elif char == "\n":
            out.append("\\n");
        elif char == "\r":
            out.append("\\r");
        elif char == separator or char == record_separator:
            out.append("\\x{:02X}".format(ord(char)));
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append("\\x{:02X}".format(ord(char)));
        else:
            out.append(char);
    return ("".join(out));


def _unescape(text: str) -> str:
    out = [];
    index = 0;
    while index < len(text):
        char = text[index];
        if char != "\\" or index + 1 >= len(text):
            out.append(char);
            index += 1;
            continue;
        code = text[index + 1];
        if code == "\\":
            out.append("\\");
            index += 2;
            continue;
        if code == "t":
            out.append("\t");
            index += 2;
            continue;
        if code == "n":
            out.append("\n");
            index += 2;
            continue;
        if code == "r":
            out.append("\r");
            index += 2;
            continue;
        if code == "x" and index + 3 < len(text):
            raw = text[index + 2:index + 4];
            try:
                out.append(chr(int(raw, 16)));
                index += 4;
                continue;
            except ValueError:
                pass;
        # Forward-compatible rule: an unknown escape keeps the slash.
        out.append("\\");
        out.append(code);
        index += 2;
    return ("".join(out));


def _optional_int(value: str) -> int | None:
    return (None if value == "" else int(value));


def _bool_field(value: str) -> bool:
    return (value == "1");


def _serialize_value(
    value: object,
    column: SumColumn,
    separator: str = DEFAULT_FIELD_SEPARATOR,
    record_separator: str = DEFAULT_RECORD_SEPARATOR,
) -> str:
    if value is None:
        return (NULL_TOKEN);
    logical = column.logical_type;
    if logical == "LOGICAL":
        return ("TRUE" if bool(value) else "FALSE");
    if logical == "BLOB":
        if isinstance(value, memoryview):
            value = value.tobytes();
        if isinstance(value, bytearray):
            value = bytes(value);
        if not isinstance(value, bytes):
            raise TypeError("BLOB column '{}' expects bytes.".format(column.name));
        return (value.hex().upper());
    if logical == "DATE" and isinstance(value, date) and not isinstance(value, datetime):
        return (value.isoformat());
    if logical == "TIME" and isinstance(value, time):
        return (value.isoformat());
    if logical == "DATETIME" and isinstance(value, datetime):
        return (value.isoformat());
    if logical == "NUMERIC":
        number = value if isinstance(value, Decimal) else Decimal(str(value));
        if column.scale is not None:
            return (format(number, ".{}f".format(int(column.scale))));
        return (format(number, "f"));
    if logical == "FLOAT" and isinstance(value, float):
        if math.isnan(value):
            return ("NaN");
        if math.isinf(value):
            return ("Infinity" if value > 0 else "-Infinity");
        return (repr(value));
    if logical == "UUID" and isinstance(value, uuid.UUID):
        return (str(value));
    if logical in ("JSON", "ARRAY", "LIST", "DICT", "SET", "TUPLE", "OBJECT"):
        if not isinstance(value, str):
            if isinstance(value, set):
                value = sorted(value, key=repr);
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"));
    return (_escape(value, separator, record_separator));


def _parse_value(token: str, column: SumColumn) -> object:
    if token == NULL_TOKEN:
        return (None);
    logical = column.logical_type;
    text = _unescape(token);
    if logical == "INTEGER":
        return (int(text));
    if logical == "NUMERIC":
        return (Decimal(text));
    if logical == "FLOAT":
        return (float(text));
    if logical == "LOGICAL":
        upper = text.strip().upper();
        if upper in ("TRUE", "T", "YES", "Y", "1"):
            return (True);
        if upper in ("FALSE", "F", "NO", "N", "0"):
            return (False);
        raise ValueError("Invalid LOGICAL value {!r}.".format(text));
    if logical == "DATE":
        return (date.fromisoformat(text));
    if logical == "TIME":
        return (time.fromisoformat(text));
    if logical == "DATETIME":
        return (datetime.fromisoformat(text));
    if logical == "BLOB":
        return (bytes.fromhex(text));
    if logical == "UUID":
        return (uuid.UUID(text));
    if logical in ("JSON", "ARRAY", "LIST", "DICT", "SET", "TUPLE", "OBJECT"):
        try:
            value = json.loads(text);
            if logical == "SET" and isinstance(value, list):
                return (set(value));
            if logical == "TUPLE" and isinstance(value, list):
                return (tuple(value));
            return (value);
        except json.JSONDecodeError:
            return (text);
    return (text);


def dumps(
    table: SumTable,
    separator: str = DEFAULT_FIELD_SEPARATOR,
    record_separator: str = DEFAULT_RECORD_SEPARATOR,
) -> str:
    separator = normalize_separator(separator);
    record_separator = normalize_record_separator(record_separator);
    _validate_separator_pair(separator, record_separator);
    records = [];
    metadata = {str(key): str(value) for key, value in table.metadata.items()};
    metadata.update({
        "schema": SUMTAB_FORMAT,
        "encoding": "UTF-8",
        "separator": separator_name(separator),
        "field_separator": separator_name(separator),
        "record_separator": record_separator_name(record_separator),
        "null": NULL_TOKEN,
    });
    for key, value in metadata.items():
        records.append(separator.join((
            "META",
            _escape(key, separator, record_separator),
            _escape(value, separator, record_separator),
        )));
    for column in table.columns:
        records.append(separator.join((
            "FIELD",
            _escape(column.name, separator, record_separator),
            _escape(column.logical_type, separator, record_separator),
            _escape(column.declared_type or column.logical_type, separator, record_separator),
            "" if column.length is None else str(column.length),
            "" if column.precision is None else str(column.precision),
            "" if column.scale is None else str(column.scale),
            "1" if column.nullable else "0",
            "1" if column.primary_key else "0",
            "1" if column.unique else "0",
            "1" if column.autoinum else "0",
            "" if column.default is None else _escape(column.default, separator, record_separator),
            "" if column.references is None else _escape(column.references, separator, record_separator),
        )));
    for index in table.indexes:
        fields = [
            "INDEX",
            _escape(index.name, separator, record_separator),
            "1" if index.unique else "0",
            _escape(index.origin, separator, record_separator),
            "" if index.expression is None else _escape(index.expression, separator, record_separator),
        ];
        fields.extend(_escape(column, separator, record_separator) for column in index.columns);
        records.append(separator.join(fields));
    records.append("DATA");
    for row in table.rows:
        records.append(separator.join(
            _serialize_value(value, column, separator, record_separator)
            for value, column in zip(row, table.columns)
        ));
    return (_bootstrap(separator, record_separator) + record_separator.join(records) + record_separator);


def loads(
    text: str,
    separator: str | None = None,
    record_separator: str | None = None,
) -> SumTable:
    if not text:
        raise ValueError("Empty SUMTAB document.");
    bootstrap = _parse_bootstrap(text);
    if bootstrap is not None:
        detected, detected_record_separator, payload = bootstrap;
        records = payload.split(detected_record_separator);
        if records and records[-1] == "":
            records.pop();
        first_record_number = 1;
    else:
        # Legacy SUMTAB/1: SUMTAB<FS>1 followed by LF-delimited records.
        header, marker, payload = text.partition("\n");
        if not marker:
            raise ValueError("Not a SUMTAB document.");
        detected = _separator_from_legacy_header(header);
        detected_record_separator = "\n";
        records = payload.split("\n");
        if records and records[-1] == "":
            records.pop();
        first_record_number = 2;
    if separator is None:
        separator = detected;
    else:
        separator = normalize_separator(separator);
        if separator != detected:
            raise ValueError(
                "SUMTAB separator mismatch: header uses {!r}, caller requested {!r}.".format(
                    detected, separator
                )
            );
    if record_separator is None:
        record_separator = detected_record_separator;
    else:
        record_separator = normalize_record_separator(record_separator);
        if record_separator != detected_record_separator:
            raise ValueError(
                "SUMTAB record separator mismatch: header uses {!r}, caller requested {!r}.".format(
                    detected_record_separator, record_separator
                )
            );
    _validate_separator_pair(separator, record_separator);
    columns = [];
    indexes = [];
    metadata = {};
    rows = [];
    in_data = False;
    for line_number, line in enumerate(records, start=first_record_number):
        if not in_data:
            if line == "DATA":
                in_data = True;
                continue;
            if not line:
                continue;
            parts = line.split(separator);
            kind = parts[0];
            if kind == "META":
                if len(parts) != 3:
                    raise ValueError("Invalid META record at line {}.".format(line_number));
                metadata[_unescape(parts[1])] = _unescape(parts[2]);
                continue;
            if kind == "FIELD":
                if len(parts) != 13:
                    raise ValueError("Invalid FIELD record at line {}.".format(line_number));
                columns.append(SumColumn(
                    name=_unescape(parts[1]),
                    logical_type=_unescape(parts[2]),
                    declared_type=_unescape(parts[3]) or None,
                    length=_optional_int(parts[4]),
                    precision=_optional_int(parts[5]),
                    scale=_optional_int(parts[6]),
                    nullable=_bool_field(parts[7]),
                    primary_key=_bool_field(parts[8]),
                    unique=_bool_field(parts[9]),
                    autoinum=_bool_field(parts[10]),
                    default=None if parts[11] == "" else _unescape(parts[11]),
                    references=None if parts[12] == "" else _unescape(parts[12]),
                ));
                continue;
            if kind == "INDEX":
                if len(parts) < 5:
                    raise ValueError("Invalid INDEX record at line {}.".format(line_number));
                indexes.append(SumIndex(
                    name=_unescape(parts[1]),
                    unique=_bool_field(parts[2]),
                    origin=_unescape(parts[3]) or "user",
                    expression=None if parts[4] == "" else _unescape(parts[4]),
                    columns=tuple(_unescape(value) for value in parts[5:]),
                ));
                continue;
            raise ValueError("Unknown SUMTAB record {!r} at line {}.".format(kind, line_number));
        if not columns and line:
            raise ValueError("SUMTAB DATA section has no FIELD definitions.");
        parts = line.split(separator);
        if len(parts) != len(columns):
            raise ValueError(
                "SUMTAB data row at line {} has {} fields; expected {}.".format(
                    line_number, len(parts), len(columns)
                )
            );
        rows.append(tuple(_parse_value(token, column) for token, column in zip(parts, columns)));
    if not in_data:
        raise ValueError("SUMTAB document has no DATA section.");
    metadata["separator"] = separator_name(separator);
    metadata["field_separator"] = separator_name(separator);
    metadata["record_separator"] = record_separator_name(record_separator);
    return (SumTable(columns=columns, rows=rows, indexes=indexes, metadata=metadata));


def write_sumtab(
    table: SumTable,
    path: str | Path,
    separator: str = DEFAULT_FIELD_SEPARATOR,
    record_separator: str = DEFAULT_RECORD_SEPARATOR,
) -> Path:
    target = Path(path).expanduser().resolve();
    target.parent.mkdir(parents=True, exist_ok=True);
    target.write_bytes(
        dumps(table, separator=separator, record_separator=record_separator).encode("utf-8")
    );
    return (target);


def read_sumtab(
    path: str | Path,
    separator: str | None = None,
    record_separator: str | None = None,
) -> SumTable:
    source = Path(path).expanduser().resolve();
    return (loads(
        source.read_bytes().decode("utf-8"),
        separator=separator,
        record_separator=record_separator,
    ));


__all__ = [
    "MAGIC",
    "VERSION",
    "NULL_TOKEN",
    "DEFAULT_FIELD_SEPARATOR",
    "DEFAULT_RECORD_SEPARATOR",
    "DEFAULT_SEPARATOR",
    "normalize_separator",
    "normalize_record_separator",
    "separator_name",
    "record_separator_name",
    "SumColumn",
    "SumIndex",
    "SumTable",
    "dumps",
    "loads",
    "read_sumtab",
    "write_sumtab",
];
