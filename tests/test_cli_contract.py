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

import pytest;
from sumcore import __version__;
from sumcore.cli import main;
from sumcore.cli_contract import ArgumentSpec, CommandSpec, ExampleSpec, OptionSpec, ParseResult;


def test_minimal_core_version(capsys):
    with pytest.raises(SystemExit) as exit_status:
        main(["--version"]);
    assert exit_status.value.code == 0;
    assert capsys.readouterr().out == "sumcore {}\n".format(__version__);


def test_minimal_core_help_and_no_args(capsys):
    assert main([]) == 0;
    assert "--version" in capsys.readouterr().out;
    with pytest.raises(SystemExit) as exit_status:
        main(["--help"]);
    assert exit_status.value.code == 0;


def test_minimal_core_error(capsys):
    with pytest.raises(SystemExit) as exit_status:
        main(["--unknown"]);
    assert exit_status.value.code == 2;
    assert "--unknown" in capsys.readouterr().err;


def test_contract_constructs_without_parser():
    spec = CommandSpec("demo", "example", options=(OptionSpec("--lang", aliases=("--language",), value_type="text"),), arguments=(ArgumentSpec("name"),), examples=(ExampleSpec("demo --lang en abc"),));
    assert spec.options[0].aliases == ("--language",);
    assert spec.arguments[0].name == "name";
    result = ParseResult("demo", options={"lang": "en"}, arguments={"name": "abc"});
    assert result.options["lang"] == "en";
