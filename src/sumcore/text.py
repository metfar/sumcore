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
import re;


def repeat(something,n_times):
    """Repeat a value using the host multiplication semantics."""
    return (something * int(n_times));


def left(text,count):
    return (str(text)[:max(0,int(count))]);


def right(text,count):
    count=max(0,int(count));
    return (str(text)[-count:] if count else "");


def mid(text,start,length=None):
    """Return a 0-based substring, shared by sumBASIC/sumX/sumpy/SES."""
    source=str(text); start=max(0,int(start));
    if length is None: return (source[start:]);
    return (source[start:start+max(0,int(length))]);


def instr(text,needle,start=0,case_sensitive=True):
    """Return a 0-based match offset, or -1 when the substring is absent."""
    source=str(text); wanted=str(needle); start=max(0,int(start));
    if case_sensitive: return (source.find(wanted,start));
    return (source.casefold().find(wanted.casefold(),start));


def find(text,needle,start=0):
    return (instr(text,needle,start,True));


def _trim_literals(source,items,left_side=True,right_side=True):
    items=tuple(str(item) for item in items if str(item)!="");
    if not items: return (source);
    changed=True;
    while changed:
        changed=False;
        if left_side:
            for item in items:
                if source.startswith(item): source=source[len(item):]; changed=True; break;
        if right_side:
            for item in items:
                if source.endswith(item): source=source[:-len(item)]; changed=True; break;
    return (source);


def _trim_regex(source,pattern,left_side=True,right_side=True):
    regex=pattern if hasattr(pattern,"match") else re.compile(str(pattern));
    if left_side:
        while True:
            match=regex.match(source);
            if match is None or match.end()==0: break;
            source=source[match.end():];
    if right_side:
        tail=re.compile("(?:"+regex.pattern+")$");
        while True:
            match=tail.search(source);
            if match is None or match.start()==match.end(): break;
            source=source[:match.start()];
    return (source);


def _trim(text,what=None,left_side=True,right_side=True):
    source=str(text);
    if what is None:
        if left_side and right_side: return (source.strip());
        if left_side: return (source.lstrip());
        return (source.rstrip());
    if hasattr(what,"match") and hasattr(what,"pattern"):
        return (_trim_regex(source,what,left_side,right_side));
    if isinstance(what,(list,tuple,set,frozenset)):
        return (_trim_literals(source,what,left_side,right_side));
    # A string means a set of literal characters, matching Python's strip()
    # intuition and the old xBase family of trim helpers.
    chars=str(what);
    if left_side: source=source.lstrip(chars);
    if right_side: source=source.rstrip(chars);
    return (source);


def ltrim(text,what=None):
    return (_trim(text,what,True,False));


def rtrim(text,what=None):
    return (_trim(text,what,False,True));


def alltrim(text,what=None):
    return (_trim(text,what,True,True));


def trim(text,what=None):
    return (alltrim(text,what));


def _sql_like_regex(pattern):
    out=["^"]; escaped=False;
    for char in str(pattern):
        if escaped:
            out.append(re.escape(char)); escaped=False; continue;
        if char=="\\": escaped=True; continue;
        if char=="%": out.append(".*"); continue;
        if char=="_": out.append("."); continue;
        out.append(re.escape(char));
    if escaped: out.append(re.escape("\\"));
    out.append("$");
    return ("".join(out));


def like(text,pattern):
    return (re.match(_sql_like_regex(pattern),str(text),flags=re.DOTALL) is not None);


def ilike(text,pattern):
    return (re.match(_sql_like_regex(pattern),str(text),flags=re.DOTALL|re.IGNORECASE) is not None);


__all__=["repeat","left","right","mid","instr","find","ltrim","rtrim","trim","alltrim","like","ilike"];
