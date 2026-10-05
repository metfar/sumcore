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
"""Language-neutral vocabulary for the sum ecosystem.

The canonical identifier is always stable and language independent.  A
frontend chooses a syntax language (en/es/fr/pt) and maps human spellings to
that identifier.  UI language and data locale remain separate concerns.
""";
from dataclasses import dataclass,field;
import unicodedata;

SUPPORTED_LANGUAGES=("en","es","fr","pt");


def _key(value):
    text=unicodedata.normalize("NFKC",str(value)).strip().casefold();
    return (text);


@dataclass(frozen=True)
class Lexeme:
    canonical:str;
    kind:str;
    names:dict;
    aliases:dict=field(default_factory=dict);
    summary:str="";
    syntax:tuple=();
    example:str="";
    see_also:tuple=();

    def spellings(self,language):
        language=language if language in SUPPORTED_LANGUAGES else "en";
        values=[self.names.get(language,self.names.get("en",self.canonical))];
        values.extend(self.aliases.get(language,()));
        if self.canonical not in values: values.append(self.canonical);
        return (tuple(values));


_FUNCTIONS=(
    Lexeme("ABS","function",{"en":"ABS","es":"ABS","fr":"ABS","pt":"ABS"},summary="Absolute value.",syntax=("ABS(number)",),example="ABS(-3) -> 3"),
    Lexeme("ALLTRIM","function",{"en":"ALLTRIM","es":"TODORECORTAR","fr":"TOUTSUPPRESPACE","pt":"TODOTRIM"},aliases={"en":("TRIM",),"es":("TRIM",),"fr":("TRIM",),"pt":("TRIM",)},summary="Trim both ends of text; optionally trim selected characters, items or a regular expression.",syntax=("ALLTRIM(text [, what])",),example='ALLTRIM("...hola...", ".") -> "hola"',see_also=("LTRIM","RTRIM")),
    Lexeme("AND","function",{"en":"AND","es":"Y","fr":"ET","pt":"E"},summary="Logical AND.",syntax=("AND(a; b; ...)",),example="AND(TRUE; TRUE) -> TRUE"),
    Lexeme("AVG","function",{"en":"AVG","es":"PROMEDIO","fr":"MOYENNE","pt":"MÉDIA"},aliases={"en":("AVERAGE",),"pt":("MEDIA",)},summary="Arithmetic mean.",syntax=("AVG(values...)",),example="AVG(2;4;6) -> 4"),
    Lexeme("BOOLFORMAT","function",{"en":"BOOLFORMAT","es":"FORMATOBOOL","fr":"FORMATBOOL","pt":"FORMATOBOOL"},summary="Format FALSE/TRUE/UNKNOWN without changing the logical value.",syntax=("BOOLFORMAT(value; format)",),example='BOOLFORMAT(NULL; "NO|SI|OMITIDO") -> "OMITIDO"'),
    Lexeme("CEIL","function",{"en":"CEIL","es":"TECHO","fr":"PLAFOND","pt":"TETO"},aliases={"en":("CEILING",),"es":("REDONDEAR.MAS",),"fr":("ARRONDI.SUP",),"pt":("ARREDONDAR.PARA.CIMA",)},summary="Round toward positive infinity.",syntax=("CEIL(number)",),example="CEIL(1.2) -> 2"),
    Lexeme("COUNT","function",{"en":"COUNT","es":"CONTAR","fr":"NB","pt":"CONT.NÚM"},aliases={"pt":("CONT.NUM",)},summary="Count numeric values.",syntax=("COUNT(values...)",),example="COUNT(1;2;\"x\") -> 2"),
    Lexeme("COUNTIF","function",{"en":"COUNTIF","es":"CONTAR.SI","fr":"NB.SI","pt":"CONT.SE"},summary="Count values matching a criterion.",syntax=("COUNTIF(range; criterion)",),example='COUNTIF(A1:A10; ">0")'),
    Lexeme("DATEFORMAT","function",{"en":"DATEFORMAT","es":"FORMATOFECHA","fr":"FORMATDATE","pt":"FORMDATA"},summary="Format a date using a named preset or explicit pattern.",syntax=("DATEFORMAT(value; format)",),example='DATEFORMAT(d; "DD/MM/YYYY")'),
    Lexeme("FIND","function",{"en":"FIND","es":"ENCONTRAR","fr":"TROUVE","pt":"LOCALIZAR"},summary="Find a substring and return its zero-based position, or -1.",syntax=("FIND(text; substring [, start])",),example='FIND("abcdef"; "cd") -> 2',see_also=("INSTR","ILIKE","LIKE")),
    Lexeme("FLOOR","function",{"en":"FLOOR","es":"PISO","fr":"PLANCHER","pt":"PISO"},aliases={"en":("ROUNDDOWN",),"es":("REDONDEAR.MENOS",),"fr":("ARRONDI.INF",),"pt":("ARREDONDAR.PARA.BAIXO",)},summary="Round toward negative infinity.",syntax=("FLOOR(number)",),example="FLOOR(1.8) -> 1"),
    Lexeme("HLOOKUP","function",{"en":"HLOOKUP","es":"BUSCARH","fr":"RECHERCHEH","pt":"PROCH"},summary="Horizontal lookup.",syntax=("HLOOKUP(value; table; row; exact)",),example='HLOOKUP("A"; A1:D4; 2; TRUE)'),
    Lexeme("IF","function",{"en":"IF","es":"SI","fr":"SI","pt":"SE"},summary="Return one value when a condition is true and another when it is false.",syntax=("IF(condition; true_value; false_value)",),example='IF(A1>0; "positive"; "other")'),
    Lexeme("ILIKE","function",{"en":"ILIKE","es":"COMO.I","fr":"COMME.I","pt":"COMO.I"},summary="Case-insensitive SQL-style pattern match using % and _.",syntax=("ILIKE(text; pattern)",),example='ILIKE("Montevideo"; "monte%") -> TRUE',see_also=("LIKE",)),
    Lexeme("INSTR","function",{"en":"INSTR","es":"EN.CADENA","fr":"DANSCHAINE","pt":"EMSTRING"},summary="Return a zero-based substring position, or -1 when absent.",syntax=("INSTR(text; substring)","INSTR(start; text; substring)"),example='INSTR("abcdef"; "cd") -> 2',see_also=("FIND","MID")),
    Lexeme("LEFT","function",{"en":"LEFT","es":"IZQUIERDA","fr":"GAUCHE","pt":"ESQUERDA"},summary="Take characters from the left side.",syntax=("LEFT(text; count)",),example='LEFT("abcdef"; 2) -> "ab"'),
    Lexeme("LENGTH","function",{"en":"LENGTH","es":"LARGO","fr":"NBCAR","pt":"NÚM.CARACT"},aliases={"en":("LEN",),"es":("LEN",),"fr":("LEN",),"pt":("NUM.CARACT", "LEN")},summary="Length of text or a collection.",syntax=("LENGTH(value)",),example='LENGTH("abc") -> 3'),
    Lexeme("LIKE","function",{"en":"LIKE","es":"COMO","fr":"COMME","pt":"COMO"},summary="SQL-style pattern match using % and _.",syntax=("LIKE(text; pattern)",),example='LIKE("abcdef"; "abc%") -> TRUE',see_also=("ILIKE",)),
    Lexeme("LTRIM","function",{"en":"LTRIM","es":"RECORTARIZQ","fr":"SUPPRESPACEG","pt":"LTRIM"},summary="Trim the left edge of text.",syntax=("LTRIM(text [, what])",),example='LTRIM("---abc"; "-") -> "abc"'),
    Lexeme("MID","function",{"en":"MID","es":"MEDIO","fr":"STXT","pt":"EXT.TEXTO"},aliases={"pt":("EXTTEXTO",)},summary="Take a zero-based substring.",syntax=("MID(text; start; length)",),example='MID("abcdef"; 0; 1) -> "a"',see_also=("INSTR","LEFT","RIGHT")),
    Lexeme("NOT","function",{"en":"NOT","es":"NO","fr":"NON","pt":"NÃO"},aliases={"pt":("NAO",)},summary="Logical negation.",syntax=("NOT(value)",),example="NOT(TRUE) -> FALSE"),
    Lexeme("NUMFORMAT","function",{"en":"NUMFORMAT","es":"FORMATONUM","fr":"FORMATNOMBRE","pt":"FORMATONUM"},summary="Format a number using a named preset or PICTURE.",syntax=("NUMFORMAT(number; format)",),example='NUMFORMAT(5; "$ 9990.00") -> "$    5.00"'),
    Lexeme("OR","function",{"en":"OR","es":"O","fr":"OU","pt":"OU"},summary="Logical OR.",syntax=("OR(a; b; ...)",),example="OR(FALSE; TRUE) -> TRUE"),
    Lexeme("REPEAT","function",{"en":"REPEAT","es":"REPETIR","fr":"RÉPÉTER","pt":"REPETIR"},aliases={"fr":("REPETER",)},summary="Repeat a value a specified number of times.",syntax=("REPEAT(value; count)",),example='REPEAT("ab"; 3) -> "ababab"'),
    Lexeme("RIGHT","function",{"en":"RIGHT","es":"DERECHA","fr":"DROITE","pt":"DIREITA"},summary="Take characters from the right side.",syntax=("RIGHT(text; count)",),example='RIGHT("abcdef"; 2) -> "ef"'),
    Lexeme("ROUND","function",{"en":"ROUND","es":"REDONDEAR","fr":"ARRONDI","pt":"ARRED"},summary="Round a number.",syntax=("ROUND(number [, digits])",),example="ROUND(3.14159; 2) -> 3.14"),
    Lexeme("RTRIM","function",{"en":"RTRIM","es":"RECORTARDER","fr":"SUPPRESPACED","pt":"RTRIM"},summary="Trim the right edge of text.",syntax=("RTRIM(text [, what])",),example='RTRIM("abc---"; "-") -> "abc"'),
    Lexeme("SUM","function",{"en":"SUM","es":"SUMA","fr":"SOMME","pt":"SOMA"},summary="Sum numeric values.",syntax=("SUM(values...)",),example="SUM(1;2;3) -> 6"),
    Lexeme("SUMIF","function",{"en":"SUMIF","es":"SUMAR.SI","fr":"SOMME.SI","pt":"SOMASE"},summary="Sum values matching a criterion.",syntax=("SUMIF(range; criterion [, sum_range])",),example='SUMIF(A1:A10; ">0"; B1:B10)'),
    Lexeme("TEXTFORMAT","function",{"en":"TEXTFORMAT","es":"FORMATOTEXTO","fr":"FORMATTexte","pt":"FORMATOTEXTO"},summary="Format or transform text through a named text preset.",syntax=("TEXTFORMAT(text; format)",),example='TEXTFORMAT("ana pérez"; "text.upper") -> "ANA PÉREZ"'),
    Lexeme("TRIM","function",{"en":"TRIM","es":"RECORTAR","fr":"SUPPRESPACE","pt":"ARRUMAR"},aliases={"en":("ALLTRIM",),"es":("TODORECORTAR",),"pt":("TODOTRIM",)},summary="Trim both ends of text.",syntax=("TRIM(text [, what])",),example='TRIM("  hello  ") -> "hello"'),
    Lexeme("VLOOKUP","function",{"en":"VLOOKUP","es":"BUSCARV","fr":"RECHERCHEV","pt":"PROCV"},summary="Vertical lookup.",syntax=("VLOOKUP(value; table; column; exact)",),example='VLOOKUP(A2; Clients; 3; TRUE)'),
);

_KEYWORDS=(
    Lexeme("ELSE","keyword",{"en":"ELSE","es":"SINO","fr":"SINON","pt":"SENÃO"},aliases={"pt":("SENAO",)},example="IF x THEN ... ELSE ..."),
    Lexeme("FOR","keyword",{"en":"FOR","es":"PARA","fr":"POUR","pt":"PARA"},example="FOR i=0 TO 10"),
    Lexeme("IF","keyword",{"en":"IF","es":"SI","fr":"SI","pt":"SE"},example="IF x>0 THEN PRINT x"),
    Lexeme("NEXT","keyword",{"en":"NEXT","es":"SIGUIENTE","fr":"SUIVANT","pt":"PRÓXIMO"},aliases={"pt":("PROXIMO",)},example="NEXT i"),
    Lexeme("PRINT","keyword",{"en":"PRINT","es":"IMPRIMIR","fr":"IMPRIMER","pt":"IMPRIMIR"},example='PRINT "hello"'),
    Lexeme("THEN","keyword",{"en":"THEN","es":"ENTONCES","fr":"ALORS","pt":"ENTÃO"},aliases={"pt":("ENTAO",)},example="IF x THEN PRINT x"),
    Lexeme("TO","keyword",{"en":"TO","es":"HASTA","fr":"À","pt":"ATÉ"},aliases={"fr":("A",),"pt":("ATE",)},example="FOR i=0 TO 10"),
);

_CONSTANTS=(
    Lexeme("FALSE","constant",{"en":"FALSE","es":"FALSO","fr":"FAUX","pt":"FALSO"},example="FALSE"),
    Lexeme("TRUE","constant",{"en":"TRUE","es":"VERDADERO","fr":"VRAI","pt":"VERDADEIRO"},example="TRUE"),
    Lexeme("UNKNOWN","constant",{"en":"UNKNOWN","es":"DESCONOCIDO","fr":"INCONNU","pt":"DESCONHECIDO"},aliases={"en":("NULL","NONE","NIL"),"es":("NULL","NONE","NIL"),"fr":("NULL","NONE","NIL"),"pt":("NULL","NONE","NIL")},example="UNKNOWN"),
);

LEXEMES=tuple(sorted(_FUNCTIONS+_KEYWORDS+_CONSTANTS,key=lambda item:(item.kind,item.canonical)));


def lexemes(kind=None):
    values=[item for item in LEXEMES if kind is None or item.kind==kind];
    return (tuple(values));


def resolve(name,language="en",kind=None,allow_canonical=True):
    wanted=_key(name); language=language if language in SUPPORTED_LANGUAGES else "en";
    for item in LEXEMES:
        if kind is not None and item.kind!=kind: continue;
        spellings=list(item.spellings(language));
        if not allow_canonical: spellings=[value for value in spellings if _key(value)!=_key(item.canonical) or _key(value)==_key(item.names.get(language,""))];
        if any(_key(value)==wanted for value in spellings): return (item.canonical);
    return (None);


def display_name(canonical,language="en",kind=None):
    canonical=_key(canonical); language=language if language in SUPPORTED_LANGUAGES else "en";
    for item in LEXEMES:
        if kind is not None and item.kind!=kind: continue;
        if _key(item.canonical)==canonical: return (item.names.get(language,item.names.get("en",item.canonical)));
    return (str(canonical).upper());


def help_topics(language="en",kind="function"):
    """Return A-Z help entries. About is intentionally not a help topic."""
    topics=[];
    for item in lexemes(kind):
        topics.append({
            "name":display_name(item.canonical,language,item.kind),
            "canonical":item.canonical,
            "summary":item.summary,
            "syntax":item.syntax,
            "example":item.example,
            "see_also":item.see_also,
        });
    topics.sort(key=lambda topic:_key(topic["name"]));
    return (tuple(topics));


__all__=["SUPPORTED_LANGUAGES","Lexeme","LEXEMES","lexemes","resolve","display_name","help_topics"];
