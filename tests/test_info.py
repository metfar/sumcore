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
import json;

from sumcore import info;


def test_suminfo_has_real_software_and_simulated_sections(monkeypatch):
    monkeypatch.setattr(info, "_command_json", lambda command, timeout=2.0: {"PROPERTY_OUTPUT_SAMPLE_RATE": "48000"} if command[0] == "termux-audio-info" else None);
    monkeypatch.setattr(info.PersistentPCMOutput, "pulse_server_info", staticmethod(lambda: "Server Name: test"));
    monkeypatch.setattr(info.PersistentPCMOutput, "pulse_sinks", staticmethod(lambda: [{"id": "1", "name": "OpenSL_ES_sink", "raw": "1 OpenSL_ES_sink"}]));
    monkeypatch.setattr(info.PersistentPCMOutput, "pulse_default_sink", classmethod(lambda cls: "OpenSL_ES_sink"));
    monkeypatch.setattr(info.PersistentPCMOutput, "preferred_pulse_sink", classmethod(lambda cls: "OpenSL_ES_sink"));
    monkeypatch.setattr(info, "_daemon_info", lambda: {"ok": True, "pid": 123, "mixer": {"output": {"backend": "pulseaudio/pacat"}}});
    data = info.collect_info();
    assert set(data) == {"hardware", "software", "simulated"};
    assert "platform_profile" in data["software"];
    assert data["hardware"]["android_audio"]["PROPERTY_OUTPUT_SAMPLE_RATE"] == "48000";
    assert data["software"]["pulseaudio"]["preferred_sink"] == "OpenSL_ES_sink";
    assert data["simulated"]["audio"]["internal_sample_rate"] == 48000;
    assert data["simulated"]["audio"]["daemon"]["pid"] == 123;
    text = info.render_text(data);
    assert "HARDWARE" in text and "SOFTWARE" in text and "SIMULATED" in text;
    json.dumps(data);


def test_platform_profiles_termux_google_play_and_fdroid(monkeypatch):
    monkeypatch.setattr(info.platform, "machine", lambda: "aarch64");
    monkeypatch.setenv("TERMUX_VERSION", "googleplay.2026.06.21");
    google = info._platform_profile(True);
    assert google["profile"] == "android-termux-google-play-aarch64";
    monkeypatch.setenv("TERMUX_VERSION", "0.118.3");
    fdroid = info._platform_profile(True);
    assert fdroid["profile"] == "android-termux-fdroid-aarch64";


def test_platform_profile_linux_distribution(monkeypatch):
    monkeypatch.delenv("TERMUX_VERSION", raising=False);
    monkeypatch.setattr(info.platform, "system", lambda: "Linux");
    monkeypatch.setattr(info.platform, "machine", lambda: "x86_64");
    monkeypatch.setattr(info, "_os_release", lambda: {"ID": "ubuntu"});
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "XFCE");
    profile = info._platform_profile(False);
    assert profile["profile"] == "linux-ubuntu-desktop-x86_64";


def test_suminfo_passive_policy_and_windows_preview(monkeypatch):
    assert info.PASSIVE_POLICY.mutates_state is False;
    assert info.PASSIVE_POLICY.requires_privilege is False;
    assert info.PASSIVE_POLICY.uses_network is False;
    monkeypatch.setattr(info.platform, "system", lambda: "Windows");
    monkeypatch.setattr(info.platform, "machine", lambda: "AMD64");
    profile = info._platform_profile(False);
    assert profile["family"] == "windows";
    assert profile["support"] == "unsupported";
    assert profile["privilege_assumption"] == "standard-user";
    assert profile["profile"] == "windows-preview-AMD64";


def test_suminfo_python_provenance_can_be_reclassified_by_dpkg(monkeypatch):
    class FakeDist:
        metadata = {"Name": "demo"};
        version = "2.0rc1";
        _path = "/usr/lib/python3/dist-packages/demo-2.0rc1.dist-info";
        def read_text(self, name):
            if name == "INSTALLER": return "pip\n";
            if name == "direct_url.json": return None;
            return None;
    monkeypatch.setattr(info.importlib.metadata, "distributions", lambda: [FakeDist()]);
    monkeypatch.setattr(info, "_dpkg_owners", lambda paths: {FakeDist._path: "python3-demo"});
    packages = info._python_packages(detailed=True);
    assert packages["count"] == 1;
    assert packages["items"][0]["origin"] == "os-package";
    assert packages["items"][0]["owner"] == "python3-demo";
    assert packages["items"][0]["stability"] == "prerelease";


def test_suminfo_local_editable_python_provenance():
    class FakeDist:
        metadata = {"Name": "localdemo"};
        version = "0.1.dev2";
        _path = "/home/user/project/localdemo.egg-info";
        def read_text(self, name):
            if name == "INSTALLER": return "pip\n";
            if name == "direct_url.json": return '{"url":"file:///home/user/project","dir_info":{"editable":true}}';
            return None;
    record = info._python_distribution_record(FakeDist());
    assert record["origin"] == "pip-editable";
    assert record["stability"] == "development";


def test_suminfo_report_summary_groups_and_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path));
    monkeypatch.setattr(info, "_platform_group", lambda: {"profile": {"profile": "linux-test", "support": "supported", "architecture": "x86_64"}, "system": "Linux"});
    monkeypatch.setattr(info, "_hardware_group", lambda: {"cpu_count": 4, "memory_total_bytes": 8 * 1024 ** 3, "processor": "test"});
    report = info.collect_report(groups=("platform", "hardware"), detailed=False);
    text = info.render_report(report, detailed=False);
    assert "PLATFORM" in text and "linux-test" in text;
    assert "HARDWARE" in text and "8.0 GiB" in text;
    path = info.save_snapshot("baseline", report);
    assert path.is_file();
    loaded = info.load_snapshot("baseline");
    changed = json.loads(json.dumps(loaded));
    changed["groups"]["hardware"]["data"]["cpu_count"] = 8;
    diff = info.compare_reports(loaded, changed, groups=("hardware",));
    assert any(item["path"].endswith("cpu_count") for item in diff["changes"]);


def test_suminfo_theme_inventory_has_explicit_subsystems(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path));
    monkeypatch.setenv("PREFIX", str(tmp_path / "prefix"));
    result = info._theme_inventory();
    assert set(("sum", "gtk", "gnome", "xfce", "kde", "terminal")).issubset(result["groups"]);
    for value in result["groups"].values():
        assert "count" in value and "items" in value and "paths" in value;


def test_suminfo_interactive_frontend_dispatch(monkeypatch):
    import sys;
    import types;
    report = {"groups": {"platform": {"status": "ok", "data": {}}}};
    called = {};
    module = types.ModuleType("sumtui.tools.info_view");
    module.run = lambda value, groups=None, detailed=False: called.update({"value": value, "groups": groups, "detailed": detailed}) or 7;
    monkeypatch.setitem(sys.modules, "sumtui.tools.info_view", module);
    assert info._interactive_view("tui", report, ("platform",), False) == 7;
    assert called["groups"] == ("platform",);
    assert called["detailed"] is False;


def test_suminfo_distro_installer_metadata_is_os_managed(monkeypatch):
    class FakeDist:
        metadata = {"Name": "distrodemo"};
        version = "1.2.3";
        _path = "/usr/lib/python3/dist-packages/distrodemo-1.2.3.dist-info";
        def read_text(self, name):
            if name == "INSTALLER": return "debian\n";
            return None;
    record = info._python_distribution_record(FakeDist());
    assert record["origin"] == "os-package";
    assert record["source"] == "debian";
