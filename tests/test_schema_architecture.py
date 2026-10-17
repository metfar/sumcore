#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301

from sumcore.architecture import DEFAULT_AUTHORITIES, write_architecture_artifacts;
from sumcore.schema import SUMTAB_FORMAT, canonical_type;


def test_sum_types_are_authoritative_above_language_runtimes():
    assert canonical_type("currency") == "NUMERIC";
    assert canonical_type("bool") == "LOGICAL";
    assert canonical_type("double") == "FLOAT";
    assert canonical_type("list") == "LIST";


def test_sumtab_and_index_definitions_are_registered_architecture_contracts():
    assert SUMTAB_FORMAT == "sumtab/1";
    assert DEFAULT_AUTHORITIES["sumtab/1"]["authority"] == "sumCore";
    assert DEFAULT_AUTHORITIES["sumtab/1"]["implementation"] == "sumdoc.sumtab";
    assert DEFAULT_AUTHORITIES["sum.indexes/1"]["authority"] == "sumCore";


def test_architecture_artifacts_include_authorities(tmp_path):
    paths = write_architecture_artifacts(tmp_path);
    names = {path.name for path in paths};
    assert "SUM_AUTHORITIES.md" in names;
    yaml_text = (tmp_path / "SUM_ARCHITECTURE.yaml").read_text(encoding="utf-8");
    assert "authorities:" in yaml_text;
    assert "sumtab/1:" in yaml_text;
