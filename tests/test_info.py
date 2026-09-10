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
