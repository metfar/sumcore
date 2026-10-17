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

"""Authoritative SUM scalar/schema vocabulary shared by language runtimes and formats.""";

SUM_TYPE_SYSTEM = "sum.types/1";
SUM_SCHEMA_SYSTEM = "sum.schema/1";
SUM_INDEX_SYSTEM = "sum.indexes/1";
SUMTAB_FORMAT = "sumtab/1";

# These are logical interchange types, not storage-engine declarations.
SUM_SCALAR_TYPES = (
    "INTEGER",
    "NUMERIC",
    "FLOAT",
    "CHARACTER",
    "VARCHAR",
    "MEMO",
    "TEXT",
    "LOGICAL",
    "DATE",
    "TIME",
    "DATETIME",
    "BLOB",
    "UUID",
    "JSON",
    "COMPLEX",
);

# Structured value types are valid SUM values but are not required by the
# SUMTAB Core reader.  They are registered here so languages do not become
# competing authorities for the common type vocabulary.
SUM_STRUCTURED_TYPES = (
    "ARRAY",
    "LIST",
    "DICT",
    "SET",
    "TUPLE",
    "OBJECT",
);

TYPE_ALIASES = {
    "INT": "INTEGER",
    "I": "INTEGER",
    "LONG": "INTEGER",
    "AUTONUM": "INTEGER",
    "AUTOINCREMENT": "INTEGER",
    "IDENTITY": "INTEGER",
    "SERIAL": "INTEGER",
    "NUMBER": "NUMERIC",
    "DECIMAL": "NUMERIC",
    "N": "NUMERIC",
    "CURRENCY": "NUMERIC",
    "MONEY": "NUMERIC",
    "REAL": "FLOAT",
    "DOUBLE": "FLOAT",
    "SINGLE": "FLOAT",
    "F": "FLOAT",
    "CHAR": "CHARACTER",
    "C": "CHARACTER",
    "STRING": "VARCHAR",
    "STR": "VARCHAR",
    "M": "MEMO",
    "BOOL": "LOGICAL",
    "BOOLEAN": "LOGICAL",
    "L": "LOGICAL",
    "TIMESTAMP": "DATETIME",
    "BINARY": "BLOB",
    "BYTE": "BLOB",
    "BYTES": "BLOB",
    "GENERAL": "BLOB",
    "G": "BLOB",
    "OBJ": "OBJECT",
};


def canonical_type(type_name: str) -> str:
    """Return the canonical SUM logical type name for a declaration or alias.""";
    source = str(type_name or "").strip().upper();
    if not source:
        return ("TEXT");
    base = source.split("(", 1)[0].strip();
    canonical = TYPE_ALIASES.get(base, base);
    if canonical not in SUM_SCALAR_TYPES and canonical not in SUM_STRUCTURED_TYPES:
        return ("TEXT");
    return (canonical);


def is_sum_type(type_name: str) -> bool:
    canonical = canonical_type(type_name);
    return (canonical in SUM_SCALAR_TYPES or canonical in SUM_STRUCTURED_TYPES);


__all__ = [
    "SUM_TYPE_SYSTEM",
    "SUM_SCHEMA_SYSTEM",
    "SUM_INDEX_SYSTEM",
    "SUMTAB_FORMAT",
    "SUM_SCALAR_TYPES",
    "SUM_STRUCTURED_TYPES",
    "TYPE_ALIASES",
    "canonical_type",
    "is_sum_type",
];
