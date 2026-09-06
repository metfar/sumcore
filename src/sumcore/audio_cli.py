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

"""Shell entry points for the common Sum audio engine.""";

import argparse;
import signal;
import sys;
import time;

from . import __version__;
from .audio import (
    AudioEngine, GW_BASIC_SOUND_MAX_HZ, GW_BASIC_SOUND_MIN_HZ,
    MusicParseError, gw_ticks_to_seconds, spectrum_frequency_pitch,
    spectrum_pitch_frequency,
);


def _volume(value):
    number = float(value);
    if number < 0.0 or number > 300.0:
        raise argparse.ArgumentTypeError("volume must be between 0 and 300");
    return number;


def _non_negative(value):
    number = float(value);
    if number < 0.0:
        raise argparse.ArgumentTypeError("value must be non-negative");
    return number;


def _parser(name, description):
    parser = argparse.ArgumentParser(prog=name, description=description);
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__));
    return parser;


def _finish(engine):
    try:
        engine.wait_for_background();
    except KeyboardInterrupt:
        engine.stop_all();
        return 130;
    return 0;


def _install_term_handler(engine):
    previous = signal.getsignal(signal.SIGTERM);
    def terminate(unused_signum, unused_frame):
        engine.stop_all();
        raise KeyboardInterrupt();
    signal.signal(signal.SIGTERM, terminate);
    return previous;


def _restore_term_handler(previous):
    signal.signal(signal.SIGTERM, previous);
    return None;


def main_beep(argv=None, audio_factory=AudioEngine):
    parser = _parser("sumbeep", "ZX Spectrum-style BEEP: duration in seconds and pitch in semitones from Middle C.");
    parser.add_argument("duration", type=_non_negative, help="duration in seconds");
    parser.add_argument("pitch", type=float, help="semitones relative to Middle C");
    parser.add_argument("-v", "--volume", type=_volume, default=100.0, help="output percentage (default: 100)");
    args = parser.parse_args(argv);
    engine = audio_factory();
    engine.set_volume("BEEP", args.volume / 100.0);
    previous = _install_term_handler(engine);
    try:
        engine.beep(spectrum_pitch_frequency(args.pitch), args.duration);
    except KeyboardInterrupt:
        engine.stop_all();
        return 130;
    finally:
        _restore_term_handler(previous);
    return 0;


def main_sound(argv=None, audio_factory=AudioEngine):
    parser = _parser("sumsound", "GW-BASIC-style SOUND: frequency in Hz and duration in 18.2 Hz ticks.");
    parser.add_argument("frequency", type=float, help="frequency from 37 to 32767 Hz");
    parser.add_argument("duration", type=_non_negative, help="duration in 18.2 Hz clock ticks");
    parser.add_argument("-v", "--volume", type=_volume, default=100.0, help="output percentage (default: 100)");
    args = parser.parse_args(argv);
    if args.frequency < GW_BASIC_SOUND_MIN_HZ or args.frequency > GW_BASIC_SOUND_MAX_HZ:
        parser.error("frequency must be between 37 and 32767 Hz");
    engine = audio_factory();
    engine.set_volume("SOUND", args.volume / 100.0);
    frequency = spectrum_pitch_frequency(spectrum_frequency_pitch(args.frequency));
    previous = _install_term_handler(engine);
    try:
        engine.sound(frequency, gw_ticks_to_seconds(args.duration));
        return _finish(engine);
    finally:
        _restore_term_handler(previous);


def main_play(argv=None, audio_factory=AudioEngine):
    parser = _parser("sumplay", "Play ZX Spectrum or GW-BASIC music strings through the common Sum audio engine.");
    parser.add_argument("music", nargs="+", help="one to three ZX strings, or one GW-BASIC string with --gw");
    parser.add_argument("--gw", action="store_true", help="interpret one string as GW-BASIC MML");
    parser.add_argument("--hold", action="store_true", help="hold one ZX note instead of playing a finite phrase");
    parser.add_argument("--timeout", type=_non_negative, default=3.0, metavar="SECONDS", help="held-note safety timeout (default: 3; 0 waits for a signal)");
    parser.add_argument("-v", "--volume", type=_volume, default=100.0, help="output percentage (default: 100)");
    args = parser.parse_args(argv);
    if args.gw and len(args.music) != 1:
        parser.error("--gw requires exactly one music string");
    if not args.gw and not 1 <= len(args.music) <= 3:
        parser.error("ZX PLAY requires one to three music strings");
    if args.hold and (args.gw or len(args.music) != 1):
        parser.error("--hold requires exactly one ZX music string");
    engine = audio_factory();
    engine.set_volume("PLAY", args.volume / 100.0);
    previous = _install_term_handler(engine);
    try:
        if args.hold:
            engine.zxplay_hold(args.music[0], timeout=args.timeout);
            if args.timeout == 0.0:
                while True: time.sleep(3600.0);
            else:
                time.sleep(args.timeout);
        elif args.gw:
            engine.gwplay(args.music[0], mode="FOREGROUND");
        else:
            engine.zxplay(args.music, background=False);
    except KeyboardInterrupt:
        engine.stop_all();
        return 130;
    except (MusicParseError, ValueError) as exc:
        engine.stop_all();
        print("sumplay: {}".format(exc), file=sys.stderr);
        return 2;
    finally:
        engine.stop_all();
        _restore_term_handler(previous);
    return 0;


__all__ = ["main_beep", "main_play", "main_sound"];
