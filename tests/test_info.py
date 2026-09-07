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
    monkeypatch.setattr(info, "_command_text", lambda command, timeout=2.0: "Server Name: test" if command[0] == "pactl" else None);
    monkeypatch.setattr(info.PersistentPCMOutput, "pulse_sinks", staticmethod(lambda: [{"id": "1", "name": "OpenSL_ES_sink", "raw": "1 OpenSL_ES_sink"}]));
    monkeypatch.setattr(info.PersistentPCMOutput, "preferred_pulse_sink", classmethod(lambda cls: "OpenSL_ES_sink"));
    monkeypatch.setattr(info, "_daemon_info", lambda: {"ok": True, "pid": 123, "mixer": {"output": {"backend": "pulseaudio/pacat"}}});
    data = info.collect_info();
    assert set(data) == {"hardware", "software", "simulated"};
    assert data["hardware"]["android_audio"]["PROPERTY_OUTPUT_SAMPLE_RATE"] == "48000";
    assert data["software"]["pulseaudio"]["preferred_sink"] == "OpenSL_ES_sink";
    assert data["simulated"]["audio"]["internal_sample_rate"] == 48000;
    assert data["simulated"]["audio"]["daemon"]["pid"] == 123;
    text = info.render_text(data);
    assert "HARDWARE" in text and "SOFTWARE" in text and "SIMULATED" in text;
    json.dumps(data);
