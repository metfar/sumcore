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
"""Sum audio broadcast CLI entry points.""";

def server_daemon():
    from .broadcast.server_daemon import main;
    return main();

def server_back_cli():
    from .broadcast.server_back_cli import main;
    return main();

def stream_client():
    from .broadcast.stream_client import main;
    return main();
