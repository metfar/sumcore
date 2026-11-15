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
"""Minimal sumCore entry point.  No dependency on the SUM UI parser.""";

import sys;
from . import __version__;


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv);
    if args == ["--version"]:
        print("sumcore {}".format(__version__));
        raise SystemExit(0);
    if not args or args == ["--help"] or args == ["-h"]:
        print("usage: sumcore [-h] [--version]");
        print("SUM core architecture package.");
        print("\noptions:");
        print("  -h, --help    show this help message and exit");
        print("  --version     show the sumcore version and exit");
        if args:
            raise SystemExit(0);
        return 0;
    print("sumcore: unrecognized arguments: {}".format(" ".join(args)), file=sys.stderr);
    raise SystemExit(2);


if __name__ == "__main__":
    raise SystemExit(main());
