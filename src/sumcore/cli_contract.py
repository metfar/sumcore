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
"""Language-neutral specifications for SUM command-line interfaces.

This module describes CLI semantics; it deliberately does not parse commands.
Representations in future languages must preserve behavior, not Python classes.
""";

from dataclasses import dataclass, field;
from typing import Any, Mapping, Tuple;


@dataclass(frozen=True)
class OptionSpec:
    name: str;
    aliases: Tuple[str, ...] = ();
    description: str = "";
    value_type: str = "flag";
    default: Any = None;
    required: bool = False;
    choices: Tuple[str, ...] = ();
    metavar: str = "";


@dataclass(frozen=True)
class ArgumentSpec:
    name: str;
    description: str = "";
    value_type: str = "text";
    required: bool = True;


@dataclass(frozen=True)
class ExampleSpec:
    command: str;
    description: str = "";


@dataclass(frozen=True)
class CommandSpec:
    name: str;
    description: str = "";
    options: Tuple[OptionSpec, ...] = ();
    arguments: Tuple[ArgumentSpec, ...] = ();
    examples: Tuple[ExampleSpec, ...] = ();


@dataclass(frozen=True)
class ParseResult:
    """Neutral result for consumers that do not want argparse.Namespace.""";
    command: str;
    options: Mapping[str, Any] = field(default_factory=dict);
    arguments: Mapping[str, Any] = field(default_factory=dict);


__all__ = ["OptionSpec", "ArgumentSpec", "ExampleSpec", "CommandSpec", "ParseResult"];
