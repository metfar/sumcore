"""Audio broadcast state and shared primitives."""
from collections import deque;
import threading;
import subprocess;

class Station:
    def __init__(self, route, category, source, mode, ffmpeg, bitrate='128k', source_format='wav', sample_rate=48000):
        self.route, self.category, self.source, self.mode = route, category, source, mode;
        self.ffmpeg, self.bitrate = ffmpeg, bitrate;
        self.source_format, self.sample_rate = source_format, sample_rate;
        self.lock = threading.Condition();
        self.chunks = deque(maxlen=192);
        self.counter = 0;
        self.listeners = 0;
        self.ended = False;
        self.process = None;
        self.thread = None;

    def start(self):
        cmd = [self.ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'error', '-re'];
        if self.mode == 'file':
            cmd += ['-stream_loop', '-1', '-i', self.source];
        elif self.mode == 'tone':
            cmd = [self.ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'error', '-re', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100'];
        else:
            if self.source_format == 'raw':
                cmd += ['-f', 's16le', '-ar', str(self.sample_rate), '-ac', '1'];
            cmd += ['-i', 'pipe:0'];
        cmd += ['-vn', '-ar', '44100', '-ac', '2', '-codec:a', 'libmp3lame', '-b:a', self.bitrate, '-f', 'mp3', 'pipe:1'];
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE if self.mode == 'live' else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=None, bufsize=0);
        self.thread = threading.Thread(target=self._produce, daemon=True, name='station-' + self.route);
        self.thread.start();

    def _produce(self):
        try:
            while True:
                chunk = self.process.stdout.read(4096);
                if not chunk:
                    break;
                with self.lock:
                    self.chunks.append((self.counter, chunk));
                    self.counter += 1;
                    self.lock.notify_all();
        finally:
            with self.lock:
                self.ended = True;
                self.lock.notify_all();

    def read(self, position):
        with self.lock:
            while position >= self.counter and not self.ended:
                self.lock.wait(1.0);
            if position >= self.counter:
                return None, position;
            oldest = self.chunks[0][0];
            position = max(position, oldest);
            return self.chunks[position-oldest][1], position + 1;

    def stop(self):
        if self.process is not None:
            if self.process.stdin is not None:
                try: self.process.stdin.close();
                except OSError: pass;
            if self.process.poll() is None:
                self.process.terminate();
                try: self.process.wait(timeout=2);
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait();
        with self.lock:
            self.ended = True;
            self.lock.notify_all();

    def status(self):
        with self.lock:
            return {'route': self.route, 'category': self.category, 'source': self.source, 'mode': self.mode, 'listeners': self.listeners, 'active': not self.ended};
