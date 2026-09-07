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
import io;
import struct;
import wave;

import pytest;

from sumcore.audio import SystemTonePlayer;
from sumcore.audio_api import midi_frequency, tone_pcm_bytes, tone_wav_bytes;


def test_midi_frequency_a4_is_440_hz():
    assert midi_frequency(69) == pytest.approx(440.0);


def test_public_pcm_generator_is_the_system_tone_generator():
    player = SystemTonePlayer(sample_rate=48000);
    public = tone_pcm_bytes(440.0, .02, .4, 48000);
    assert public == player._pcm_bytes(440.0, .02, .4);
    values = struct.unpack("<{}h".format(len(public) // 2), public);
    assert max(abs(value) for value in values) <= 4400;


def test_five_default_piano_voices_have_theoretical_headroom():
    source_peak = 11000;
    channel_volume = .4;
    assert source_peak * channel_volume * 5 < 32767;


def test_wav_generator_is_mono_signed_16_at_requested_rate():
    payload = tone_wav_bytes(midi_frequency(60), .01, .4, 48000);
    with wave.open(io.BytesIO(payload), "rb") as wav:
        assert wav.getnchannels() == 1;
        assert wav.getsampwidth() == 2;
        assert wav.getframerate() == 48000;
        assert wav.getnframes() == 480;
