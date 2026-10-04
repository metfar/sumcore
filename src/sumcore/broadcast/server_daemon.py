#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#
# Copyright 2018- William Martinez Bas <metfar@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
"""HTTP audio service + loopback-only administrative API."""
import argparse;
import configparser;
import hmac;
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer;
import json;
import os;
from pathlib import Path;
import secrets;
import shutil;
import threading;
import subprocess;
from urllib.parse import urlsplit;
from .common import Station;

class Registry:
    def __init__(self, config, token_file, ffmpeg):
        self.lock = threading.RLock();
        self.routes = {};
        self.config = Path(config).expanduser().resolve();
        self.token_file = Path(token_file).expanduser().resolve();
        self.ffmpeg = ffmpeg;
        self.token_file.parent.mkdir(parents=True, exist_ok=True);
        if not self.token_file.exists():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL;
            fd = os.open(self.token_file, flags, 0o600);
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                file.write(secrets.token_hex(32) + '\n');
        self.token = self.token_file.read_text(encoding='utf-8').strip();
        self.restore();
        self.signal = Station('/signal', 'sumAudio - Adjustment Signal', '440 Hz sine wave', 'tone', self.ffmpeg);
        self.signal.start();

    def valid_route(self, value):
        if not isinstance(value, str) or not value.startswith('/') or value.startswith('/__') or '?' in value or '#' in value or len(value) > 200 or '//' in value or '..' in value:
            raise ValueError('Invalid route');
        if value in ('/', '/health', '/signal'):
            raise ValueError('Reserved route');
        return value;

    def add(self, route, category, source, persist=True):
        route = self.valid_route(route);
        path = Path(source).expanduser().resolve();
        if not path.is_file():
            raise ValueError('Source file missing: ' + str(path));
        with self.lock:
            if route in self.routes:
                raise ValueError('Route already exists');
            station = Station(route, str(category), str(path), 'file', self.ffmpeg);
            station.start();
            self.routes[route] = station;
            if persist:
                self.save();
            return station.status();

    def live(self, route, category, source_format="wav", sample_rate=48000):
        route = self.valid_route(route);
        with self.lock:
            if route in self.routes:
                raise ValueError('Route already exists');
            station = Station(route, str(category), 'stdin', 'live', self.ffmpeg, source_format=source_format, sample_rate=sample_rate);
            station.start();
            self.routes[route] = station;
            return station;

    def remove(self, route, persist=True):
        with self.lock:
            station = self.routes.pop(route, None);
            if station is None:
                raise ValueError('Unknown route');
            if persist:
                self.save();
        station.stop();

    def status(self):
        with self.lock:
            return [station.status() for station in self.routes.values()];

    def save(self):
        parser = configparser.ConfigParser(interpolation=None);
        for station in self.routes.values():
            if station.mode == 'file':
                parser['route:' + station.route] = {'category': station.category, 'source': station.source, 'loop': 'true'};
        self.config.parent.mkdir(parents=True, exist_ok=True);
        temp = self.config.with_suffix(self.config.suffix + '.tmp');
        with temp.open('w', encoding='utf-8') as file:
            parser.write(file);
        temp.replace(self.config);

    def inspect_config(self):
        """Parse and verify the *whole* INI without modifying active stations."""
        parser = configparser.ConfigParser(interpolation=None, strict=True);
        if not self.config.is_file():
            raise ValueError('Configuration file missing: ' + str(self.config));
        try:
            with self.config.open('r', encoding='utf-8') as stream:
                parser.read_file(stream);
        except (configparser.Error, UnicodeError, OSError) as error:
            raise ValueError('Invalid INI: ' + str(error)) from error;
        proposed = {};
        for section in parser.sections():
            if not section.startswith('route:'):
                raise ValueError('Unsupported section: ' + section);
            route = self.valid_route(section[6:]);
            unknown = set(parser.options(section)) - {'source', 'category', 'loop'};
            if unknown:
                raise ValueError('Unknown option(s) in ' + section + ': ' + ', '.join(sorted(unknown)));
            if not parser.has_option(section, 'source'):
                raise ValueError('Missing source in ' + section);
            try: loop = parser.getboolean(section, 'loop', fallback=True);
            except ValueError as error: raise ValueError('Invalid loop in ' + section) from error;
            if not loop:
                raise ValueError('Finite file playback not implemented: ' + section);
            source = Path(parser.get(section, 'source')).expanduser().resolve();
            if not source.is_file():
                raise ValueError('Missing source for ' + section + ': ' + str(source));
            if not os.access(source, os.R_OK):
                raise ValueError('Unreadable source for ' + section + ': ' + str(source));
            # A readable file is not necessarily decodable audio: probe before deployment.
            try:
                probe = subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-i', str(source), '-t', '0.05', '-f', 'null', '-'],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE, timeout=8, check=False);
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError('Cannot probe ' + section + ': ' + str(error)) from error;
            if probe.returncode != 0:
                raise ValueError('Invalid audio in ' + section + ': ' + probe.stderr.decode('utf-8', 'replace')[:300].strip());
            proposed[route] = {'category': parser.get(section, 'category', fallback=''), 'source': str(source)};
        return proposed;

    def try_config(self):
        # Hold the lock to provide a coherent comparison with the current registry.
        with self.lock:
            proposed = self.inspect_config();
            old = {route: station for route, station in self.routes.items() if station.mode == 'file'};
            changed = [route for route, data in proposed.items() if route not in old or old[route].source != data['source'] or old[route].category != data['category']];
            removed = [route for route in old if route not in proposed];
            collisions = [route for route in proposed if route in self.routes and self.routes[route].mode != 'file'];
            if collisions: raise ValueError('Configured routes collide with live streams: ' + ', '.join(collisions));
            return {'valid': True, 'file_routes': len(proposed), 'will_start_or_replace': changed, 'will_remove': removed};

    def reload(self):
        """Stage new producers then switch routes atomically; never save the INI."""
        with self.lock:
            summary = self.try_config();
            proposed = self.inspect_config();
            staged = {};
            old_to_stop = [];
            try:
                for route, data in proposed.items():
                    current = self.routes.get(route);
                    if current is not None and current.mode == 'file' and current.source == data['source'] and current.category == data['category'] and not current.ended:
                        continue;
                    station = Station(route, data['category'], data['source'], 'file', self.ffmpeg);
                    station.start();
                    # Detect immediately failed FFmpeg processes before changing the registry.
                    if station.process.poll() is not None:
                        raise ValueError('Encoder exited for ' + route);
                    staged[route] = station;
                updated = dict(self.routes);
                for route, current in self.routes.items():
                    if current.mode == 'file' and (route not in proposed or route in staged):
                        updated.pop(route, None);
                        old_to_stop.append(current);
                updated.update(staged);
                self.routes = updated;
            except Exception:
                for station in staged.values(): station.stop();
                raise;
        for station in old_to_stop: station.stop();
        return {'ok': True, 'configuration': summary, 'active_routes': len(self.routes)};

    def restore(self):
        if not self.config.exists(): return;
        try:
            proposed = self.inspect_config();
            for route, data in proposed.items():
                self.add(route, data['category'], data['source'], persist=False);
        except (ValueError, OSError) as error:
            raise ValueError('Startup configuration invalid; no partial restore: ' + str(error)) from error;

class PublicHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1';
    def do_GET(self):
        route = urlsplit(self.path).path;
        if route == '/':
            self.send_response(302);
            self.send_header('Location', '/signal');
            self.send_header('Content-Length', '0');
            self.end_headers();
            return;
        if route == '/health':
            payload = b'OK\n';
            self.send_response(200);
            self.send_header('Content-Length', str(len(payload)));
            self.end_headers();
            self.wfile.write(payload);
            return;
        with self.server.registry.lock:
            station = self.server.registry.signal if route == '/signal' else self.server.registry.routes.get(route);
        if station is None:
            self.send_error(404);
            return;
        with station.lock:
            position = station.counter;
            station.listeners += 1;
        try:
            self.send_response(200);
            self.send_header('Content-Type', 'audio/mpeg');
            self.send_header('icy-name', station.category);
            self.send_header('icy-description', 'sumAudio continuous broadcast');
            self.send_header('Cache-Control', 'no-store, no-transform');
            self.send_header('Connection', 'close');
            self.end_headers();
            while True:
                data, position = station.read(position);
                if data is None:
                    break;
                self.wfile.write(data);
                self.wfile.flush();
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            pass;
        finally:
            with station.lock:
                station.listeners -= 1;

    def log_message(self, fmt, *args):
        print('access ' + self.address_string() + ' ' + fmt % args, flush=True);

class AdminHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1';
    def _authorized(self):
        if not hmac.compare_digest(self.headers.get('X-Sum-Audio-Token', ''), self.server.registry.token):
            self.send_error(403);
            return False;
        return True;

    def _respond(self, code, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8');
        self.send_response(code);
        self.send_header('Content-Type', 'application/json; charset=utf-8');
        self.send_header('Content-Length', str(len(payload)));
        self.end_headers();
        self.wfile.write(payload);

    def do_GET(self):
        if not self._authorized(): return;
        if self.path != '/status': return self._respond(404, {'error': 'unknown command'});
        self._respond(200, {'routes': self.server.registry.status()});

    def do_POST(self):
        if not self._authorized(): return;
        path = urlsplit(self.path).path;
        if path == '/live': return self._live();
        if path in ('/try', '/reload'):
            try:
                result = self.server.registry.try_config() if path == '/try' else self.server.registry.reload();
                return self._respond(200, result);
            except (ValueError, OSError) as error:
                return self._respond(400, {'valid': False, 'error': str(error)});
        if path == '/stop':
            self._respond(200, {'ok': True, 'message': 'Daemon shutdown requested'});
            threading.Thread(target=self.server.public.shutdown, daemon=True).start();
            return;
        try:
            size = int(self.headers.get('Content-Length', '0'));
            if size < 0 or size > 65536: raise ValueError('Invalid request size');
            data = json.loads(self.rfile.read(size));
            if path == '/add':
                result = self.server.registry.add(data['route'], data.get('category', ''), data['source']);
                return self._respond(200, result);
            if path == '/remove':
                self.server.registry.remove(data['route']);
                return self._respond(200, {'ok': True});
            return self._respond(404, {'error': 'unknown command'});
        except (ValueError, KeyError, json.JSONDecodeError, OSError) as error:
            return self._respond(400, {'error': str(error)});

    def _live(self):
        from urllib.parse import parse_qs;
        query = parse_qs(urlsplit(self.path).query);
        route = query.get('route', [''])[0];
        category = query.get('category', [''])[0];
        source_format = query.get('format', ['wav'])[0];
        sample_rate = int(query.get('sample_rate', ['48000'])[0]);
        if source_format not in ('wav', 'mp3', 'raw') or not 8000 <= sample_rate <= 192000:
            return self._respond(400, {'error': 'invalid live format or sample rate'});
        try:
            station = self.server.registry.live(route, category, source_format, sample_rate);
        except (ValueError, OSError) as error:
            return self._respond(400, {'error': str(error)});
        try:
            if self.headers.get('Transfer-Encoding', '').lower() != 'chunked':
                raise ValueError('Live input requires chunked transfer encoding');
            while True:
                line = self.rfile.readline(128);
                if not line: break;
                size = int(line.strip().split(b';', 1)[0], 16);
                if size == 0:
                    while True:
                        if self.rfile.readline(8192) in (b'\r\n', b'\n', b''): break;
                    break;
                if size > 65536: raise ValueError('Chunk too large');
                data = self.rfile.read(size);
                if len(data) != size or self.rfile.read(2) != b'\r\n': raise ValueError('Invalid chunk');
                station.process.stdin.write(data);
            station.process.stdin.close();
            station.process.wait(timeout=15);
            return self._respond(200, {'ok': True, 'route': route});
        except (BrokenPipeError, ValueError, OSError, TimeoutError) as error:
            return self._respond(400, {'error': str(error)});
        finally:
            with self.server.registry.lock:
                if self.server.registry.routes.get(route) is station:
                    self.server.registry.routes.pop(route);
            station.stop();

    def log_message(self, fmt, *args):
        print('admin ' + fmt % args, flush=True);

def main():
    parser = argparse.ArgumentParser(description='sum audio broadcast daemon');
    parser.add_argument('--port', type=int, default=53845);
    parser.add_argument('--host', default='127.0.0.1');
    parser.add_argument('--admin-port', type=int);
    parser.add_argument('--config', default='server.ini');
    parser.add_argument('--token-file', default='server.token');
    args = parser.parse_args();
    if not shutil.which('ffmpeg'): parser.error('ffmpeg is required');
    registry = Registry(args.config, args.token_file, shutil.which('ffmpeg'));
    admin_port = args.admin_port if args.admin_port is not None else args.port + 1;
    admin = ThreadingHTTPServer(('127.0.0.1', admin_port), AdminHandler);
    admin.registry = registry;
    public = ThreadingHTTPServer((args.host, args.port), PublicHandler);
    public.registry = registry;
    admin.public = public;
    thread = threading.Thread(target=admin.serve_forever, daemon=True);
    thread.start();
    print('Audio HTTP listening at %s:%d; admin loopback at 127.0.0.1:%d' % (args.host, args.port, admin_port), flush=True);
    try: public.serve_forever();
    except KeyboardInterrupt: pass;
    finally:
        public.server_close();
        admin.shutdown();
        admin.server_close();
        for station in list(registry.routes.values()): station.stop();
        registry.signal.stop();

if __name__ == '__main__': main();
