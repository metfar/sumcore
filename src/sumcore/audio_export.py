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
"""Finite-program audio renderer using sumcore.audio event semantics.

Modes: WAV file (seekable) and headerless signed-16 mono PCM for pipes.
""";
import math;
import struct;
import sys;
import threading;
import wave;
from pathlib import Path;


class AudioExport:
    def __init__(self, destination, audio_format="wav", sample_rate=48000):
        self.destination=str(destination);
        self.audio_format=audio_format.lower();
        self.sample_rate=int(sample_rate);
        if self.audio_format not in ("wav", "raw"):
            raise ValueError("audio format must be wav or raw");
        if not 8000 <= self.sample_rate <= 192000:
            raise ValueError("audio rate must be 8000..192000");
        if self.destination == "-" and self.audio_format == "wav":
            raise ValueError("WAV stdout needs a seekable header: use --audio-format=raw");
        self._lock=threading.Lock();
        self._stream=sys.stdout.buffer if self.destination == "-" else open(self.destination,"wb");
        self._wav=None;
        if self.audio_format == "wav":
            self._wav=wave.open(self._stream,"wb");
            self._wav.setnchannels(1);
            self._wav.setsampwidth(2);
            self._wav.setframerate(self.sample_rate);
        self._closed=False;

    def _write(self, chunk):
        with self._lock:
            if self._closed:
                raise ValueError("audio stream closed");
            if self._wav is not None:
                self._wav.writeframesraw(chunk);
            else:
                self._stream.write(chunk);

    def __call__(self, frequency, duration, blocking=True, volume=1.0):
        from .audio import tone_pcm_bytes;
        self._write(tone_pcm_bytes(frequency,duration,volume,self.sample_rate));
        return None;

    def render_tracks(self, tracks, output_volume=1.0):
        """Mix each ZX channel on its own timeline; emit only one PCM stream.""";
        schedules=[];
        end_time=0.0;
        for events in tracks:
            cursor=0.0;
            spans=[];
            for event in events:
                duration=max(0.0,float(event.duration));
                if event.frequency is not None and duration:
                    spans.append((cursor,cursor+duration,float(event.frequency),float(event.volume)*output_volume));
                cursor+=duration;
            end_time=max(end_time,cursor);
            schedules.extend(spans);
        total=int(round(end_time*self.sample_rate));
        for offset in range(0,total,2048):
            count=min(2048,total-offset);
            pcm=bytearray(count*2);
            for i in range(count):
                t=(offset+i)/self.sample_rate;
                sample=0.0;
                for start,end,freq,vol in schedules:
                    if start <= t < end:
                        sample+=11000*max(0.0,min(3.0,vol))*math.sin(2.0*math.pi*freq*(t-start));
                sample=max(-32768,min(32767,int(sample)));
                struct.pack_into("<h",pcm,2*i,sample);
            self._write(pcm);

    def close(self):
        if self._closed:
            return;
        self._closed=True;
        if self._wav is not None:
            self._wav.close();
        if self.destination != "-":
            self._stream.close();
        else:
            self._stream.flush();
