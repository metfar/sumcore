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
"""Runtime diagnostics for real, software and Sum-simulated capabilities.""";

import argparse;
import importlib.metadata;
import json;
import os;
import platform;
import shutil;
import subprocess;
import sys;

from . import __version__;
from .audio_daemon import AudioDaemonClient, DEFAULT_RELEASE_MS, DEFAULT_SAMPLE_RATE, PersistentPCMOutput, default_endpoint;

_SUM_PACKAGES = ("sumcore", "sumui", "sumtui", "sumgui", "sumide", "sumbasic", "sumx", "sumpy", "sumr", "sumdata", "sumplot", "sumdiff", "sumdoc");


def _command_json(command, timeout=2.0):
    executable = shutil.which(command[0]);
    if not executable: return None;
    argv = [executable] + list(command[1:]);
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=float(timeout), check=False);
    except (OSError, subprocess.SubprocessError):
        return None;
    if result.returncode != 0: return None;
    try: return json.loads(result.stdout);
    except (TypeError, ValueError): return None;


def _command_text(command, timeout=2.0):
    executable = shutil.which(command[0]);
    if not executable: return None;
    argv = [executable] + list(command[1:]);
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=float(timeout), check=False);
    except (OSError, subprocess.SubprocessError):
        return None;
    if result.returncode != 0: return None;
    return result.stdout.strip();


def _memory_total_bytes():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if line.startswith("MemTotal:"):
                    fields = line.split();
                    return int(fields[1]) * 1024;
    except (OSError, ValueError, IndexError):
        pass;
    return None;


def _installed_sum_versions():
    versions = {};
    for package in _SUM_PACKAGES:
        try: versions[package] = importlib.metadata.version(package);
        except importlib.metadata.PackageNotFoundError: pass;
    versions.setdefault("sumcore", __version__);
    return versions;


def _pygame_info():
    try:
        import pygame;
        return {"available": True, "version": getattr(pygame.version, "ver", None), "mixer": pygame.mixer.get_init()};
    except Exception:
        return {"available": False, "version": None, "mixer": None};


def _pulse_info():
    server = PersistentPCMOutput.pulse_server_info();
    sinks = PersistentPCMOutput.pulse_sinks();
    return {
        "available": bool(server is not None),
        "pacat": shutil.which("pacat"),
        "server_info": server,
        "sinks": sinks,
        "default_sink": PersistentPCMOutput.pulse_default_sink(),
        "preferred_sink": PersistentPCMOutput.preferred_pulse_sink(),
    };


def _os_release():
    values = {};
    try:
        for line in open("/etc/os-release", "r", encoding="utf-8", errors="replace"):
            text = line.strip();
            if not text or text.startswith("#") or "=" not in text: continue;
            key, value = text.split("=", 1);
            values[key] = value.strip().strip('"').strip("'");
    except OSError:
        pass;
    return values;


def _platform_profile(android=None):
    architecture = platform.machine() or "unknown";
    is_android = bool(os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION")) if android is None else bool(android);
    if is_android:
        termux = str(os.environ.get("TERMUX_VERSION", "")).strip();
        distribution = "google-play" if termux.lower().startswith("googleplay") else ("fdroid" if termux else "unknown");
        environment = "termux" if termux or "/com.termux/" in str(os.environ.get("PREFIX", "")) else "android";
        profile = "android-{}-{}-{}".format(environment, distribution, architecture);
        return {"family": "android", "environment": environment, "distribution": distribution, "architecture": architecture, "profile": profile};
    system = (platform.system() or "unknown").lower();
    release = _os_release();
    distribution = str(release.get("ID") or "unknown").lower();
    environment = "desktop" if bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")) else "console";
    profile = "{}-{}-{}-{}".format(system, distribution, environment, architecture);
    return {"family": system, "environment": environment, "distribution": distribution, "architecture": architecture, "profile": profile};


def _daemon_info():
    client = AudioDaemonClient(timeout=.25);
    try:
        if client.ping(): return client.info();
    except Exception: pass;
    return {"ok": False, "running": False, "endpoint": default_endpoint()};


def collect_info():
    termux_audio = _command_json(["termux-audio-info"]);
    term = str(os.environ.get("TERM", ""));
    term_program = str(os.environ.get("TERM_PROGRAM", ""));
    kitty = bool(os.environ.get("KITTY_WINDOW_ID") or "kitty" in term.lower() or "kitty" in term_program.lower());
    android = bool(os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION"));
    hardware = {
        "architecture": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "memory_total_bytes": _memory_total_bytes(),
        "android_audio": termux_audio,
    };
    software = {
        "platform_profile": _platform_profile(android),
        "os": platform.system(),
        "os_release": platform.release(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "android": android,
        "termux_version": os.environ.get("TERMUX_VERSION"),
        "termux_prefix": os.environ.get("PREFIX") if os.environ.get("TERMUX_VERSION") else None,
        "terminal": {"TERM": term or None, "TERM_PROGRAM": term_program or None, "tty": bool(sys.stdin.isatty()), "kitty_protocol_likely": kitty},
        "pygame": _pygame_info(),
        "pulseaudio": _pulse_info(),
        "persistent_audio": PersistentPCMOutput(DEFAULT_SAMPLE_RATE, 1).info(),
        "commands": {name: shutil.which(name) for name in ("pacat", "pactl", "play", "aplay", "termux-media-player", "termux-audio-info")},
        "sum_packages": _installed_sum_versions(),
    };
    daemon = _daemon_info();
    simulated = {
        "sumcore_version": __version__,
        "audio": {
            "internal_sample_rate": DEFAULT_SAMPLE_RATE,
            "pcm_format": "s16le mono",
            "release_ms": DEFAULT_RELEASE_MS,
            "maximum_gain_percent": 300,
            "beep": "ZX Spectrum duration,pitch semantics",
            "sound": "GW-BASIC frequency,ticks semantics",
            "play": "ZX PLAY and GW PLAY music strings",
            "zx_octaves": "O0..O10",
            "polyphony": 3,
            "daemon": daemon,
        },
        "keyboard": {
            "gui_keyup": "physical when frontend supplies release events",
            "tty_keyup": "physical only with extended terminal protocol; otherwise heuristic",
            "keyrepeat_control": "physical in GUI/extended protocols; backlog coalescing on legacy TTY",
        },
    };
    return {"hardware": hardware, "software": software, "simulated": simulated};


def _format_value(value):
    if value is None: return "n/a";
    if isinstance(value, bool): return "yes" if value else "no";
    if isinstance(value, (dict, list)): return json.dumps(value, sort_keys=True);
    return str(value);


def _flatten(prefix, value, rows):
    if isinstance(value, dict):
        for key, item in value.items():
            label = "{}.{}".format(prefix, key) if prefix else str(key);
            _flatten(label, item, rows);
        return rows;
    if isinstance(value, list):
        if not value:
            rows.append((prefix, "[]"));
        else:
            for index, item in enumerate(value): _flatten("{}[{}]".format(prefix, index), item, rows);
        return rows;
    rows.append((prefix, _format_value(value)));
    return rows;


def render_text(info):
    lines = [];
    for section in ("hardware", "software", "simulated"):
        lines.append(section.upper());
        rows = _flatten("", info.get(section, {}), []);
        width = max([len(key) for key, unused in rows] + [1]);
        for key, value in rows: lines.append("  {:{width}} : {}".format(key, value, width=width));
        lines.append("");
    return "\n".join(lines).rstrip();


def main(argv=None):
    parser = argparse.ArgumentParser(prog="suminfo", description="Show real hardware, software environment and Sum-simulated capabilities.");
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON");
    args = parser.parse_args(argv);
    info = collect_info();
    if args.json: print(json.dumps(info, indent=2, sort_keys=True));
    else: print(render_text(info));
    return 0;


if __name__ == "__main__":
    raise SystemExit(main());
