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
"""Cross-language lexical compatibility helpers for Sum runtimes.

The helpers deliberately normalize *concepts*, not numeric representations.
For example, BASIC may represent TRUE as -1 while Python represents True as 1
when coerced to an integer.  Frontends are expected to keep those native
semantics after using this module to recognize aliases.
""";

TRUE_ALIASES = frozenset(("TRUE", "True", "true"));
FALSE_ALIASES = frozenset(("FALSE", "False", "false"));
NULL_ALIASES = frozenset(("NULL", "Null", "null", "NIL", "Nil", "nil", "None", "none"));


def truth_alias(value):
    """Return True/False when *value* is a recognized logical alias.

    ``None`` means that the token is not a logical alias.  Existing booleans
    are returned unchanged.
    """;
    if isinstance(value, bool): return value;
    text = str(value);
    if text in TRUE_ALIASES: return True;
    if text in FALSE_ALIASES: return False;
    return None;


def is_null_alias(value):
    """Return whether *value* spells one of the Sum null aliases.""";
    return str(value) in NULL_ALIASES;


def basic_boolean(value):
    """Return the canonical sumBASIC numeric boolean (TRUE=-1, FALSE=0).""";
    return -1 if bool(value) else 0;


__all__ = ["TRUE_ALIASES", "FALSE_ALIASES", "NULL_ALIASES", "truth_alias", "is_null_alias", "basic_boolean"];
