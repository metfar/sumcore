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
"""Small cross-language ASC table explorer.""";
from .charset import ASC;

def main(argv=None):
    import argparse;
    parser = argparse.ArgumentParser();
    parser.add_argument("--start", type=int, default=0);
    parser.add_argument("--count", type=int, default=256);
    args = parser.parse_args(argv);
    for index in range(max(0, args.start), min(len(ASC), args.start + args.count)):
        print("{0:4d} {1!r}".format(index, ASC[index]));
    return 0;

if __name__ == "__main__":
    raise SystemExit(main());
