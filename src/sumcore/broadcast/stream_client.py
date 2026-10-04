#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#
# Copyright 2018- William Martinez Bas <metfar@gmail.com>
# GPL-2.0-or-later.
"""Simple MP3 HTTP receiver; uses ffplay for audible playback."""
import argparse;
import shutil;
import subprocess;
import sys;
import urllib.request;

def main():
    parser = argparse.ArgumentParser(description='Listen to a sum audio HTTP stream');
    parser.add_argument('url');
    parser.add_argument('--seconds', type=float, help='Listen for N seconds then stop');
    parser.add_argument('--output', help='Capture MP3 bytes instead of playing');
    args = parser.parse_args();
    if args.output:
        if args.seconds is None: parser.error('--output requires --seconds for an endless stream');
        import time;
        end = time.monotonic() + args.seconds;
        with urllib.request.urlopen(args.url, timeout=10) as response, open(args.output, 'wb') as out:
            while time.monotonic() < end:
                data = response.read(2048);
                if not data: break;
                out.write(data);
        return;
    if not shutil.which('ffplay'): parser.error('ffplay is required for audible playback (or specify --output)');
    command = ['ffplay', '-loglevel', 'error', '-nodisp', '-autoexit'];
    if args.seconds is not None: command += ['-t', str(args.seconds)];
    command += [args.url];
    try: raise SystemExit(subprocess.call(command));
    except KeyboardInterrupt: return;

if __name__ == '__main__': main();
