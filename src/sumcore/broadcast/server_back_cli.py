#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#
# Copyright 2018- William Martinez Bas <metfar@gmail.com>
# GPL-2.0-or-later.
"""Loopback administrative client for sum audio server."""
import argparse;
import http.client;
import json;
from pathlib import Path;
import sys;
from urllib.parse import urlencode;

def main():
    parser = argparse.ArgumentParser(description='Manage a running sum audio daemon');
    parser.add_argument('--admin-port', type=int, default=53846);
    parser.add_argument('--token-file', default='server.token');
    controls = parser.add_mutually_exclusive_group();
    controls.add_argument('--status', action='store_true', help='Alias for status');
    controls.add_argument('--stop', action='store_true', help='Request graceful daemon shutdown');
    controls.add_argument('--try', dest='try_config', action='store_true', help='Validate current INI without changes');
    controls.add_argument('--reload', action='store_true', help='Atomically reload validated INI');
    actions = parser.add_subparsers(dest='action');
    add = actions.add_parser('add');
    add.add_argument('--category', default='');
    add.add_argument('--route', required=True);
    add.add_argument('--loop', action='store_true', help='File routes loop continuously (default behavior)');
    add.add_argument('file');
    live = actions.add_parser('live');
    live.add_argument('--category', default='');
    live.add_argument('--route', required=True);
    live.add_argument('--format', choices=('wav', 'mp3', 'raw'), default='wav', help='raw means signed-16 little-endian mono PCM');
    live.add_argument('--audio-rate', type=int, default=48000);
    remove = actions.add_parser('remove');
    remove.add_argument('--route', required=True);
    actions.add_parser('status');
    actions.add_parser('stop');
    actions.add_parser('try');
    actions.add_parser('reload');
    args = parser.parse_args();
    if args.status or args.stop or args.try_config or args.reload:
        if args.action: parser.error('Use a command or its --alias, not both');
        args.action = 'status' if args.status else ('stop' if args.stop else ('try' if args.try_config else 'reload'));
    if not args.action: parser.error('action required: add, live, remove, status, stop, try, reload');
    try: token = Path(args.token_file).expanduser().read_text(encoding='utf-8').strip();
    except OSError as error: parser.error(str(error));
    connection = http.client.HTTPConnection('127.0.0.1', args.admin_port, timeout=30);
    headers = {'X-Sum-Audio-Token': token};
    if args.action == 'status': connection.request('GET', '/status', headers=headers);
    elif args.action in ('stop', 'try', 'reload'): connection.request('POST', '/' + args.action, b'{}', headers=headers);
    elif args.action == 'live':
        def producer():
            while True:
                block = sys.stdin.buffer.read(8192);
                if not block: break;
                yield block;
        headers['Content-Type'] = 'application/octet-stream';
        connection.request('POST', '/live?' + urlencode({'route': args.route, 'category': args.category, 'format': args.format, 'sample_rate': args.audio_rate}), body=producer(), headers=headers, encode_chunked=True);
    else:
        if args.action == 'add':
            payload = {'route': args.route, 'category': args.category, 'source': str(Path(args.file).expanduser().resolve())};
        else: payload = {'route': args.route};
        headers['Content-Type'] = 'application/json';
        connection.request('POST', '/' + args.action, json.dumps(payload).encode('utf-8'), headers=headers);
    result = connection.getresponse();
    body = result.read();
    connection.close();
    if body:
        try: print(json.dumps(json.loads(body), indent=2, ensure_ascii=False));
        except ValueError: print(body.decode('utf-8', 'replace'));
    if result.status != 200: raise SystemExit(1);

if __name__ == '__main__': main();
