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
"""Passive runtime and environment inspection for the SUM ecosystem.

Observation contract
====================
``suminfo`` is intentionally an observer.  Collectors may read, query,
enumerate, classify and compare.  They must not install/remove/upgrade
software, refresh repositories, rewrite configuration, start/stop services,
change permissions, request privilege elevation, or otherwise deliberately
change persistent system state.

Some observation has unavoidable transient effects (a process is created,
files may enter the OS cache, etc.).  The contract is therefore *no
intentional persistent mutation*, not the physically impossible promise of
zero perturbation.

Windows
=======
Windows is recognised only as a preview/unsupported platform.  Current code
must work as an ordinary, non-Administrator user and must never trigger UAC.
Future Windows probes belong behind explicit collectors and should remain
user-readable and failure-tolerant.  Do not grow Registry/WMI/package-manager
heuristics until Windows becomes an explicit tested SUM target.
""";

import argparse;
from collections import Counter;
from dataclasses import dataclass;
from datetime import datetime, timezone;
import importlib.metadata;
import json;
import os;
from pathlib import Path;
import platform;
import re;
import shutil;
import subprocess;
import sys;

from . import __version__;
from .audio_daemon import AudioDaemonClient, DEFAULT_RELEASE_MS, DEFAULT_SAMPLE_RATE, PersistentPCMOutput, default_endpoint;

_SUM_PACKAGES = ("sumcore", "sumui", "sumtui", "sumgui", "sumide", "sumbasic", "sumx", "sumpy", "sumr", "sumdata", "sumplot", "sumdiff", "sumdoc");
GROUPS = ("platform", "hardware", "software", "terminal", "audio", "packages", "themes", "sum", "simulated");


@dataclass(frozen=True)
class CollectorPolicy:
    """Machine-checkable declaration for passive collectors.""";
    mutates_state: bool = False;
    requires_privilege: bool = False;
    uses_network: bool = False;

    def validate(self):
        if self.mutates_state or self.requires_privilege or self.uses_network:
            raise ValueError("suminfo collectors must be local, unprivileged and non-mutating");
        return self;


PASSIVE_POLICY = CollectorPolicy().validate();


def _run(command, timeout=2.0):
    executable = shutil.which(command[0]);
    if not executable: return None;
    argv = [executable] + list(command[1:]);
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=float(timeout), check=False);
    except (OSError, subprocess.SubprocessError):
        return None;


def _command_json(command, timeout=2.0):
    result = _run(command, timeout=timeout);
    if result is None or result.returncode != 0: return None;
    try: return json.loads(result.stdout);
    except (TypeError, ValueError): return None;


def _command_text(command, timeout=2.0):
    result = _run(command, timeout=timeout);
    if result is None or result.returncode != 0: return None;
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
    system = (platform.system() or "unknown").lower();
    is_android = bool(os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION")) if android is None else bool(android);
    if is_android:
        termux = str(os.environ.get("TERMUX_VERSION", "")).strip();
        distribution = "google-play" if termux.lower().startswith("googleplay") else ("fdroid" if termux else "unknown");
        environment = "termux" if termux or "/com.termux/" in str(os.environ.get("PREFIX", "")) else "android";
        profile = "android-{}-{}-{}".format(environment, distribution, architecture);
        return {"family": "android", "environment": environment, "distribution": distribution, "architecture": architecture, "profile": profile, "support": "supported"};
    if system == "windows":
        # Preview only.  Keep this deliberately boring and standard-user safe.
        return {"family": "windows", "environment": "desktop", "distribution": "windows", "architecture": architecture, "profile": "windows-preview-{}".format(architecture), "support": "unsupported", "privilege_assumption": "standard-user"};
    release = _os_release();
    distribution = str(release.get("ID") or "unknown").lower();
    environment = "desktop" if bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")) else "console";
    profile = "{}-{}-{}-{}".format(system, distribution, environment, architecture);
    return {"family": system, "environment": environment, "distribution": distribution, "architecture": architecture, "profile": profile, "support": "supported" if system == "linux" else "experimental"};


def _daemon_info():
    client = AudioDaemonClient(timeout=.25);
    try:
        if client.ping(): return client.info();
    except Exception: pass;
    return {"ok": False, "running": False, "endpoint": default_endpoint()};


def _version_stability(version):
    text = str(version or "").strip().lower();
    if not text: return "unknown";
    try:
        from packaging.version import Version;
        value = Version(text);
        if value.is_devrelease: return "development";
        if value.is_prerelease: return "prerelease";
        return "stable";
    except Exception:
        if re.search(r"(?:^|[.\-+_~])(dev|snapshot|git)\d*", text): return "development";
        if re.search(r"(?:^|[.\-+_~])(a|alpha|b|beta|rc|pre|preview)\d*", text): return "prerelease";
        return "stable";


def _os_version_channel(version):
    text = str(version or "").lower();
    if re.search(r"(?:alpha|beta|~rc|~pre|~dev|snapshot|\+git|~git)", text): return "development";
    return "distribution";


def _distribution_path(dist):
    path = getattr(dist, "_path", None);
    if path is not None: return str(path);
    try: return str(dist.locate_file(""));
    except Exception: return "";


def _dpkg_owners(paths):
    """Return exact dpkg owners using bounded batches instead of N probes.""";
    values = [str(path) for path in paths if path];
    if not values or not shutil.which("dpkg-query"): return {};
    owners = {};
    # Keep argv comfortably below platform command-line limits.  dpkg-query -S
    # is a read-only local database query; no apt/pkg refresh is performed.
    for start in range(0, len(values), 120):
        batch = values[start:start + 120];
        result = _run(["dpkg-query", "-S"] + batch, timeout=3.0);
        if result is None: continue;
        for line in (result.stdout or "").splitlines():
            if ": " not in line: continue;
            owner, found = line.split(": ", 1);
            if found in batch: owners[found] = owner.strip() or None;
    return owners;


def _python_distribution_record(dist, detailed=False):
    name = str(dist.metadata.get("Name") or getattr(dist, "name", "") or "unknown");
    version = str(getattr(dist, "version", "") or "");
    location = _distribution_path(dist);
    try: installer = str(dist.read_text("INSTALLER") or "").strip().lower();
    except Exception: installer = "";
    try: direct = json.loads(dist.read_text("direct_url.json") or "null");
    except Exception: direct = None;
    owner = None;
    origin = "unknown";
    source = "";
    if owner:
        origin = "os-package";
        source = owner;
    elif isinstance(direct, dict):
        url = str(direct.get("url") or "");
        directory = dict(direct.get("dir_info") or {});
        vcs = dict(direct.get("vcs_info") or {});
        if vcs:
            origin = "vcs";
            source = url;
        elif url.startswith("file:"):
            origin = "pip-editable" if bool(directory.get("editable")) else "pip-local";
            source = url;
        else:
            origin = "pip" if installer == "pip" else (installer or "direct");
            source = url;
    elif installer:
        # Debian/Ubuntu and Termux may stamp Python metadata with the OS
        # installer even when dpkg-query cannot map the metadata directory
        # itself.  This is still an OS-managed Python distribution.
        if installer in ("debian", "apt", "dpkg", "pkg", "termux"):
            origin = "os-package";
            source = installer;
        else:
            origin = "pip" if installer == "pip" else installer;
    elif location:
        origin = "direct";
    scope = "system";
    if location and sys.prefix != getattr(sys, "base_prefix", sys.prefix) and str(location).startswith(str(sys.prefix)):
        scope = "environment";
    elif location and str(Path.home()) in location:
        scope = "user";
    return {"name": name, "version": version, "stability": _version_stability(version), "origin": origin, "installer": installer or None, "owner": owner, "source": source or None, "scope": scope, "location": location or None};


def _python_packages(detailed=False):
    records = [];
    for dist in importlib.metadata.distributions():
        try: records.append(_python_distribution_record(dist, detailed=False));
        except Exception: continue;
    if detailed:
        owners = _dpkg_owners([item.get("location") for item in records]);
        for item in records:
            owner = owners.get(item.get("location"));
            if owner:
                item["owner"] = owner;
                item["origin"] = "os-package";
                item["source"] = owner;
    records.sort(key=lambda item: item["name"].casefold());
    origins = Counter(item["origin"] for item in records);
    stability = Counter(item["stability"] for item in records);
    scopes = Counter(item["scope"] for item in records);
    return {"count": len(records), "by_origin": dict(sorted(origins.items())), "by_stability": dict(sorted(stability.items())), "by_scope": dict(sorted(scopes.items())), "items": records if detailed else []};


def _os_packages(detailed=False):
    manager = "pkg/apt/dpkg" if bool(os.environ.get("TERMUX_VERSION")) and shutil.which("dpkg-query") else ("apt/dpkg" if shutil.which("dpkg-query") else None);
    if manager is None: return {"manager": None, "count": 0, "items": [], "status": "unavailable"};
    text = _command_text(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"], timeout=8.0 if detailed else 4.0);
    if text is None: return {"manager": manager, "count": 0, "items": [], "status": "unavailable"};
    rows = [];
    for line in text.splitlines():
        parts = line.split("\t", 1);
        if not parts or not parts[0].strip(): continue;
        rows.append({"name": parts[0].strip(), "version": parts[1].strip() if len(parts) > 1 else "", "channel": _os_version_channel(parts[1] if len(parts) > 1 else "")});
    manual = set();
    automatic = set();
    if detailed and shutil.which("apt-mark"):
        manual_text = _command_text(["apt-mark", "showmanual"], timeout=4.0);
        auto_text = _command_text(["apt-mark", "showauto"], timeout=4.0);
        manual = set((manual_text or "").splitlines());
        automatic = set((auto_text or "").splitlines());
        for row in rows:
            row["requested"] = "manual" if row["name"] in manual else ("automatic" if row["name"] in automatic else "unknown");
    channels = Counter(row["channel"] for row in rows);
    return {"manager": manager, "count": len(rows), "by_channel": dict(sorted(channels.items())), "items": rows if detailed else [], "status": "ok"};


def _scan_names(roots, glob_pattern="*", directory_only=True):
    names = set();
    paths = [];
    for root in roots:
        path = Path(os.path.expandvars(str(root))).expanduser();
        if not path.exists() or not path.is_dir(): continue;
        paths.append(str(path));
        try:
            for item in path.glob(glob_pattern):
                if directory_only and not item.is_dir(): continue;
                if not directory_only and not item.is_file(): continue;
                name = item.stem if item.is_file() else item.name;
                if name and not name.startswith("."): names.add(name);
        except OSError: continue;
    return sorted(names, key=str.casefold), paths;


def _theme_inventory():
    prefix = Path(os.environ.get("PREFIX", "/usr"));
    home = Path.home();
    sum_names = [];
    sum_paths = [];
    active_sum = None;
    try:
        from sumtui.theme import BUILTIN_THEME_NAMES, available_theme_names, user_theme_dir;
        sum_names = list(available_theme_names(include_hidden=True));
        sum_paths = [str(user_theme_dir())];
        try:
            state = user_theme_dir() / ".state.json";
            if state.is_file(): active_sum = json.loads(state.read_text(encoding="utf-8")).get("active");
        except Exception: active_sum = None;
        for name in BUILTIN_THEME_NAMES:
            if name not in sum_names: sum_names.append(name);
        sum_names = sorted(set(sum_names), key=str.casefold);
    except Exception:
        default_sum = home / ".config" / "sumtui" / "themes";
        found, sum_paths = _scan_names((default_sum,), "*.json", directory_only=False);
        sum_names = [name for name in found if name != ".state"];
    gtk_roots = (home / ".themes", home / ".local/share/themes", prefix / "share/themes", Path("/usr/share/themes"));
    gtk = set(); gnome = set(); xfce = set(); gtk_paths = [];
    for root in gtk_roots:
        root = Path(root).expanduser();
        if not root.is_dir(): continue;
        if str(root) not in gtk_paths: gtk_paths.append(str(root));
        try: children = list(root.iterdir());
        except OSError: continue;
        for child in children:
            if not child.is_dir() or child.name.startswith("."): continue;
            if any((child / name).exists() for name in ("gtk-2.0", "gtk-3.0", "gtk-4.0")): gtk.add(child.name);
            if (child / "gnome-shell").exists(): gnome.add(child.name);
            if any((child / name).exists() for name in ("xfwm4", "xfce-notify-4.0")): xfce.add(child.name);
    gtk = sorted(gtk, key=str.casefold);
    gnome = sorted(gnome, key=str.casefold);
    xfce = sorted(xfce, key=str.casefold);
    kde_roots = (home / ".local/share/color-schemes", prefix / "share/color-schemes", Path("/usr/share/color-schemes"));
    kde, kde_paths = _scan_names(kde_roots, "*.colors", directory_only=False);
    terminal = set();
    terminal_paths = [];
    for roots, pattern in (
        ((home / ".local/share/xfce4/terminal/colorschemes", prefix / "share/xfce4/terminal/colorschemes", Path("/usr/share/xfce4/terminal/colorschemes")), "*.theme"),
        ((home / ".local/share/konsole", prefix / "share/konsole", Path("/usr/share/konsole")), "*.colorscheme"),
    ):
        found, paths = _scan_names(roots, pattern, directory_only=False);
        terminal.update(found);
        terminal_paths.extend(paths);
    active_desktop = os.environ.get("GTK_THEME") or None;
    groups = {
        "sum": {"count": len(sum_names), "items": sum_names, "paths": sum_paths},
        "gtk": {"count": len(gtk), "items": gtk, "paths": gtk_paths},
        "gnome": {"count": len(gnome), "items": gnome, "paths": gtk_paths},
        "xfce": {"count": len(xfce), "items": xfce, "paths": gtk_paths},
        "kde": {"count": len(kde), "items": kde, "paths": kde_paths},
        "terminal": {"count": len(terminal), "items": sorted(terminal, key=str.casefold), "paths": sorted(set(terminal_paths))},
    };
    return {"active": {"sum": active_sum, "desktop": active_desktop}, "groups": groups, "unique_count": len(set(name.casefold() for group in groups.values() for name in group["items"]))};


def _platform_group():
    android = bool(os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION"));
    profile = _platform_profile(android);
    release = _os_release();
    return {
        "profile": profile,
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "platform": platform.platform(),
        "os_release": release,
    };


def _hardware_group():
    return {"architecture": platform.machine(), "processor": platform.processor() or None, "cpu_count": os.cpu_count(), "memory_total_bytes": _memory_total_bytes(), "android_audio": _command_json(["termux-audio-info"])};


def _software_group():
    return {"python": platform.python_version(), "implementation": platform.python_implementation(), "executable": sys.executable, "pygame": _pygame_info()};


def _terminal_group():
    term = str(os.environ.get("TERM", ""));
    term_program = str(os.environ.get("TERM_PROGRAM", ""));
    kitty = bool(os.environ.get("KITTY_WINDOW_ID") or "kitty" in term.lower() or "kitty" in term_program.lower());
    return {"TERM": term or None, "TERM_PROGRAM": term_program or None, "tty": bool(sys.stdin.isatty()), "kitty_protocol_likely": kitty, "desktop": os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")};


def _audio_group():
    return {"pulseaudio": _pulse_info(), "persistent_audio": PersistentPCMOutput(DEFAULT_SAMPLE_RATE, 1).info(), "daemon": _daemon_info(), "commands": {name: shutil.which(name) for name in ("pacat", "pactl", "play", "aplay", "termux-media-player", "termux-audio-info")}};


def _sum_group():
    return {"packages": _installed_sum_versions(), "sumcore_version": __version__};


def _simulated_group():
    return {
        "audio": {"internal_sample_rate": DEFAULT_SAMPLE_RATE, "pcm_format": "s16le mono", "release_ms": DEFAULT_RELEASE_MS, "maximum_gain_percent": 300, "beep": "ZX Spectrum duration,pitch semantics", "sound": "GW-BASIC frequency,ticks semantics", "play": "ZX PLAY and GW PLAY music strings", "zx_octaves": "O0..O10", "polyphony": 3},
        "keyboard": {"gui_keyup": "physical when frontend supplies release events", "tty_keyup": "physical only with extended terminal protocol; otherwise heuristic", "keyrepeat_control": "physical in GUI/extended protocols; backlog coalescing on legacy TTY"},
    };


def collect_report(groups=None, detailed=False):
    """Collect a structured passive report.

    ``detailed=False`` intentionally avoids expensive per-package ownership
    probes.  Asking for explicit groups through the CLI uses detailed mode.
    """;
    requested = tuple(groups or GROUPS);
    unknown = [name for name in requested if name not in GROUPS];
    if unknown: raise ValueError("unknown suminfo group(s): {}".format(", ".join(unknown)));
    report = {"schema": "sum.info/1", "created": datetime.now(timezone.utc).isoformat(), "suminfo_version": __version__, "observation": {"mutates_state": False, "requires_privilege": False, "uses_network": False}, "groups": {}};
    collectors = {
        "platform": _platform_group,
        "hardware": _hardware_group,
        "software": _software_group,
        "terminal": _terminal_group,
        "audio": _audio_group,
        "themes": _theme_inventory,
        "sum": _sum_group,
        "simulated": _simulated_group,
    };
    for name in requested:
        try:
            if name == "packages":
                value = {"python": _python_packages(detailed=detailed), "os": _os_packages(detailed=detailed)};
            else:
                value = collectors[name]();
            report["groups"][name] = {"status": "ok", "data": value};
        except Exception as exc:
            report["groups"][name] = {"status": "unavailable", "reason": str(exc), "data": {}};
    return report;


def collect_info():
    """Compatibility view used by the original ``suminfo`` API/tests.""";
    platform_group = _platform_group();
    hardware = _hardware_group();
    terminal = _terminal_group();
    audio = _audio_group();
    software = {
        "platform_profile": platform_group["profile"],
        "os": platform_group["system"],
        "os_release": platform_group["release"],
        "platform": platform_group["platform"],
        "python": platform.python_version(),
        "executable": sys.executable,
        "android": platform_group["profile"]["family"] == "android",
        "termux_version": os.environ.get("TERMUX_VERSION"),
        "termux_prefix": os.environ.get("PREFIX") if os.environ.get("TERMUX_VERSION") else None,
        "terminal": terminal,
        "pygame": _pygame_info(),
        "pulseaudio": audio["pulseaudio"],
        "persistent_audio": audio["persistent_audio"],
        "commands": audio["commands"],
        "sum_packages": _installed_sum_versions(),
    };
    simulated = _simulated_group();
    simulated["sumcore_version"] = __version__;
    simulated["audio"]["daemon"] = audio["daemon"];
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
        if not value: rows.append((prefix, "[]"));
        else:
            for index, item in enumerate(value): _flatten("{}[{}]".format(prefix, index), item, rows);
        return rows;
    rows.append((prefix, _format_value(value)));
    return rows;


def render_text(info):
    """Legacy full renderer for ``collect_info``.""";
    lines = [];
    for section in ("hardware", "software", "simulated"):
        lines.append(section.upper());
        rows = _flatten("", info.get(section, {}), []);
        width = max([len(key) for key, unused in rows] + [1]);
        for key, value in rows: lines.append("  {:{width}} : {}".format(key, value, width=width));
        lines.append("");
    return "\n".join(lines).rstrip();


def _memory_text(value):
    if not value: return "n/a";
    return "{:.1f} GiB".format(float(value) / (1024 ** 3));


def summary_rows(group, data):
    if group == "platform":
        profile = data.get("profile", {});
        return [("profile", profile.get("profile")), ("support", profile.get("support")), ("system", data.get("system")), ("architecture", profile.get("architecture"))];
    if group == "hardware": return [("cpu_count", data.get("cpu_count")), ("memory", _memory_text(data.get("memory_total_bytes"))), ("processor", data.get("processor"))];
    if group == "software": return [("python", data.get("python")), ("implementation", data.get("implementation")), ("pygame", (data.get("pygame") or {}).get("version"))];
    if group == "terminal": return [("TERM", data.get("TERM")), ("desktop", data.get("desktop")), ("tty", data.get("tty"))];
    if group == "audio":
        pulse = data.get("pulseaudio", {});
        persistent = data.get("persistent_audio", {});
        return [("pulse", pulse.get("available")), ("default_sink", pulse.get("default_sink")), ("backend", persistent.get("backend") or persistent.get("selected_backend")), ("sample_rate", DEFAULT_SAMPLE_RATE)];
    if group == "packages":
        py = data.get("python", {}); osdata = data.get("os", {});
        rows = [("python.count", py.get("count")), ("os.count", osdata.get("count")), ("os.manager", osdata.get("manager"))];
        for key, value in sorted((py.get("by_origin") or {}).items()): rows.append(("python.origin.{}".format(key), value));
        for key, value in sorted((py.get("by_stability") or {}).items()): rows.append(("python.stability.{}".format(key), value));
        return rows;
    if group == "themes":
        rows = [];
        active = data.get("active", {});
        if active.get("sum"): rows.append(("active.sum", active.get("sum")));
        if active.get("desktop"): rows.append(("active.desktop", active.get("desktop")));
        for name, item in (data.get("groups") or {}).items(): rows.append(("{}.count".format(name), item.get("count", 0)));
        rows.append(("unique.count", data.get("unique_count", 0)));
        return rows;
    if group == "sum":
        packages = data.get("packages", {});
        rows = [("installed", len(packages))];
        for name in ("sumcore", "sumui", "sumtui", "sumgui", "sumide", "sumbasic", "sumx"): 
            if name in packages: rows.append((name, packages[name]));
        return rows;
    if group == "simulated": return [("audio.sample_rate", data.get("audio", {}).get("internal_sample_rate")), ("audio.polyphony", data.get("audio", {}).get("polyphony")), ("keyboard.keyup", data.get("keyboard", {}).get("gui_keyup"))];
    return _flatten("", data, []);


def render_report(report, detailed=False, search=None):
    lines = [];
    query = str(search or "").casefold();
    for group, payload in report.get("groups", {}).items():
        if payload.get("status") != "ok":
            rows = [("status", payload.get("status")), ("reason", payload.get("reason"))];
        else:
            rows = _flatten("", payload.get("data", {}), []) if detailed else summary_rows(group, payload.get("data", {}));
        if query:
            rows = [(key, value) for key, value in rows if query in (str(key) + " " + str(value)).casefold()];
            if not rows: continue;
        lines.append(group.upper());
        width = max([len(str(key)) for key, unused in rows] + [1]);
        for key, value in rows: lines.append("  {:{width}} : {}".format(str(key), _format_value(value), width=width));
        lines.append("");
    return "\n".join(lines).rstrip();


def _snapshot_dir():
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"));
    return root / "suminfo" / "snapshots";


def _snapshot_path(name):
    raw = str(name or "").strip();
    if not raw: raise ValueError("snapshot name cannot be empty");
    candidate = Path(raw).expanduser();
    if candidate.suffix.lower() == ".json" or candidate.parent != Path("."):
        return candidate;
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-") or "snapshot";
    return _snapshot_dir() / (safe + ".json");


def save_snapshot(name, report=None):
    report = report or collect_report(detailed=True);
    path = _snapshot_path(name);
    path.parent.mkdir(parents=True, exist_ok=True);
    payload = dict(report);
    payload["snapshot"] = {"name": Path(path).stem, "saved": datetime.now(timezone.utc).isoformat()};
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8");
    return path;


def load_snapshot(name):
    path = _snapshot_path(name);
    data = json.loads(path.read_text(encoding="utf-8"));
    if data.get("schema") != "sum.info/1": raise ValueError("unsupported snapshot schema");
    return data;


def _list_key(item):
    if isinstance(item, dict):
        for key in ("name", "id", "path", "package"):
            if key in item: return str(item[key]);
    return None;


def _semantic_diff(old, new, path=""):
    changes = [];
    # Volatile values that would otherwise dominate every comparison.
    if path in ("created", "snapshot.saved") or path.endswith("memory_available_bytes") or path.endswith("uptime"): return changes;
    if isinstance(old, dict) and isinstance(new, dict):
        keys = sorted(set(old) | set(new));
        for key in keys:
            child = "{}.{}".format(path, key) if path else key;
            if key not in old: changes.append({"kind": "added", "path": child, "old": None, "new": new[key]});
            elif key not in new: changes.append({"kind": "removed", "path": child, "old": old[key], "new": None});
            else: changes.extend(_semantic_diff(old[key], new[key], child));
        return changes;
    if isinstance(old, list) and isinstance(new, list):
        old_keys = [_list_key(item) for item in old]; new_keys = [_list_key(item) for item in new];
        if old and new and all(old_keys) and all(new_keys):
            omap = {key: item for key, item in zip(old_keys, old)}; nmap = {key: item for key, item in zip(new_keys, new)};
            return _semantic_diff(omap, nmap, path);
        if old != new: changes.append({"kind": "changed", "path": path, "old": old, "new": new});
        return changes;
    if old != new:
        kind = "changed";
        if old in (None, False, "unavailable") and new not in (None, False, "unavailable"): kind = "became_available";
        elif new in (None, False, "unavailable") and old not in (None, False, "unavailable"): kind = "became_unavailable";
        changes.append({"kind": kind, "path": path, "old": old, "new": new});
    return changes;


def compare_reports(old, new, groups=None):
    wanted = tuple(groups or GROUPS);
    left = {"groups": {key: old.get("groups", {}).get(key) for key in wanted if key in old.get("groups", {})}};
    right = {"groups": {key: new.get("groups", {}).get(key) for key in wanted if key in new.get("groups", {})}};
    return {"schema": "sum.info-diff/1", "old_created": old.get("created"), "new_created": new.get("created"), "changes": _semantic_diff(left, right)};


def render_diff(diff, detailed=False):
    changes = list(diff.get("changes", []));
    if not changes: return "No comparable changes.";
    if not detailed:
        # Collapse noisy item-level paths only by displaying all actual changes;
        # callers can still use --group to narrow the signal.  This keeps the
        # first implementation lossless while leaving room for importance tags.
        pass;
    lines = ["CHANGES"];
    for item in changes:
        lines.append("  {:18} {}".format(item.get("kind", "changed"), item.get("path", "")));
        if detailed:
            lines.append("    old: {}".format(_format_value(item.get("old"))));
            lines.append("    new: {}".format(_format_value(item.get("new"))));
    return "\n".join(lines);


def _interactive_view(kind, report, groups, detailed):
    module_name = "sumtui.tools.info_view" if kind == "tui" else "sumgui.tools.info_view";
    try:
        module = __import__(module_name, fromlist=["run"]);
    except Exception as exc:
        raise RuntimeError("{} frontend unavailable: {}".format(kind.upper(), exc));
    return int(module.run(report, groups=groups, detailed=detailed));


def main(argv=None):
    parser = argparse.ArgumentParser(prog="suminfo", description="Passively inspect the current system and SUM environment.");
    parser.add_argument("-a", "--all", action="store_true", help="show complete information for all selected groups");
    parser.add_argument("-g", "--group", action="append", choices=GROUPS, help="show one group in detail; may be repeated");
    parser.add_argument("--list-groups", action="store_true", help="list available information groups");
    parser.add_argument("--search", default=None, help="filter rendered keys/values");
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON");
    front = parser.add_mutually_exclusive_group();
    front.add_argument("--tui", action="store_true", help="show information in a tabbed sumTUI viewer");
    front.add_argument("--gui", action="store_true", help="show information in a tabbed sumGUI viewer");
    parser.add_argument("--save", metavar="NAME_OR_FILE", help="save a complete structured snapshot");
    parser.add_argument("--compare", nargs="+", metavar="SNAPSHOT", help="compare one snapshot with now, or two saved snapshots");
    parser.add_argument("--debug", action="store_true", help="show collector status/reasons when available");
    args = parser.parse_args(argv);
    if args.list_groups:
        print("\n".join(GROUPS));
        return 0;
    groups = tuple(args.group or GROUPS);
    detailed = bool(args.all or args.group);
    try:
        if args.save:
            path = save_snapshot(args.save, collect_report(groups=GROUPS, detailed=True));
            print(path);
            return 0;
        if args.compare:
            if len(args.compare) > 2: raise ValueError("--compare accepts one or two snapshots");
            old = load_snapshot(args.compare[0]);
            new = load_snapshot(args.compare[1]) if len(args.compare) == 2 else collect_report(groups=GROUPS, detailed=True);
            diff = compare_reports(old, new, groups=groups);
            if args.json: print(json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True));
            else: print(render_diff(diff, detailed=bool(args.all)));
            return 0;
        report = collect_report(groups=groups, detailed=detailed);
        if args.tui: return _interactive_view("tui", report, groups, detailed);
        if args.gui: return _interactive_view("gui", report, groups, detailed);
        if args.json: print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True));
        else: print(render_report(report, detailed=detailed, search=args.search));
        return 0;
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print("suminfo: {}".format(exc), file=sys.stderr);
        return 2;


if __name__ == "__main__":
    raise SystemExit(main());
