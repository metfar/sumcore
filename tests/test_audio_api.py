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

from sumcore.audio import AudioEngine;
from sumcore.audio_api import beep, play, set_audio_engine, sound;


def test_common_facade_preserves_basic_units_and_dialects():
    tones = [];
    engine = AudioEngine(tone_func=lambda frequency, duration, blocking, volume=1.0: tones.append((frequency, duration, blocking, volume)));
    set_audio_engine(engine);
    beep(.25, 12, volume=.4);
    sound(440, 18.2, volume=.5);
    play("T240O4c", volume=.6);
    assert abs(tones[0][0] - 523.2511306011972) < 1e-9 and tones[0][1] == .25;
    assert abs(tones[1][0] - 440.0) < 1e-9 and abs(tones[1][1] - 1.0) < 1e-12;
    assert tones[2][2] is True;


def test_hold_prefers_normal_sox_audio_path_before_pygame(monkeypatch):
    import sumcore.audio as audio;
    calls = [];
    class Process:
        def __init__(self, command): self.command = command; self.terminated = False;
        def poll(self): return None if not self.terminated else 0;
        def terminate(self): self.terminated = True;
    process = None;
    def popen(command, **_kwargs):
        nonlocal process;
        calls.append(command);
        process = Process(command);
        return process;
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/play" if name == "play" else None);
    monkeypatch.setattr(audio.subprocess, "Popen", popen);
    player = audio.SystemTonePlayer();
    assert player.hold(440, .25) is True;
    assert calls and calls[0][0] == "/usr/bin/play";
    assert "sine" in calls[0];
    player.stop();
    assert process.terminated is True;
