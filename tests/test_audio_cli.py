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
#
#import warnings;
#warnings.filterwarnings("ignore", category=UserWarning);

from sumcore.audio_cli import main_beep, main_play, main_sound;


class FakeAudio:
    instances = [];

    def __init__(self):
        self.calls = [];
        self.__class__.instances.append(self);

    def set_volume(self, bus, value): self.calls.append(("volume", bus, value));
    def beep(self, frequency, duration): self.calls.append(("beep", frequency, duration));
    def sound(self, frequency, duration): self.calls.append(("sound", frequency, duration));
    def zxplay(self, strings, background=False): self.calls.append(("zx", strings, background));
    def zxplay_hold(self, source, timeout=3.0): self.calls.append(("hold", source, timeout));
    def gwplay(self, source, mode=None): self.calls.append(("gw", source, mode));
    def wait_for_background(self): self.calls.append(("wait",));
    def stop_all(self): self.calls.append(("stop",));


def _last(): return FakeAudio.instances[-1];


def test_sumbeep_keeps_basic_duration_pitch_order():
    assert main_beep(["0.25", "12", "--volume", "40"], FakeAudio) == 0;
    assert _last().calls[0] == ("volume", "BEEP", .4);
    assert abs(_last().calls[1][1] - 523.2511306011972) < 1e-9;
    assert _last().calls[1][2] == .25;


def test_sumsound_keeps_hertz_and_tick_units_and_waits():
    assert main_sound(["440", "18.2"], FakeAudio) == 0;
    assert _last().calls[1][0] == "sound";
    assert abs(_last().calls[1][1] - 440.0) < 1e-9;
    assert abs(_last().calls[1][2] - 1.0) < 1e-12;
    assert _last().calls[-1] == ("wait",);


def test_sumplay_supports_zx_voices_gw_and_hold_timeout():
    assert main_play(["O4c", "O3g"], FakeAudio) == 0;
    assert ("zx", ["O4c", "O3g"], False) in _last().calls;
    assert main_play(["--gw", "T180 O4 L8 CDE"], FakeAudio) == 0;
    assert ("gw", "T180 O4 L8 CDE", "FOREGROUND") in _last().calls;
    assert main_play(["--hold", "--timeout", ".001", "O4c"], FakeAudio) == 0;
    assert ("hold", "O4c", .001) in _last().calls;
    assert _last().calls[-1] == ("stop",);
