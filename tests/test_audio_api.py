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


def test_hold_uses_streamed_sox_pcm_when_mixer_is_not_already_active(monkeypatch):
    import sumcore.audio as audio;
    calls = [];
    class Pipe:
        def __init__(self, owner): self.owner = owner; self.closed = False; self.data = bytearray();
        def write(self, payload): self.data.extend(payload); return len(payload);
        def flush(self): return None;
        def close(self): self.closed = True; self.owner.terminated = True;
    class Process:
        def __init__(self, command):
            self.command = command;
            self.terminated = False;
            self.stdin = Pipe(self);
        def poll(self): return None if not self.terminated else 0;
        def terminate(self): self.terminated = True;
        def wait(self, timeout=None): self.terminated = True; return 0;
    process = None;
    def popen(command, **_kwargs):
        nonlocal process;
        calls.append(command);
        process = Process(command);
        return process;
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/play" if name == "play" else None);
    monkeypatch.setattr(audio.subprocess, "Popen", popen);
    monkeypatch.setattr(audio.SystemTonePlayer, "_start_pygame_hold", lambda self, frequency, volume, initialize=False: False);
    player = audio.SystemTonePlayer();
    assert player.hold(440, .25) is True;
    assert calls and calls[0][0] == "/usr/bin/play";
    assert "raw" in calls[0];
    player.stop();
    assert process.terminated is True;
    assert process.stdin.data;



def test_hold_prefers_an_already_initialized_pygame_mixer_before_external_audio(monkeypatch):
    import sumcore.audio as audio;
    calls = [];
    def pygame_hold(self, frequency, volume, initialize=False):
        calls.append((frequency, volume, initialize));
        return initialize is False;
    monkeypatch.setattr(audio.SystemTonePlayer, "_start_pygame_hold", pygame_hold);
    monkeypatch.setattr(audio.shutil, "which", lambda _name: (_ for _ in ()).throw(AssertionError("external backend should not be probed")));
    player = audio.SystemTonePlayer();
    assert player.hold(440, .5) is True;
    assert calls == [(440.0, .5, False)];


def test_termux_hold_uses_native_media_player_and_cleans_temp_file(monkeypatch, tmp_path):
    import os;
    import sumcore.audio as audio;
    calls = [];
    class Result:
        returncode = 0;
        stdout = "Now Playing: sumtone-test.wav\n";
        stderr = "";
    def run(command, **_kwargs):
        calls.append(list(command));
        return Result();
    monkeypatch.setenv("TERMUX_VERSION", "0.119-test");
    monkeypatch.setenv("TMPDIR", str(tmp_path));
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/data/data/com.termux/files/usr/bin/termux-media-player" if name == "termux-media-player" else None);
    monkeypatch.setattr(audio.subprocess, "run", run);
    monkeypatch.setattr(audio.SystemTonePlayer, "_start_pygame_hold", lambda self, frequency, volume, initialize=False: False);
    player = audio.SystemTonePlayer();
    assert player.hold(220, .5, duration_hint=.7) is True;
    media_file = player._termux_media_file;
    assert media_file is not None and os.path.exists(media_file);
    assert calls[0][1] == "play";
    assert calls[0][2] == media_file;
    player.stop();
    assert calls[-1][1] == "stop";
    assert not os.path.exists(media_file);


def test_termux_backend_is_not_selected_outside_termux(monkeypatch):
    import sumcore.audio as audio;
    monkeypatch.delenv("TERMUX_VERSION", raising=False);
    monkeypatch.setenv("PREFIX", "/usr");
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/termux-media-player" if name == "termux-media-player" else None);
    assert audio.SystemTonePlayer._termux_media_command() is None;


def test_play_bus_allows_150_percent_software_gain_without_unity_clamp():
    from sumcore.audio import AudioEngine, SystemTonePlayer;
    engine = AudioEngine();
    assert engine.set_volume("PLAY", 1.5) == 1.5;
    assert engine.get_volume("PLAY") == 1.5;
    player = SystemTonePlayer();
    frames = player._pcm_bytes(440, .01, 1.5);
    assert frames;
    samples = __import__("struct").unpack("<{}h".format(len(frames) // 2), frames);
    assert max(abs(value) for value in samples) > 11000;
    assert max(abs(value) for value in samples) <= 32767;


def test_finite_posix_tone_uses_same_raw_pcm_sox_path_as_hold(monkeypatch):
    import sumcore.audio as audio;
    calls = [];
    class Process:
        def __init__(self, command):
            self.command = list(command);
            self.returncode = None;
            self.payload = None;
        def communicate(self, payload):
            self.payload = bytes(payload);
            self.returncode = 0;
            return (b"", b"");
        def poll(self): return self.returncode;
        def terminate(self): self.returncode = -15;
    process = None;
    def popen(command, **_kwargs):
        nonlocal process;
        process = Process(command);
        calls.append(process);
        return process;
    monkeypatch.delenv("TERMUX_VERSION", raising=False);
    monkeypatch.setenv("PREFIX", "/usr");
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/play" if name == "play" else None);
    monkeypatch.setattr(audio.subprocess, "Popen", popen);
    player = audio.SystemTonePlayer();
    assert player._play_blocking(440, .05, 1.5) is True;
    assert calls;
    assert calls[0].command[:4] == ["/usr/bin/play", "-q", "-t", "raw"];
    assert "synth" not in calls[0].command;
    assert calls[0].payload == player._pcm_bytes(440, .05, 1.5);


def test_termux_media_player_stdout_error_does_not_mask_backend_failure(monkeypatch):
    import sumcore.audio as audio;
    class Result:
        returncode = 0;
        stdout = "setDataSource failed: status = 0x80000000\n";
        stderr = "";
    monkeypatch.setenv("TERMUX_VERSION", "0.119-test");
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/data/data/com.termux/files/usr/bin/termux-media-player" if name == "termux-media-player" else None);
    monkeypatch.setattr(audio.subprocess, "run", lambda *args, **kwargs: Result());
    assert audio.SystemTonePlayer._termux_media_call("play", "/tmp/tone.wav") is False;


def test_termux_finite_wav_has_silent_preroll_and_postroll():
    import io;
    import struct;
    import wave;
    from sumcore.audio import SystemTonePlayer;
    player = SystemTonePlayer(sample_rate=8000, termux_preroll=.4, termux_postroll=.1);
    payload = player._wav_bytes(100, .2, 1.0, preroll=.4, postroll=.1);
    with wave.open(io.BytesIO(payload), "rb") as wav:
        frames = wav.readframes(wav.getnframes());
        assert wav.getnframes() == 5600;
    samples = struct.unpack("<{}h".format(len(frames) // 2), frames);
    assert all(value == 0 for value in samples[:3200]);
    assert any(value != 0 for value in samples[3200:4800]);
    assert all(value == 0 for value in samples[4800:]);


def test_termux_finite_player_keeps_media_alive_for_preroll_tone_and_postroll(monkeypatch, tmp_path):
    import sumcore.audio as audio;
    calls = [];
    monkeypatch.setenv("TERMUX_VERSION", "0.119-test");
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/data/data/com.termux/files/usr/bin/termux-media-player" if name == "termux-media-player" else None);
    player = audio.SystemTonePlayer(sample_rate=1000, termux_preroll=.002, termux_postroll=.001);
    media = tmp_path / "tone.wav";
    media.write_bytes(b"x");
    monkeypatch.setattr(player, "_termux_wav_file", lambda frequency, duration, volume, preroll=0.0, postroll=0.0: (calls.append((frequency, duration, volume, preroll, postroll)) or str(media)));
    monkeypatch.setattr(player, "_termux_media_call", lambda action, media_file=None, timeout=2.0: True);
    started = __import__("time").monotonic();
    assert player._play_termux_blocking(440, .001, 1.0) is True;
    elapsed = __import__("time").monotonic() - started;
    assert calls == [(440, .001, 1.0, .002, .001)];
    assert elapsed >= .003;
    assert not media.exists();


def test_termux_preroll_can_be_tuned_from_environment(monkeypatch):
    from sumcore.audio import SystemTonePlayer;
    monkeypatch.setenv("SUM_TERMUX_AUDIO_PREROLL_MS", "900");
    monkeypatch.setenv("SUM_TERMUX_AUDIO_POSTROLL_MS", "125");
    player = SystemTonePlayer();
    assert abs(player.termux_preroll - .9) < 1e-12;
    assert abs(player.termux_postroll - .125) < 1e-12;
