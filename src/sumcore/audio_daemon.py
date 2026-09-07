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
"""Portable IPC audio daemon for the Sum ecosystem.

The protocol is deliberately backend-neutral.  POSIX hosts use an AF_UNIX
socket; Windows uses localhost TCP.  The daemon owns one persistent PCM output
and mixes named voices so every Sum language can share the same low-latency
audio service.
""";

import argparse;
import json;
import math;
import os;
import shutil;
import socket;
import struct;
import subprocess;
import sys;
import tempfile;
import threading;
import time;
import uuid;

PROTOCOL_VERSION = 1;
DEFAULT_SAMPLE_RATE = 48000;
DEFAULT_RELEASE_MS = 8;
DEFAULT_CHUNK_MS = 10;


def _is_termux_environment():
    prefix = str(os.environ.get("PREFIX", ""));
    return bool(os.environ.get("TERMUX_VERSION") or "/com.termux/" in prefix or prefix.endswith("/com.termux/files/usr"));


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on", "enable", "enabled");


def default_endpoint():
    if os.name == "nt":
        port = int(os.environ.get("SUM_AUDIO_PORT", "45837"));
        return {"kind": "tcp", "host": "127.0.0.1", "port": port};
    explicit = os.environ.get("SUM_AUDIO_SOCKET");
    if explicit:
        path = explicit;
    else:
        runtime = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or tempfile.gettempdir();
        try: uid = os.getuid();
        except AttributeError: uid = 0;
        path = os.path.join(runtime, "sumaudiod-{}.sock".format(uid));
    return {"kind": "unix", "path": path};


def _connect(endpoint, timeout=1.0):
    if endpoint.get("kind") == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        sock.settimeout(float(timeout));
        sock.connect((endpoint.get("host", "127.0.0.1"), int(endpoint.get("port", 45837))));
        return sock;
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);
    sock.settimeout(float(timeout));
    sock.connect(endpoint["path"]);
    return sock;


def _recv_line(sock, limit=1024 * 1024):
    data = bytearray();
    while len(data) < limit:
        chunk = sock.recv(4096);
        if not chunk: break;
        data.extend(chunk);
        if b"\n" in chunk: break;
    raw = bytes(data).split(b"\n", 1)[0];
    if not raw: return {};
    return json.loads(raw.decode("utf-8"));


def _send_json(sock, payload):
    wire = (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8");
    sock.sendall(wire);
    return None;


class PersistentPCMOutput:
    """One long-lived raw PCM subprocess selected from available host tools.""";
    def __init__(self, sample_rate=DEFAULT_SAMPLE_RATE, channels=1):
        self.sample_rate = int(sample_rate);
        self.channels = int(channels);
        self.process = None;
        self.backend = None;
        self.sink = None;
        self.command = None;
        self.last_error = None;
        self._lock = threading.Lock();

    @staticmethod
    def pulse_sinks():
        pactl = shutil.which("pactl");
        if not pactl: return [];
        try:
            result = subprocess.run([pactl, "list", "short", "sinks"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5, check=False);
        except (OSError, subprocess.SubprocessError):
            return [];
        if result.returncode != 0: return [];
        sinks = [];
        for line in result.stdout.splitlines():
            tab_fields = line.split("\t");
            if len(tab_fields) >= 2:
                item = {"id": tab_fields[0], "name": tab_fields[1], "raw": line};
                if len(tab_fields) > 2: item["driver"] = tab_fields[2];
                if len(tab_fields) > 3: item["sample_spec"] = tab_fields[3];
                if len(tab_fields) > 4: item["channel_map"] = tab_fields[4];
                if len(tab_fields) > 5: item["owner_module"] = tab_fields[5];
                if len(tab_fields) > 6: item["state"] = tab_fields[6];
                sinks.append(item);
                continue;
            fields = line.split();
            if len(fields) >= 2:
                item = {"id": fields[0], "name": fields[1], "raw": line};
                if len(fields) >= 4: item["driver"] = fields[2];
                if len(fields) >= 7:
                    item["sample_spec"] = " ".join(fields[3:6]);
                    item["state"] = fields[-1];
                sinks.append(item);
        return sinks;

    @classmethod
    def preferred_pulse_sink(cls):
        explicit = str(os.environ.get("SUM_AUDIO_SINK", "")).strip();
        if explicit: return explicit;
        names = [item["name"] for item in cls.pulse_sinks()];
        for wanted in ("AAudio_sink", "OpenSL_ES_sink"):
            if wanted in names: return wanted;
        for name in names:
            if "auto_null" not in name.lower(): return name;
        return None;

    def _candidate_commands(self):
        result = [];
        pacat = shutil.which("pacat");
        sink = self.preferred_pulse_sink();
        if pacat:
            command = [pacat, "--playback", "--raw", "--format=s16le", "--rate={}".format(self.sample_rate), "--channels={}".format(self.channels), "--client-name=Sum", "--stream-name=SumAudio"];
            if sink: command.append("--device={}".format(sink));
            result.append(("pulseaudio/pacat", sink, command));
        player = shutil.which("play");
        if player:
            command = [player, "-q", "-t", "raw", "-r", str(self.sample_rate), "-e", "signed-integer", "-b", "16", "-c", str(self.channels), "-L", "-"];
            result.append(("sox/play", None, command));
        aplay = shutil.which("aplay");
        if aplay:
            command = [aplay, "-q", "-t", "raw", "-f", "S16_LE", "-c", str(self.channels), "-r", str(self.sample_rate), "-"];
            result.append(("alsa/aplay", None, command));
        return result;

    def open(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None and self.process.stdin is not None: return True;
            self.close();
            for backend, sink, command in self._candidate_commands():
                try:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE);
                    time.sleep(.035);
                    if process.poll() is not None or process.stdin is None:
                        stderr = b"";
                        try: stderr = process.stderr.read(4096) if process.stderr is not None else b"";
                        except Exception: pass;
                        self.last_error = stderr.decode("utf-8", "replace").strip() or "backend exited during startup";
                        try: process.kill();
                        except Exception: pass;
                        continue;
                    self.process = process;
                    self.backend = backend;
                    self.sink = sink;
                    self.command = list(command);
                    self.last_error = None;
                    return True;
                except OSError as exc:
                    self.last_error = str(exc);
            return False;

    def write(self, payload):
        if not payload: return True;
        if not self.open(): return False;
        with self._lock:
            try:
                self.process.stdin.write(payload);
                self.process.stdin.flush();
                return True;
            except (BrokenPipeError, OSError, ValueError) as exc:
                self.last_error = str(exc);
                self.close();
                return False;

    def close(self):
        process = self.process;
        self.process = None;
        if process is not None:
            try:
                if process.stdin is not None: process.stdin.close();
            except Exception: pass;
            try:
                if process.poll() is None: process.terminate();
            except Exception: pass;
            try: process.wait(timeout=.2);
            except Exception:
                try: process.kill();
                except Exception: pass;
        return None;

    def info(self):
        candidates = [{"backend": backend, "sink": sink, "command": command} for backend, sink, command in self._candidate_commands()];
        return {
            "backend": self.backend,
            "sink": self.sink,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "running": bool(self.process is not None and self.process.poll() is None),
            "command": self.command,
            "last_error": self.last_error,
            "candidates": candidates,
            "pulse_sinks": self.pulse_sinks(),
        };


class _Voice:
    def __init__(self, voice_id, frequency, volume, sample_rate, duration=None, release_ms=DEFAULT_RELEASE_MS):
        self.voice_id = str(voice_id);
        self.frequency = float(frequency);
        self.volume = max(0.0, min(3.0, float(volume)));
        self.sample_rate = int(sample_rate);
        self.phase = 0.0;
        self.remaining = None if duration is None else max(0, int(round(float(duration) * self.sample_rate)));
        self.release_total = max(1, int(round(self.sample_rate * max(0, int(release_ms)) / 1000.0)));
        self.release_remaining = None;
        self.done = threading.Event();

    def request_stop(self):
        if self.release_remaining is None:
            self.release_remaining = self.release_total;
        return None;

    def sample(self):
        gain = 1.0;
        if self.release_remaining is not None:
            gain = max(0.0, self.release_remaining / float(self.release_total));
        elif self.remaining is not None and self.remaining <= self.release_total:
            gain = max(0.0, self.remaining / float(self.release_total));
        value = math.sin(self.phase) * self.volume * gain;
        self.phase += (2.0 * math.pi * self.frequency) / float(self.sample_rate);
        if self.phase > 2.0 * math.pi: self.phase -= 2.0 * math.pi;
        if self.remaining is not None and self.remaining > 0: self.remaining -= 1;
        if self.release_remaining is not None: self.release_remaining -= 1;
        natural_done = self.remaining is not None and self.remaining <= 0;
        stopped_done = self.release_remaining is not None and self.release_remaining <= 0;
        return value, bool(natural_done or stopped_done);


class AudioMixer:
    """Realtime sine mixer writing silence while idle to keep the host stream hot.""";
    def __init__(self, output=None, sample_rate=DEFAULT_SAMPLE_RATE, release_ms=DEFAULT_RELEASE_MS, chunk_ms=DEFAULT_CHUNK_MS):
        self.sample_rate = int(sample_rate);
        self.release_ms = int(release_ms);
        self.chunk_frames = max(32, int(round(self.sample_rate * float(chunk_ms) / 1000.0)));
        self.output = output if output is not None else PersistentPCMOutput(self.sample_rate, 1);
        self._voices = {};
        self._lock = threading.RLock();
        self._stop = threading.Event();
        self._thread = None;
        self._started_at = None;

    def start(self):
        if self._thread is not None and self._thread.is_alive(): return True;
        if not self.output.open(): return False;
        self._stop.clear();
        self._started_at = time.time();
        self._thread = threading.Thread(target=self._loop, name="sumaudiod-mixer", daemon=True);
        self._thread.start();
        return True;

    def close(self):
        self._stop.set();
        thread = self._thread;
        if thread is not None and thread is not threading.current_thread():
            try: thread.join(timeout=.5);
            except Exception: pass;
        with self._lock:
            for voice in self._voices.values(): voice.done.set();
            self._voices.clear();
        self.output.close();
        return None;

    def tone(self, voice_id, frequency, duration, volume=1.0):
        voice = _Voice(voice_id, frequency, volume, self.sample_rate, duration=duration, release_ms=self.release_ms);
        with self._lock:
            old = self._voices.get(str(voice_id));
            if old is not None: old.done.set();
            self._voices[str(voice_id)] = voice;
        return voice.done;

    def hold(self, voice_id, frequency, volume=1.0):
        return self.tone(voice_id, frequency, None, volume=volume);

    def stop_voice(self, voice_id=None):
        with self._lock:
            if voice_id is None:
                targets = list(self._voices.values());
            else:
                voice = self._voices.get(str(voice_id));
                targets = [] if voice is None else [voice];
            for voice in targets: voice.request_stop();
        return len(targets);

    def _loop(self):
        amplitude = 11000.0;
        interval = self.chunk_frames / float(self.sample_rate);
        while not self._stop.is_set():
            started = time.monotonic();
            frames = bytearray();
            finished = set();
            with self._lock:
                voices = list(self._voices.values());
                for unused_index in range(self.chunk_frames):
                    mixed = 0.0;
                    for voice in voices:
                        if voice.voice_id in finished: continue;
                        value, done = voice.sample();
                        mixed += value;
                        if done: finished.add(voice.voice_id);
                    sample = int(amplitude * mixed);
                    sample = max(-32768, min(32767, sample));
                    frames.extend(struct.pack("<h", sample));
                for voice_id in finished:
                    voice = self._voices.pop(voice_id, None);
                    if voice is not None: voice.done.set();
            if not self.output.write(bytes(frames)):
                time.sleep(.05);
            elapsed = time.monotonic() - started;
            self._stop.wait(max(0.0, interval - elapsed));
        return None;

    def info(self):
        with self._lock:
            voices = [{"id": item.voice_id, "frequency": item.frequency, "volume": item.volume, "held": item.remaining is None} for item in self._voices.values()];
        return {
            "sample_rate": self.sample_rate,
            "release_ms": self.release_ms,
            "chunk_frames": self.chunk_frames,
            "active_voices": voices,
            "uptime_seconds": None if self._started_at is None else max(0.0, time.time() - self._started_at),
            "output": self.output.info(),
        };


class AudioDaemonServer:
    def __init__(self, endpoint=None, mixer=None):
        self.endpoint = endpoint or default_endpoint();
        self.mixer = mixer if mixer is not None else AudioMixer();
        self.sock = None;
        self.stop_event = threading.Event();

    def _bind(self):
        if self.endpoint.get("kind") == "tcp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1);
            sock.bind((self.endpoint.get("host", "127.0.0.1"), int(self.endpoint.get("port", 45837))));
        else:
            path = self.endpoint["path"];
            try:
                if os.path.exists(path): os.unlink(path);
            except OSError: pass;
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);
            sock.bind(path);
            try: os.chmod(path, 0o600);
            except OSError: pass;
        sock.listen(16);
        sock.settimeout(.25);
        self.sock = sock;
        return sock;

    def serve_forever(self):
        if not self.mixer.start():
            raise RuntimeError("no persistent PCM backend available: {}".format(self.mixer.output.info().get("last_error") or "unknown error"));
        sock = self._bind();
        try:
            while not self.stop_event.is_set():
                try: client, unused_address = sock.accept();
                except socket.timeout: continue;
                except OSError:
                    if self.stop_event.is_set(): break;
                    raise;
                thread = threading.Thread(target=self._handle_client, args=(client,), daemon=True);
                thread.start();
        finally:
            try: sock.close();
            except Exception: pass;
            self.mixer.close();
            if self.endpoint.get("kind") == "unix":
                try: os.unlink(self.endpoint["path"]);
                except OSError: pass;
        return 0;

    def _handle_client(self, client):
        try:
            request = _recv_line(client);
            response = self.dispatch(request);
            _send_json(client, response);
        except Exception as exc:
            try: _send_json(client, {"ok": False, "error": str(exc)});
            except Exception: pass;
        finally:
            try: client.close();
            except Exception: pass;
        return None;

    def dispatch(self, request):
        command = str(request.get("command", "")).lower();
        if command in ("ping", "hello"):
            return {"ok": True, "protocol": PROTOCOL_VERSION, "pid": os.getpid()};
        if command == "info":
            return {"ok": True, "protocol": PROTOCOL_VERSION, "pid": os.getpid(), "endpoint": self.endpoint, "mixer": self.mixer.info()};
        if command == "tone":
            voice = str(request.get("voice") or uuid.uuid4().hex);
            duration = max(0.0, float(request.get("duration", 0.0)));
            done = self.mixer.tone(voice, float(request["frequency"]), duration, float(request.get("volume", 1.0)));
            if bool(request.get("blocking", True)):
                done.wait(duration + max(1.0, self.mixer.release_ms / 1000.0 + .5));
            return {"ok": True, "voice": voice};
        if command == "hold":
            voice = str(request.get("voice") or uuid.uuid4().hex);
            self.mixer.hold(voice, float(request["frequency"]), float(request.get("volume", 1.0)));
            return {"ok": True, "voice": voice};
        if command == "stop":
            voice = request.get("voice");
            count = self.mixer.stop_voice(None if voice in (None, "", "*") else str(voice));
            return {"ok": True, "stopped": count};
        if command == "shutdown":
            self.stop_event.set();
            return {"ok": True};
        return {"ok": False, "error": "unknown command {!r}".format(command)};


class AudioDaemonClient:
    def __init__(self, endpoint=None, timeout=1.0):
        self.endpoint = endpoint or default_endpoint();
        self.timeout = float(timeout);

    def request(self, payload, timeout=None):
        sock = _connect(self.endpoint, timeout=self.timeout if timeout is None else timeout);
        try:
            _send_json(sock, payload);
            return _recv_line(sock);
        finally:
            try: sock.close();
            except Exception: pass;

    def ping(self):
        try: response = self.request({"command": "ping"});
        except (OSError, ValueError, socket.error): return False;
        return bool(response.get("ok") and int(response.get("protocol", 0)) == PROTOCOL_VERSION);

    def info(self): return self.request({"command": "info"});

    def tone(self, voice, frequency, duration, volume=1.0, blocking=True):
        timeout = max(self.timeout, float(duration) + 2.0) if blocking else self.timeout;
        return self.request({"command": "tone", "voice": str(voice), "frequency": float(frequency), "duration": float(duration), "volume": float(volume), "blocking": bool(blocking)}, timeout=timeout);

    def hold(self, voice, frequency, volume=1.0):
        return self.request({"command": "hold", "voice": str(voice), "frequency": float(frequency), "volume": float(volume)});

    def stop(self, voice=None):
        return self.request({"command": "stop", "voice": "*" if voice is None else str(voice)});

    def shutdown(self): return self.request({"command": "shutdown"});


def _spawn_daemon_process():
    argv = [sys.executable, "-m", "sumcore.audio_daemon", "serve"];
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True};
    if os.name == "nt":
        detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008);
        new_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200);
        kwargs["creationflags"] = detached | new_group;
    else:
        kwargs["start_new_session"] = True;
    try: subprocess.Popen(argv, **kwargs);
    except OSError: return False;
    return True;


def ensure_audio_daemon(start=True, timeout=2.0):
    client = AudioDaemonClient(timeout=.25);
    if client.ping(): return client;
    if not start: return None;
    if not _spawn_daemon_process(): return None;
    deadline = time.monotonic() + max(.2, float(timeout));
    while time.monotonic() < deadline:
        time.sleep(.05);
        if client.ping(): return client;
    return None;


def daemon_autostart_enabled():
    policy = str(os.environ.get("SUM_AUDIO_DAEMON", "auto")).strip().lower();
    if policy in ("0", "false", "no", "off", "disable", "disabled"): return False;
    if policy in ("1", "true", "yes", "on", "enable", "enabled"): return True;
    return _is_termux_environment();


def _main_start():
    client = ensure_audio_daemon(start=True, timeout=3.0);
    if client is None:
        print("sumaudiod: could not start persistent audio backend", file=sys.stderr);
        return 1;
    info = client.info();
    mixer = info.get("mixer", {});
    output = mixer.get("output", {});
    print("sumaudiod: running pid={} backend={} sink={}".format(info.get("pid"), output.get("backend") or "unknown", output.get("sink") or "default"));
    return 0;


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sumaudiod", description="Persistent audio daemon from sumCore.");
    sub = parser.add_subparsers(dest="command");
    sub.add_parser("start", help="start the daemon in the background");
    sub.add_parser("serve", help="run the daemon in the foreground");
    sub.add_parser("status", help="show daemon status");
    sub.add_parser("stop", help="stop the daemon");
    args = parser.parse_args(argv);
    command = args.command or "start";
    if command == "serve":
        server = AudioDaemonServer();
        try: return server.serve_forever();
        except KeyboardInterrupt: return 130;
        except RuntimeError as exc:
            print("sumaudiod: {}".format(exc), file=sys.stderr);
            return 1;
    client = AudioDaemonClient(timeout=.5);
    if command == "start": return _main_start();
    if command == "status":
        if not client.ping():
            print("sumaudiod: stopped");
            return 1;
        info = client.info();
        output = info.get("mixer", {}).get("output", {});
        print("sumaudiod: running pid={} backend={} sink={}".format(info.get("pid"), output.get("backend") or "unknown", output.get("sink") or "default"));
        return 0;
    if command == "stop":
        if not client.ping():
            print("sumaudiod: already stopped");
            return 0;
        client.shutdown();
        print("sumaudiod: stopped");
        return 0;
    return 2;


if __name__ == "__main__":
    raise SystemExit(main());
