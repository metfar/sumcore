#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018- William Martinez Bas <metfar@gmail.com>
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
#
#import warnings;
#warnings.filterwarnings("ignore", category=UserWarning);
from dataclasses import dataclass;
from datetime import date, datetime, time;
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP;
import re;


class PictureError(ValueError):
    pass;


@dataclass(frozen=True)
class PictureSpec:
    source: str;
    functions: frozenset;
    mask: str;
    choices: tuple = ();

    @property
    def uppercase(self):
        return "!" in self.functions;

    @property
    def blank_zero(self):
        return "Z" in self.functions;

    @property
    def remove_literals(self):
        return "R" in self.functions;

    @property
    def clear_on_edit(self):
        return "K" in self.functions;


_PICTURE_FUNCTIONS = frozenset("!ZCX(EBRKGTM");
_EDITABLE = frozenset("ANX!9#YL");


def parse_picture(picture):
    source = str(picture or "").strip();
    rest = source;
    functions = [];
    choices = ();
    while rest.startswith("@"): 
        match = re.match(r"^@([!ZCX(EBRKGTM])(?:\s+|$)", rest, flags=re.I);
        if not match:
            break;
        function = match.group(1).upper();
        functions.append(function);
        rest = rest[match.end():].lstrip();
        if function == "M":
            choices = tuple(item.strip() for item in rest.replace("|", ",").split(",") if item.strip() != "");
            rest = "";
            break;
    return PictureSpec(source, frozenset(functions), rest, choices);


def picture_capacity(picture):
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    if spec.choices:
        return max(1, max(len(item) for item in spec.choices));
    return sum(1 for char in spec.mask if char.upper() in _EDITABLE);


def picture_display_width(picture):
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    if spec.choices:
        return picture_capacity(spec);
    return max(1, len(spec.mask));


def picture_choices(picture):
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    return tuple(spec.choices);


def _accepts(token, char):
    token = str(token).upper();
    if token == "A":
        return char.isalpha();
    if token == "N":
        return char.isalnum();
    if token in ("X", "!"):
        return char != "\n";
    if token == "9":
        return char.isdigit() or char in "+-";
    if token == "#":
        return char.isdigit() or char in "+- ";
    if token in ("Y", "L"):
        return char.upper() in "YNTFSV01";
    return False;


def picture_input_char(picture, position, char, overflow=False):
    """Validate/transform one GET character at a logical data position.

    The position counts editable data characters rather than display literals.
    ``None`` means reject the keystroke.  Overflow characters are accepted only
    when FIELD_WRAP_OVERFLOW is enabled.
    """
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    if not char:
        return None;
    if spec.choices:
        index = max(0, int(position));
        for choice in spec.choices:
            if index < len(choice) and choice[index].casefold() == str(char)[0].casefold():
                chosen = choice[index];
                return chosen.upper() if spec.uppercase else chosen;
        return None;
    data_tokens = [token for token in spec.mask if token.upper() in _EDITABLE];
    index = max(0, int(position));
    if not data_tokens and not spec.mask:
        return char.upper() if spec.uppercase else char;
    if index >= len(data_tokens):
        if not overflow:
            return None;
        return char.upper() if spec.uppercase else char;
    token = data_tokens[index];
    if not _accepts(token, char):
        return None;
    if spec.uppercase or token == "!":
        return char.upper();
    return char;


def _format_character(value, spec, overflow=False):
    source = str(value);
    if spec.choices:
        return source.upper() if spec.uppercase else source;
    if spec.uppercase:
        source = source.upper();
    if not spec.mask:
        return source;
    out = [];
    data_index = 0;
    for token in spec.mask:
        upper = token.upper();
        if upper not in _EDITABLE:
            out.append(token);
            continue;
        chosen = "";
        while data_index < len(source):
            char = source[data_index];
            data_index += 1;
            if _accepts(token, char):
                chosen = char.upper() if spec.uppercase or upper == "!" else char;
                break;
        out.append(chosen if chosen else " ");
    if overflow and data_index < len(source):
        tail = source[data_index:];
        out.append(tail.upper() if spec.uppercase else tail);
    result = "".join(out);
    return result.rstrip() if overflow else result;


def _decimal_value(value):
    if isinstance(value, Decimal):
        return value;
    try:
        return Decimal(str(value));
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PictureError("Numeric PICTURE requires a numeric value") from exc;


def _numeric_mask_info(mask):
    if not mask:
        return 0, False;
    decimal_index = mask.rfind(".");
    if decimal_index < 0:
        decimal_places = 0;
    else:
        decimal_places = sum(1 for char in mask[decimal_index + 1:] if char in "9#*");
    grouped = "," in (mask[:decimal_index] if decimal_index >= 0 else mask);
    return decimal_places, grouped;


def _swap_european(text):
    marker = "\x00";
    return text.replace(",", marker).replace(".", ",").replace(marker, ".");


def _format_numeric(value, spec, overflow=False):
    number = _decimal_value(value);
    mask = spec.mask or "9";
    width = max(1, len(mask));
    if spec.blank_zero and number == 0:
        return " " * width;
    decimal_places, grouped = _numeric_mask_info(mask);
    quant = Decimal(1).scaleb(-decimal_places) if decimal_places else Decimal(1);
    number = number.quantize(quant, rounding=ROUND_HALF_UP);
    negative = number < 0;
    absolute = abs(number);
    format_spec = ",.{}f".format(decimal_places) if grouped else ".{}f".format(decimal_places);
    body = format(absolute, format_spec);
    currency = "$" in mask;
    if negative and "(" not in spec.functions:
        body = "-" + body;
    protected = "*" in mask;
    if currency:
        body_width = max(0, width - 1);
        if len(body) > body_width and not overflow:
            result = "*" * width;
        else:
            fill = "*" if protected else " ";
            aligned = body.ljust(body_width, fill) if "B" in spec.functions else body.rjust(body_width, fill);
            result = "$" + aligned if "$" == mask[:1] else aligned + "$";
    else:
        if len(body) > width and not overflow:
            result = "*" * width;
        else:
            fill = "*" if protected else " ";
            result = body.ljust(width, fill) if "B" in spec.functions else body.rjust(width, fill);
    if overflow and len(body) + (1 if currency else 0) > width:
        result = ("$" if currency else "") + body;
    if negative and "(" in spec.functions:
        stripped = result.strip().lstrip("-");
        result = "({})".format(stripped);
    if "C" in spec.functions and number > 0:
        result += " CR";
    if "X" in spec.functions and number < 0:
        result = result.replace("-", "").strip() + " DB";
    if "E" in spec.functions:
        result = _swap_european(result);
    return result;


def _coerce_datetime(value):
    if isinstance(value, datetime):
        return value;
    if isinstance(value, date):
        return datetime.combine(value, time());
    if isinstance(value, time):
        return datetime.combine(date.today(), value);
    source = str(value).strip();
    try:
        return datetime.fromisoformat(source);
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(source), time());
        except ValueError as exc:
            raise PictureError("Date/time PICTURE requires an ISO-like date/time value") from exc;


def transform(value, picture, overflow=False):
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    if "G" in spec.functions:
        moment = _coerce_datetime(value);
        return moment.strftime("%Y.%m.%d");
    if "T" in spec.functions:
        moment = _coerce_datetime(value);
        return moment.strftime("%H:%M:%S");
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return _format_numeric(value, spec, overflow=overflow);
    if isinstance(value, (date, datetime, time)):
        moment = _coerce_datetime(value);
        if "E" in spec.functions:
            return moment.strftime("%d/%m/%Y");
        return str(value);
    if isinstance(value, bool):
        if any(char.upper() in ("Y", "L") for char in spec.mask):
            return "Y" if value else "N";
        return "T" if value else "F";
    return _format_character(value, spec, overflow=overflow);


def strip_picture_literals(text, picture):
    spec = picture if isinstance(picture, PictureSpec) else parse_picture(picture);
    source = str(text);
    if not spec.remove_literals or not spec.mask:
        return source;
    output = [];
    index = 0;
    for token in spec.mask:
        if index >= len(source):
            break;
        if token.upper() in _EDITABLE:
            output.append(source[index]);
        index += 1;
    if index < len(source):
        output.append(source[index:]);
    return "".join(output);
