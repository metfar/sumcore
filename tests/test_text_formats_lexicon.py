#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re;
from sumcore.text import repeat,mid,instr,trim,ltrim,rtrim,like,ilike;
from sumcore.formatting import numformat,boolformat,tristate;
from sumcore.lexicon import resolve,help_topics;

def test_zero_based_text_semantics():
    assert repeat("ab",3)=="ababab";
    assert mid("abc",0,1)=="a";
    assert instr("abcdef","cd")==2;
    assert instr("abcdef","xx")==-1;

def test_trim_variants():
    assert trim("...hola...",".")=="hola";
    assert ltrim("---abc","-")=="abc";
    assert rtrim("abc---","-")=="abc";
    assert trim("123abc456",re.compile(r"\d+"))=="abc";
    assert trim("xyhelloxy",["xy"])=="hello";

def test_like():
    assert like("abcdef","abc%");
    assert like("abc","a_c");
    assert ilike("Montevideo","monte%");

def test_formats_and_tristate():
    assert numformat(5,"general")=="5";
    assert numformat(5,"$ 0000.00")=="$ 0005.00";
    assert tristate(-1) is True;
    assert tristate(None) is None;
    assert boolformat(None,"NO|SI|OMITIDO")=="OMITIDO";

def test_multilingual_lexicon_and_help():
    assert resolve("BUSCARV","es","function")=="VLOOKUP";
    assert resolve("RECHERCHEV","fr","function")=="VLOOKUP";
    assert resolve("PROCV","pt","function")=="VLOOKUP";
    topics=help_topics("es");
    assert [topic["name"] for topic in topics]==sorted([topic["name"] for topic in topics],key=str.casefold);
    assert all(topic["example"] for topic in topics);
    assert all(topic["canonical"]!="ABOUT" for topic in topics);
