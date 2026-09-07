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

"""Small language-neutral facade over the shared Sum audio engine.""";

from .audio import AudioEngine, gw_ticks_to_seconds, midi_frequency, spectrum_frequency_pitch, spectrum_pitch_frequency, tone_pcm_bytes, tone_wav_bytes;

_engine = AudioEngine();


def audio_engine(): return _engine;


def set_audio_engine(engine):
    global _engine;
    if not isinstance(engine, AudioEngine): raise TypeError("engine must be an AudioEngine");
    _engine = engine;
    return engine;


def beep(duration, pitch, volume=None):
    if volume is not None: _engine.set_volume("BEEP", float(volume));
    return _engine.beep(spectrum_pitch_frequency(float(pitch)), float(duration));


def sound(frequency, duration, volume=None):
    if volume is not None: _engine.set_volume("SOUND", float(volume));
    hz = spectrum_pitch_frequency(spectrum_frequency_pitch(float(frequency)));
    return _engine.sound(hz, gw_ticks_to_seconds(float(duration)));


def play(*music, dialect="zx", background=False, hold=False, timeout=3.0, volume=None):
    if volume is not None: _engine.set_volume("PLAY", float(volume));
    strings = [str(item) for item in music];
    if hold:
        if len(strings) != 1 or str(dialect).lower() != "zx": raise ValueError("held PLAY requires exactly one ZX string");
        return _engine.zxplay_hold(strings[0], timeout=float(timeout));
    if str(dialect).lower() == "gw":
        if len(strings) != 1: raise ValueError("GW PLAY requires exactly one string");
        return _engine.gwplay(strings[0], mode="BACKGROUND" if background else "FOREGROUND");
    return _engine.zxplay(strings, background=bool(background));


def stop_audio(): return _engine.stop_all();
def wait_audio(): return _engine.wait_for_background();


__all__ = ["audio_engine", "beep", "midi_frequency", "play", "set_audio_engine", "sound", "stop_audio", "tone_pcm_bytes", "tone_wav_bytes", "wait_audio"];
