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
import os;
import threading;
import time;

import pytest;

from sumcore.audio_daemon import AudioDaemonClient, AudioDaemonServer, AudioMixer, PROTOCOL_VERSION;


class MemoryOutput:
    def __init__(self):
        self.running = False;
        self.payloads = [];
    def open(self): self.running = True; return True;
    def write(self, payload): self.payloads.append(bytes(payload)); return True;
    def close(self): self.running = False; return None;
    def info(self): return {"backend": "memory", "sink": None, "running": self.running};


def test_mixer_tone_and_hold_have_click_free_lifecycle():
    output = MemoryOutput();
    mixer = AudioMixer(output=output, sample_rate=8000, release_ms=8, chunk_ms=5);
    assert mixer.start();
    done = mixer.tone("finite", 440, .03, 1.0);
    assert done.wait(.5);
    held = mixer.hold("held", 330, 1.0);
    time.sleep(.03);
    assert not held.is_set();
    assert mixer.stop_voice("held") == 1;
    assert held.wait(.5);
    mixer.close();
    assert output.payloads;
    assert any(any(byte != 0 for byte in payload) for payload in output.payloads);


def test_daemon_protocol_roundtrip(tmp_path):
    if not hasattr(__import__("socket"), "AF_UNIX"): pytest.skip("AF_UNIX unavailable");
    output = MemoryOutput();
    mixer = AudioMixer(output=output, sample_rate=8000, release_ms=8, chunk_ms=5);
    endpoint = {"kind": "unix", "path": str(tmp_path / "sum.sock")};
    server = AudioDaemonServer(endpoint=endpoint, mixer=mixer);
    thread = threading.Thread(target=server.serve_forever, daemon=True);
    thread.start();
    client = AudioDaemonClient(endpoint=endpoint, timeout=.5);
    deadline = time.monotonic() + 1.0;
    while time.monotonic() < deadline and not client.ping(): time.sleep(.01);
    assert client.ping();
    info = client.info();
    assert info["protocol"] == PROTOCOL_VERSION;
    assert info["mixer"]["output"]["backend"] == "memory";
    assert client.tone("a", 440, .02, 1.0, blocking=True)["ok"];
    assert client.hold("b", 523.25, 1.0)["ok"];
    assert client.stop("b")["ok"];
    assert client.shutdown()["ok"];
    thread.join(timeout=1.0);
    assert not thread.is_alive();
    assert not os.path.exists(endpoint["path"]);
