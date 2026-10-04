#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
# Copyright 2018- William Martinez Bas <metfar@gmail.com>
# GPL-2.0-or-later.
"""Playback of live HTTP audio; STOP disconnects (no time-shift buffering)."""
import shutil;
import subprocess;
import threading;

class StreamPlayer:
    def __init__(self):
        self.url = None;
        self.process = None;
        self.lock = threading.RLock();

    def _dispose(self):
        process = self.process;
        self.process = None;
        if process is not None and process.poll() is None:
            process.terminate();
            try: process.wait(timeout=2);
            except subprocess.TimeoutExpired:
                process.kill(); process.wait();

    def play(self, url, blocking=True):
        with self.lock:
            self._dispose();
            self.url = str(url);
            if not shutil.which("ffplay"):
                raise RuntimeError("STREAMPLAY requires ffplay (FFmpeg)");
            self.process = subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "error", "-autoexit", self.url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL);
            process = self.process;
        if blocking:
            try: return process.wait();
            except KeyboardInterrupt:
                self.stop(); raise;
        return 0;

    def active(self):
        with self.lock: return int(self.process is not None and self.process.poll() is None);

    def stop(self):
        with self.lock: self._dispose();

    def cont(self, blocking=False):
        with self.lock:
            url = self.url;
            if self.active(): return 0;
        if url is None: raise RuntimeError("STREAMCONT without previous STREAMPLAY");
        return self.play(url, blocking=blocking);

    def close(self):
        with self.lock:
            self._dispose();
            self.url = None;
