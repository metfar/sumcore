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
from sumcore import DEFAULT_ARCHITECTURE, write_architecture_artifacts;

def test_dependency_model():
    assert "sumGUI" in DEFAULT_ARCHITECTURE["sumIDE"]["optional"];
    assert "sumGUI" not in DEFAULT_ARCHITECTURE["sumIDE"]["requires"];

def test_artifacts(tmp_path):
    paths=write_architecture_artifacts(tmp_path);
    assert len(paths)==5;
    assert all(path.exists() for path in paths);

def test_cli_version(capsys):
    from sumcore.cli import main;
    import pytest;
    with pytest.raises(SystemExit) as exc: main(["--version"]);
    assert exc.value.code==0; assert "sumcore 0.1.0a14" in capsys.readouterr().out;


def test_architecture_cli_version(capsys):
    from sumcore.architecture import main;
    import pytest;
    with pytest.raises(SystemExit) as exc: main(["--version"]);
    assert exc.value.code==0; assert "0.1.0a14" in capsys.readouterr().out;

def test_sum_compat_aliases():
    from sumcore import basic_boolean, is_null_alias, truth_alias;
    assert truth_alias("TRUE") is True;
    assert truth_alias("True") is True;
    assert truth_alias("true") is True;
    assert truth_alias("FALSE") is False;
    assert truth_alias("false") is False;
    assert is_null_alias("NULL");
    assert is_null_alias("nil");
    assert is_null_alias("None");
    assert basic_boolean(True) == -1;
    assert basic_boolean(False) == 0;
