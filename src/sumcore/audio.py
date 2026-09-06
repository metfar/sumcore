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
import contextlib;
import math;
import os;
import queue;
import re;
import shutil;
import struct;
import subprocess;
import sys;
import threading;
import time;
import wave;
import warnings;


MIDDLE_C_HZ = 261.6255653005986;
GW_BASIC_TICKS_PER_SECOND = 18.2;
GW_BASIC_SOUND_MIN_HZ = 37.0;
GW_BASIC_SOUND_MAX_HZ = 32767.0;
_NOTE_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11};
_ZX_DURATION_QUARTERS = {1: .25, 2: .375, 3: .5, 4: .75, 5: 1.0, 6: 1.5, 7: 2.0, 8: 3.0, 9: 4.0, 10: 1.0 / 6.0, 11: 1.0 / 3.0, 12: 2.0 / 3.0};


def spectrum_pitch_frequency(pitch):
    return MIDDLE_C_HZ * (2.0 ** (float(pitch) / 12.0));


def spectrum_frequency_pitch(frequency):
    frequency = float(frequency);
    if frequency <= 0.0:
        raise ValueError("frequency must be positive");
    return 12.0 * math.log2(frequency / MIDDLE_C_HZ);


def gw_ticks_to_seconds(ticks):
    return float(ticks) / GW_BASIC_TICKS_PER_SECOND;


def _call_tone_func(func, frequency, duration, blocking, volume):
    """Call legacy or volume-aware tone callbacks without breaking old backends."""
    try:
        return func(frequency, duration, blocking, volume);
    except TypeError:
        return func(frequency, duration, blocking);


def _midi_frequency(midi_note):
    return 440.0 * (2.0 ** ((float(midi_note) - 69.0) / 12.0));


class SystemTonePlayer:
    """Small queued tone renderer.

    Instances are intentionally cheap enough to be used as independent audio
    buses.  Sum frontends therefore give BEEP, SOUND, and each music voice their
    own player instead of forcing all historical sound models through one
    blocking queue.
    """
    def __init__(self, sample_rate=48000, release_ms=8):
        self.sample_rate = max(8000, int(sample_rate));
        self.release_ms = max(0, int(release_ms));
        self._tone_queue = queue.Queue();
        self._worker = None;
        self._worker_lock = threading.Lock();
        self._generation = 0;
        self._generation_lock = threading.Lock();
        self._active_cancel_event = None;
        self._active_process = None;
        self._active_lock = threading.Lock();
        self._hold_channel = None;
        self._hold_sound = None;
        self._hold_process = None;
        self._hold_stop_event = None;
        self._hold_thread = None;
        self._hold_backend = None;

    def _ensure_worker(self):
        with self._worker_lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._worker_loop, name="sumBASIC-tone", daemon=True);
                self._worker.start();
        return self._worker;

    def _current_generation(self):
        with self._generation_lock: return self._generation;

    def stop(self):
        # Cancel the currently sounding tone and invalidate queued requests.
        with self._generation_lock: self._generation += 1;
        with self._active_lock:
            cancel_event = self._active_cancel_event;
            process = self._active_process;
        if cancel_event is not None: cancel_event.set();
        if process is not None:
            try:
                if process.poll() is None: process.terminate();
            except Exception:
                pass;
        channel = self._hold_channel;
        self._hold_channel = None;
        self._hold_sound = None;
        if channel is not None:
            try:
                if self.release_ms > 0: channel.fadeout(self.release_ms);
                else: channel.stop();
            except Exception:
                pass;
        hold_stop_event = self._hold_stop_event;
        hold_process = self._hold_process;
        hold_thread = self._hold_thread;
        hold_backend = self._hold_backend;
        self._hold_stop_event = None;
        self._hold_process = None;
        self._hold_thread = None;
        self._hold_backend = None;
        if hold_stop_event is not None: hold_stop_event.set();
        if hold_thread is not None and str(hold_backend).startswith("pcm:"):
            try: hold_thread.join(timeout=max(.05, (self.release_ms / 1000.0) + .05));
            except Exception: pass;
        if hold_process is not None:
            try:
                if str(hold_backend).startswith("pcm:") and hold_process.poll() is None:
                    hold_process.wait(timeout=max(.04, (self.release_ms / 1000.0) + .04));
                if hold_process.poll() is None: hold_process.terminate();
            except Exception:
                try:
                    if hold_process.poll() is None: hold_process.terminate();
                except Exception: pass;
        return None;

    @staticmethod
    def _pygame_module():
        try:
            with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                warnings.simplefilter("ignore");
                import pygame;
            return pygame;
        except Exception:
            return None;

    def _start_pygame_hold(self, frequency, volume, initialize=False):
        pygame = self._pygame_module();
        if pygame is None: return False;
        try:
            if not pygame.mixer.get_init():
                if not initialize: return False;
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1);
            sound = pygame.mixer.Sound(file=io.BytesIO(self._wav_bytes(frequency, 2.0, volume)));
            channel = sound.play(loops=-1);
            if channel is None: return False;
            self._hold_channel = channel;
            self._hold_sound = sound;
            self._hold_backend = "pygame";
            return True;
        except Exception:
            return False;

    def _start_pcm_hold(self, command, backend, frequency, volume):
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL);
        except OSError:
            return False;
        # GUI frontends may already own the audio device through Pygame.  Aplay
        # can then spawn successfully but die immediately; do not report that as
        # a usable backend or PLAY HOLD becomes silently stuck.
        time.sleep(.012);
        if process.poll() is not None or process.stdin is None:
            try: process.stdin.close();
            except Exception: pass;
            return False;
        stop_event = threading.Event();
        self._hold_process = process;
        self._hold_stop_event = stop_event;
        self._hold_backend = "pcm:" + str(backend);
        chunk_count = max(32, int(round(self.sample_rate * .010)));
        release_count = max(1, int(round(self.sample_rate * self.release_ms / 1000.0)));
        amplitude = int(11000 * volume);
        def feed_hold():
            sample_index = 0;
            try:
                while not stop_event.is_set() and process.poll() is None:
                    started = time.monotonic();
                    frames = bytearray();
                    for offset in range(chunk_count):
                        phase_index = sample_index + offset;
                        sample = int(amplitude * math.sin((2.0 * math.pi * frequency * phase_index) / self.sample_rate));
                        frames.extend(struct.pack("<h", sample));
                    process.stdin.write(frames);
                    process.stdin.flush();
                    sample_index += chunk_count;
                    elapsed = time.monotonic() - started;
                    stop_event.wait(max(0.0, (chunk_count / float(self.sample_rate)) - elapsed));
                if process.poll() is None and self.release_ms > 0:
                    frames = bytearray();
                    for offset in range(release_count):
                        gain = max(0.0, 1.0 - ((offset + 1) / float(release_count)));
                        phase_index = sample_index + offset;
                        sample = int(amplitude * gain * math.sin((2.0 * math.pi * frequency * phase_index) / self.sample_rate));
                        frames.extend(struct.pack("<h", sample));
                    process.stdin.write(frames);
                    process.stdin.flush();
            except (BrokenPipeError, OSError, ValueError):
                pass;
            finally:
                try: process.stdin.close();
                except Exception: pass;
        thread = threading.Thread(target=feed_hold, name="sumCore-audio-hold", daemon=True);
        self._hold_thread = thread;
        thread.start();
        return True;

    def hold(self, frequency, volume=1.0):
        """Start one cancellable continuous sine with a click-free release.""";
        self.stop();
        frequency = float(frequency);
        volume = max(0.0, min(1.0, float(volume)));
        # If a GUI already initialized the mixer, keep the held note on that
        # device.  This avoids aplay/SoX fighting Pygame for the same sink.
        if self._start_pygame_hold(frequency, volume, initialize=False): return True;
        aplay = shutil.which("aplay");
        if aplay:
            command = [aplay, "-q", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", str(self.sample_rate), "-"];
            if self._start_pcm_hold(command, "aplay", frequency, volume): return True;
        player = shutil.which("play");
        if player:
            command = [player, "-q", "-t", "raw", "-r", str(self.sample_rate), "-e", "signed-integer", "-b", "16", "-c", "1", "-L", "-"];
            if self._start_pcm_hold(command, "sox", frequency, volume): return True;
        if self._start_pygame_hold(frequency, volume, initialize=True): return True;
        return False;

    def play(self, frequency, duration, blocking=True, volume=1.0):
        frequency = float(frequency);
        duration = max(0.0, float(duration));
        volume = max(0.0, min(1.0, float(volume)));
        if duration <= 0.0:
            return None;
        completed = threading.Event() if blocking else None;
        result = [];
        generation = self._current_generation();
        cancel_event = threading.Event();
        self._ensure_worker();
        self._tone_queue.put((generation, cancel_event, frequency, duration, volume, completed, result));
        if completed is not None:
            completed.wait();
            return result[0] if result else False;
        return None;

    def wait_for_background(self):
        self._tone_queue.join();
        return None;

    def _worker_loop(self):
        while True:
            generation, cancel_event, frequency, duration, volume, completed, result = self._tone_queue.get();
            try:
                if generation != self._current_generation():
                    result.append(False);
                    continue;
                with self._active_lock: self._active_cancel_event = cancel_event;
                if generation != self._current_generation() or cancel_event.is_set():
                    result.append(False);
                    continue;
                try:
                    try:
                        result.append(self._play_blocking(frequency, duration, volume));
                    except TypeError:
                        result.append(self._play_blocking(frequency, duration));
                except Exception:
                    result.append(False);
            finally:
                with self._active_lock:
                    if self._active_cancel_event is cancel_event: self._active_cancel_event = None;
                    self._active_process = None;
                if completed is not None:
                    completed.set();
                self._tone_queue.task_done();

    def _play_blocking(self, frequency, duration, volume=1.0):
        if os.name == "nt":
            try:
                import winsound;
                winsound.Beep(max(37, min(32767, int(round(frequency)))), max(1, int(round(duration * 1000.0))));
                return True;
            except Exception:
                pass;
        player = shutil.which("play");
        if player:
            try:
                process = subprocess.Popen([player, "-q", "-v", "{:.4f}".format(volume), "-n", "synth", "{:.6f}".format(duration), "sine", "{:.6f}".format(frequency)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL);
                with self._active_lock: self._active_process = process;
                process.wait();
                return process.returncode == 0;
            except OSError:
                pass;
            finally:
                with self._active_lock:
                    if self._active_process is locals().get("process"): self._active_process = None;
        aplay = shutil.which("aplay");
        if aplay:
            try:
                payload = self._wav_bytes(frequency, duration, volume);
                process = subprocess.Popen([aplay, "-q", "-"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL);
                with self._active_lock: self._active_process = process;
                process.communicate(payload);
                return process.returncode == 0;
            except OSError:
                pass;
            finally:
                with self._active_lock:
                    if self._active_process is locals().get("process"): self._active_process = None;
        try:
            sys.stdout.write("\a");
            sys.stdout.flush();
        except Exception:
            pass;
        with self._active_lock: cancel_event = self._active_cancel_event;
        if cancel_event is None:
            time.sleep(duration);
        else:
            cancel_event.wait(duration);
        return False;

    def _pcm_bytes(self, frequency, duration, volume=1.0):
        count = max(1, int(round(self.sample_rate * float(duration))));
        amplitude = int(11000 * max(0.0, min(1.0, float(volume))));
        frames = bytearray();
        for index in range(count):
            sample = int(amplitude * math.sin((2.0 * math.pi * float(frequency) * index) / self.sample_rate));
            frames.extend(struct.pack("<h", sample));
        return bytes(frames);

    def _wav_bytes(self, frequency, duration, volume=1.0):
        frames = self._pcm_bytes(frequency, duration, volume);
        stream = io.BytesIO();
        with wave.open(stream, "wb") as wav:
            wav.setnchannels(1);
            wav.setsampwidth(2);
            wav.setframerate(self.sample_rate);
            wav.writeframes(frames);
        return stream.getvalue();


class MusicParseError(ValueError):
    pass;


class MusicEvent:
    def __init__(self, frequency, duration, volume=1.0):
        self.frequency = None if frequency is None else float(frequency);
        self.duration = max(0.0, float(duration));
        self.volume = max(0.0, min(1.0, float(volume)));

    def __repr__(self):
        return "MusicEvent({!r}, {!r}, {!r})".format(self.frequency, self.duration, self.volume);


def _remove_music_comments(source):
    result = [];
    comment = False;
    for char in str(source):
        if char == "!":
            comment = not comment;
            continue;
        if not comment:
            result.append(char);
    return "".join(result);


def _read_number(text, index, maximum_digits=None):
    start = index;
    while index < len(text) and text[index].isdigit() and (maximum_digits is None or index - start < maximum_digits):
        index += 1;
    if index == start:
        return None, start;
    return int(text[start:index]), index;


def _expand_zx_repeats(text):
    if str(text).endswith("))"):
        raise MusicParseError("ZXPLAY indefinite phrase repetition with '))' is reserved but not implemented yet");
    stack = [];
    current = [];
    for char in str(text):
        if char == "(":
            stack.append(current);
            current = [];
            continue;
        if char == ")":
            if stack:
                segment = current;
                current = stack.pop() + segment + segment;
            else:
                current = current + list(current);
            continue;
        current.append(char);
    if stack:
        raise MusicParseError("ZXPLAY phrase has an unmatched '('");
    return "".join(current);


class ZXPlayParser:
    """Parser for the useful musical subset of the ZX Spectrum 128 PLAY language.

    Notes, accidentals, octave, duration, rests, tempo, volume, N separators,
    ties, and H are implemented.  AY noise/envelope selectors (M/W/X/U) are
    recognized so historical strings remain parseable; the current sine-wave
    backend does not yet emulate those AY-specific timbres.
    """
    def __init__(self, default_tempo=120):
        self.default_tempo = int(default_tempo);

    def parse(self, source, initial_tempo=None):
        text = _remove_music_comments(source).replace(" ", "").replace("\t", "").replace("\r", "").replace("\n", "");
        text = _expand_zx_repeats(text);
        octave = 5;
        tempo = int(initial_tempo or self.default_tempo);
        duration_code = 5;
        previous_duration_code = 5;
        triplet_remaining = 0;
        volume = 15;
        tie_quarters = 0.0;
        events = [];
        index = 0;
        while index < len(text):
            char = text[index];
            upper = char.upper();
            if upper == "H":
                break;
            if upper == "N":
                index += 1;
                continue;
            if upper in ("O", "T", "V", "W", "X", "U", "M"):
                value, next_index = _read_number(text, index + 1);
                if value is None:
                    raise MusicParseError("ZXPLAY {} requires a number".format(upper));
                if upper == "O":
                    if value < 0 or value > 10: raise MusicParseError("ZXPLAY octave must be 0..10");
                    octave = value;
                elif upper == "T":
                    if value < 60 or value > 240: raise MusicParseError("ZXPLAY tempo must be 60..240 BPM");
                    tempo = value;
                elif upper == "V":
                    if value < 0 or value > 15: raise MusicParseError("ZXPLAY volume must be 0..15");
                    volume = value;
                elif upper == "W" and not 0 <= value <= 7:
                    raise MusicParseError("ZXPLAY envelope W must be 0..7");
                elif upper == "X" and not 0 <= value <= 65535:
                    raise MusicParseError("ZXPLAY envelope period X must be 0..65535");
                elif upper in ("U", "M") and not 0 <= value <= 63:
                    raise MusicParseError("ZXPLAY {} mask must be 0..63".format(upper));
                index = next_index;
                continue;
            if char.isdigit():
                value, next_index = _read_number(text, index, maximum_digits=2);
                if value not in _ZX_DURATION_QUARTERS:
                    raise MusicParseError("ZXPLAY duration code must be 1..12");
                previous_duration_code = duration_code;
                duration_code = value;
                if value >= 10:
                    triplet_remaining = 3;
                index = next_index;
                if index < len(text) and text[index] == "_":
                    tie_quarters += _ZX_DURATION_QUARTERS[duration_code];
                    while index < len(text) and text[index] == "_": index += 1;
                continue;
            accidentals = 0;
            while index < len(text) and text[index] in "#$":
                accidentals += 1 if text[index] == "#" else -1;
                index += 1;
            if index >= len(text):
                if accidentals: raise MusicParseError("ZXPLAY accidental without note");
                break;
            char = text[index];
            upper = char.upper();
            if upper in _NOTE_OFFSETS:
                upper_octave = 1 if char.isupper() else 0;
                midi_note = (12 * octave) + _NOTE_OFFSETS[upper] + (12 * upper_octave) + accidentals;
                quarters = _ZX_DURATION_QUARTERS[duration_code] + tie_quarters;
                tie_quarters = 0.0;
                duration = quarters * (60.0 / float(tempo));
                events.append(MusicEvent(_midi_frequency(midi_note), duration, float(volume) / 15.0));
                index += 1;
                if triplet_remaining:
                    triplet_remaining -= 1;
                    if triplet_remaining == 0:
                        duration_code = previous_duration_code;
                continue;
            if char == "&":
                quarters = _ZX_DURATION_QUARTERS[duration_code] + tie_quarters;
                tie_quarters = 0.0;
                events.append(MusicEvent(None, quarters * (60.0 / float(tempo)), 0.0));
                index += 1;
                if triplet_remaining:
                    triplet_remaining -= 1;
                    if triplet_remaining == 0:
                        duration_code = previous_duration_code;
                continue;
            if char == "_":
                index += 1;
                continue;
            raise MusicParseError("Unsupported ZXPLAY music code {!r}".format(char));
        return events, tempo;


class GWPlayParser:
    """GW-BASIC PLAY Music Macro Language parser for notes and timing."""
    def __init__(self):
        self.default_tempo = 120;

    def _duration(self, denominator, tempo, dots=0):
        if denominator <= 0: raise MusicParseError("GWPLAY note length must be positive");
        base = 240.0 / (float(tempo) * float(denominator));
        factor = 1.0;
        extra = .5;
        for _ in range(dots):
            factor += extra;
            extra /= 2.0;
        return base * factor;

    def parse(self, source):
        text = str(source).replace(" ", "").replace("\t", "").replace("\r", "").replace("\n", "");
        octave = 4;
        length = 4;
        tempo = self.default_tempo;
        articulation = .875;
        requested_mode = "FOREGROUND";
        events = [];
        index = 0;
        while index < len(text):
            char = text[index];
            upper = char.upper();
            if upper in _NOTE_OFFSETS:
                index += 1;
                accidental = 0;
                if index < len(text) and text[index] in "#+-":
                    accidental = -1 if text[index] == "-" else 1;
                    index += 1;
                denominator, next_index = _read_number(text, index);
                if denominator is None:
                    denominator = length;
                else:
                    index = next_index;
                dots = 0;
                while index < len(text) and text[index] == ".":
                    dots += 1;
                    index += 1;
                full_duration = self._duration(denominator, tempo, dots);
                note_duration = full_duration * articulation;
                midi_note = 12 * (octave + 1) + _NOTE_OFFSETS[upper] + accidental;
                events.append(MusicEvent(_midi_frequency(midi_note), note_duration, 1.0));
                if note_duration < full_duration:
                    events.append(MusicEvent(None, full_duration - note_duration, 0.0));
                continue;
            if upper in ("O", "L", "T", "P", "N"):
                value, next_index = _read_number(text, index + 1);
                if value is None:
                    raise MusicParseError("GWPLAY {} requires a number".format(upper));
                index = next_index;
                if upper == "O":
                    if value < 0 or value > 6: raise MusicParseError("GWPLAY octave must be 0..6");
                    octave = value;
                elif upper == "L":
                    if value < 1 or value > 64: raise MusicParseError("GWPLAY length must be 1..64");
                    length = value;
                elif upper == "T":
                    if value < 32 or value > 255: raise MusicParseError("GWPLAY tempo must be 32..255 BPM");
                    tempo = value;
                elif upper == "P":
                    dots = 0;
                    while index < len(text) and text[index] == ".": dots += 1; index += 1;
                    events.append(MusicEvent(None, self._duration(value, tempo, dots), 0.0));
                elif upper == "N":
                    if value == 0:
                        events.append(MusicEvent(None, self._duration(length, tempo), 0.0));
                    else:
                        if value < 1 or value > 84: raise MusicParseError("GWPLAY N note must be 0..84");
                        midi_note = value + 23;
                        full_duration = self._duration(length, tempo);
                        note_duration = full_duration * articulation;
                        events.append(MusicEvent(_midi_frequency(midi_note), note_duration, 1.0));
                        if note_duration < full_duration: events.append(MusicEvent(None, full_duration - note_duration, 0.0));
                continue;
            if upper == "M":
                if index + 1 >= len(text): raise MusicParseError("GWPLAY M requires N/L/S/F/B");
                code = text[index + 1].upper();
                if code == "N": articulation = .875;
                elif code == "L": articulation = 1.0;
                elif code == "S": articulation = .75;
                elif code == "F": requested_mode = "FOREGROUND";
                elif code == "B": requested_mode = "BACKGROUND";
                else: raise MusicParseError("GWPLAY M requires N/L/S/F/B");
                index += 2;
                continue;
            if char == ">":
                octave = min(6, octave + 1);
                index += 1;
                continue;
            if char == "<":
                octave = max(0, octave - 1);
                index += 1;
                continue;
            raise MusicParseError("Unsupported GWPLAY music code {!r}".format(char));
        return events, requested_mode;


class MusicEngine:
    """Queued music bus with concurrent voices inside each ZXPLAY session."""
    def __init__(self, tone_func=None, sleep_func=None):
        self.tone_func = tone_func;
        self.sleep_func = sleep_func if sleep_func is not None else time.sleep;
        self.zx_parser = ZXPlayParser();
        self.gw_parser = GWPlayParser();
        self._queue = queue.Queue();
        self._worker = None;
        self._worker_lock = threading.Lock();
        self._generation = 0;
        self._generation_lock = threading.Lock();
        self._channel_players = [SystemTonePlayer(), SystemTonePlayer(), SystemTonePlayer()];
        self.output_volume = 1.0;
        self._hold_lock = threading.Lock();
        self._hold_signature = None;
        self._hold_timer = None;

    def _ensure_worker(self):
        with self._worker_lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._worker_loop, name="sumBASIC-music", daemon=True);
                self._worker.start();

    def _current_generation(self):
        with self._generation_lock: return self._generation;

    def stop(self):
        with self._generation_lock: self._generation += 1;
        for player in self._channel_players: player.stop();
        with self._hold_lock:
            self._hold_signature = None;
            timer = self._hold_timer;
            self._hold_timer = None;
        if timer is not None: timer.cancel();
        stopper = getattr(self.tone_func, "stop", None) if self.tone_func is not None else None;
        if callable(stopper):
            try: stopper();
            except Exception: pass;
        return None;

    def set_output_volume(self, volume):
        self.output_volume = max(0.0, min(1.0, float(volume)));
        return self.output_volume;

    def _enqueue(self, tracks, background):
        completed = threading.Event();
        generation = self._current_generation();
        self._ensure_worker();
        self._queue.put((generation, tracks, completed));
        if not background:
            completed.wait();
        return completed;

    def play_zx(self, strings, background=False):
        if not 1 <= len(strings) <= 3: raise MusicParseError("ZXPLAY requires one to three music strings");
        tempo = 120;
        tracks = [];
        for index, source in enumerate(strings):
            events, parsed_tempo = self.zx_parser.parse(source, initial_tempo=tempo);
            if index == 0: tempo = parsed_tempo;
            tracks.append(events);
        return self._enqueue(tracks, bool(background));

    def hold_zx(self, source, timeout=3.0):
        """Hold one ZX note; identical calls only renew the safety timeout.""";
        events, unused_tempo = self.zx_parser.parse(source);
        pitched = [event for event in events if event.frequency is not None];
        if len(pitched) != 1: raise MusicParseError("PLAY HOLD requires exactly one note");
        event = pitched[0];
        signature = (str(source), float(event.frequency), float(event.volume));
        timeout = max(0.0, float(timeout));
        with self._hold_lock:
            same = signature == self._hold_signature;
            old_timer = self._hold_timer;
            if old_timer is not None: old_timer.cancel();
            if not same:
                for player in self._channel_players: player.stop();
                volume = event.volume * self.output_volume;
                held = self._channel_players[0].hold(event.frequency, volume);
                if not held:
                    # Last-resort compatibility path: if the continuous backend
                    # cannot open, use the same finite tone renderer that BEEP/
                    # normal PLAY already proved usable.  The safety timeout
                    # bounds the note and PLAY STOP can still cancel it.
                    fallback_duration = max(.05, timeout if timeout > 0.0 else 1.0);
                    self._channel_players[0].play(event.frequency, fallback_duration, False, volume);
                self._hold_signature = signature;
            if timeout > 0.0:
                expected = signature;
                def expire():
                    with self._hold_lock:
                        if self._hold_signature != expected: return;
                        self._hold_signature = None;
                        self._hold_timer = None;
                    self._channel_players[0].stop();
                self._hold_timer = threading.Timer(timeout, expire);
                self._hold_timer.daemon = True;
                self._hold_timer.start();
            else:
                self._hold_timer = None;
        return True;

    def play_gw(self, source, mode=None):
        events, requested_mode = self.gw_parser.parse(source);
        selected = str(mode or requested_mode).upper();
        return self._enqueue([events], selected == "BACKGROUND");

    def wait_for_background(self):
        self._queue.join();
        return None;

    def _worker_loop(self):
        while True:
            generation, tracks, completed = self._queue.get();
            try:
                if generation == self._current_generation(): self._run_tracks(generation, tracks);
            finally:
                completed.set();
                self._queue.task_done();

    def _run_tracks(self, generation, tracks):
        threads = [];
        for index, events in enumerate(tracks):
            thread = threading.Thread(target=self._run_track, args=(generation, index, events), name="sumBASIC-music-{}".format(index), daemon=True);
            threads.append(thread);
            thread.start();
        for thread in threads: thread.join();

    def _run_track(self, generation, channel, events):
        player = self._channel_players[min(channel, len(self._channel_players) - 1)];
        for event in events:
            if generation != self._current_generation(): return;
            if event.duration <= 0.0: continue;
            if event.frequency is None:
                deadline = time.monotonic() + event.duration;
                while generation == self._current_generation() and time.monotonic() < deadline:
                    self.sleep_func(min(.02, max(0.0, deadline - time.monotonic())));
                continue;
            volume = max(0.0, min(1.0, event.volume * self.output_volume));
            if self.tone_func is not None:
                _call_tone_func(self.tone_func, event.frequency, event.duration, True, volume);
            else:
                player.play(event.frequency, event.duration, True, volume);


class AudioEngine:
    """Independent historical sound buses used by the BASIC interpreter."""
    def __init__(self, tone_func=None, sleep_func=None):
        self._custom_tone_func = tone_func;
        self.beep_player = SystemTonePlayer();
        self.sound_player = SystemTonePlayer();
        self.music = MusicEngine(tone_func=tone_func, sleep_func=sleep_func);
        self._volumes = {"BEEP": 1.0, "SOUND": 1.0, "PLAY": 1.0};

    @staticmethod
    def _volume_bus(bus):
        key = str(bus or "ALL").strip().upper();
        if key == "MUSIC": key = "PLAY";
        if key not in ("ALL", "BEEP", "SOUND", "PLAY"):
            raise ValueError("audio volume bus must be ALL, BEEP, SOUND or PLAY");
        return key;

    def set_volume(self, bus, volume):
        key = self._volume_bus(bus);
        value = max(0.0, min(1.0, float(volume)));
        targets = ("BEEP", "SOUND", "PLAY") if key == "ALL" else (key,);
        for target in targets: self._volumes[target] = value;
        self.music.set_output_volume(self._volumes["PLAY"]);
        return value;

    def get_volume(self, bus):
        key = self._volume_bus(bus);
        if key == "ALL": return dict(self._volumes);
        return self._volumes[key];

    def beep(self, frequency, duration):
        volume = self._volumes["BEEP"];
        if self._custom_tone_func is not None: return _call_tone_func(self._custom_tone_func, frequency, duration, True, volume);
        return self.beep_player.play(frequency, duration, True, volume);

    def sound(self, frequency, duration):
        volume = self._volumes["SOUND"];
        if self._custom_tone_func is not None: return _call_tone_func(self._custom_tone_func, frequency, duration, False, volume);
        return self.sound_player.play(frequency, duration, False, volume);

    def zxplay(self, strings, background=False):
        return self.music.play_zx(strings, background=background);

    def zxplay_hold(self, source, timeout=3.0):
        return self.music.hold_zx(source, timeout=timeout);

    def gwplay(self, source, mode=None):
        return self.music.play_gw(source, mode=mode);

    def stop_music(self):
        return self.music.stop();

    def stop_all(self):
        self.beep_player.stop();
        self.sound_player.stop();
        self.music.stop();
        return None;

    def wait_for_background(self):
        if self._custom_tone_func is None: self.sound_player.wait_for_background();
        self.music.wait_for_background();
        return None;
