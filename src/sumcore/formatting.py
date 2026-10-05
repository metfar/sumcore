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
from datetime import date,datetime,time;
from decimal import Decimal;
from .picture import transform;

UNKNOWN=object();

NUM_PRESETS={
    "general":None,
    "number":"9999999999.99",
    "number.integer":"9999999999",
    "number.decimal2":"9999999999.99",
    "number.grouped":"999,999,999.99",
    "percent":"999999990.00%",
    "currency":"$999,999,999.99",
    "currency.dollar":"$999,999,999.99",
    "currency.euro":"€999,999,999.99",
    "currency.peso":"$999,999,999.99",
    "currency.yen":"¥999,999,999",
    "scientific":"scientific",
};

DATE_PRESETS={
    "date.iso":"%Y-%m-%d",
    "date.es":"%d/%m/%Y",
    "date.uk":"%d/%m/%Y",
    "date.us":"%m/%d/%Y",
    "time.24h":"%H:%M:%S",
    "time.12h":"%I:%M:%S %p",
};

BOOL_PRESETS={
    "boolean.truefalse":"FALSE|TRUE|UNKNOWN",
    "boolean.yesno":"NO|YES|UNKNOWN",
    "boolean.onoff":"OFF|ON|UNKNOWN",
    "boolean.01":"0|1|-1",
};

TEXT_PRESETS={
    "text.upper":"upper",
    "text.lower":"lower",
    "text.title":"title",
    "text.trim":"trim",
};


def _name(value):
    return (str(value).strip().casefold());


def tristate(value):
    if value is UNKNOWN or value is None: return (None);
    if isinstance(value,bool): return (bool(value));
    if isinstance(value,(int,float,Decimal)):
        # BASIC/xBase families commonly use -1 as TRUE, while others use 1.
        # Missing/unknown is represented by None/NIL/NULL rather than stealing
        # a valid historical numeric boolean value.
        return (False if value==0 else True);
    name=_name(value);
    if name in ("unknown","null","none","nil","na","n/a"): return (None);
    if name in ("true","t","yes","y","on","1"): return (True);
    if name in ("false","f","no","n","off","0"): return (False);
    raise ValueError("Value is not boolean/tristate");


def boolformat(value,string_format="FALSE|TRUE|UNKNOWN"):
    spec=BOOL_PRESETS.get(_name(string_format),str(string_format));
    parts=spec.split("|");
    if len(parts)==2: parts.append("");
    if len(parts)!=3: raise ValueError("BOOLFORMAT requires FALSE|TRUE|UNKNOWN");
    state=tristate(value);
    return (parts[2] if state is None else parts[1] if state else parts[0]);


def _general_number(value):
    if isinstance(value,bool): return ("1" if value else "0");
    number=Decimal(str(value));
    if number==number.to_integral(): return (str(number.quantize(Decimal(1))));
    text=format(number.normalize(),"f");
    return (text.rstrip("0").rstrip(".") if "." in text else text);


def _literal_numeric_picture(value,picture):
    """Apply simple 0/9/# numeric pictures while preserving literal text.

    The legacy sumX PICTURE engine remains available for @-style masks.  This
    helper adds spreadsheet-friendly mandatory 0 positions and arbitrary
    currency literals such as ``$ 0000.00``.
    """
    source=str(picture);
    placeholders=[index for index,char in enumerate(source) if char in "09#"];
    if not placeholders: return (source);
    dot=source.rfind(".");
    decimals=sum(1 for i in placeholders if dot>=0 and i>dot);
    number=Decimal(str(value)); negative=number<0; number=abs(number);
    rendered=("{:,.%df}"%decimals).format(number) if "," in source else ("{:.%df}"%decimals).format(number);
    whole,fraction=(rendered.split(".",1)+[""])[:2]; whole_digits="".join(ch for ch in whole if ch.isdigit());
    result=list(source); whole_positions=[i for i in placeholders if dot<0 or i<dot]; frac_positions=[i for i in placeholders if dot>=0 and i>dot];
    wi=len(whole_digits)-1;
    for pos in reversed(whole_positions):
        token=source[pos];
        if wi>=0: result[pos]=whole_digits[wi]; wi-=1;
        elif token=="0": result[pos]="0";
        else: result[pos]=" ";
    fi=0;
    for pos in frac_positions:
        token=source[pos];
        if fi<len(fraction): result[pos]=fraction[fi]; fi+=1;
        elif token=="0": result[pos]="0";
        else: result[pos]=" ";
    if wi>=0: return (("-" if negative else "")+rendered);
    text="".join(result);
    if negative:
        first=min(whole_positions) if whole_positions else 0;
        text=text[:first]+"-"+text[first+1:];
    return (text);


def numformat(number_input,string_format="general"):
    name=_name(string_format);
    if name in ("general","number.general"): return (_general_number(number_input));
    if name=="scientific": return ("{:E}".format(Decimal(str(number_input))));
    picture=NUM_PRESETS.get(name,string_format);
    if picture is None: return (_general_number(number_input));
    if name=="percent": return (_literal_numeric_picture(Decimal(str(number_input))*100,picture));
    if "0" in str(picture): return (_literal_numeric_picture(number_input,picture));
    try: return (transform(number_input,picture,overflow=True).strip());
    except Exception: return (_literal_numeric_picture(number_input,picture));


def _coerce_datetime(value):
    if isinstance(value,datetime): return (value);
    if isinstance(value,date): return (datetime.combine(value,time()));
    if isinstance(value,time): return (datetime.combine(date.today(),value));
    source=str(value).strip();
    try: return (datetime.fromisoformat(source));
    except ValueError: return (datetime.combine(date.fromisoformat(source),time()));


def _date_pattern(pattern):
    # Friendly spreadsheet/BASIC tokens. Longest first to avoid partial swaps.
    pairs=(("YYYY","%Y"),("YY","%y"),("DD","%d"),("MM","%m"),("hh","%H"),("HH","%H"),("mm","%M"),("ss","%S"));
    result=str(pattern);
    for token,replacement in pairs: result=result.replace(token,replacement);
    return (result);


def dateformat(date_input,string_format="date.iso"):
    pattern=DATE_PRESETS.get(_name(string_format),str(string_format));
    return (_coerce_datetime(date_input).strftime(_date_pattern(pattern)));


def textformat(text_input,string_format="text"):
    name=_name(string_format); text=str(text_input);
    action=TEXT_PRESETS.get(name,name);
    if action in ("text","general"): return (text);
    if action=="upper": return (text.upper());
    if action=="lower": return (text.lower());
    if action=="title": return (text.title());
    if action=="trim": return (text.strip());
    raise ValueError("Unknown TEXTFORMAT preset: {}".format(string_format));


__all__=["UNKNOWN","NUM_PRESETS","DATE_PRESETS","BOOL_PRESETS","TEXT_PRESETS","tristate","numformat","dateformat","textformat","boolformat"];
