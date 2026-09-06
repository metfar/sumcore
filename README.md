# sumcore

Core architecture, registry and release metadata for the Sum ecosystem.

## Shared audio service

`sumcore.audio` owns the Sum tone engine and ZX/GW music parsers. The
language-neutral facade is available directly:

```python
from sumcore import beep, play, sound, stop_audio;

beep(.25, 12);
sound(440, 18.2);
play("T180O5cdefgabC");
stop_audio();
```

The package also installs `sumbeep`, `sumplay`, and `sumsound`. On Termux,
`sumCore` now prefers the native `termux-media-player` command when it is
available, generating temporary WAV data and letting Android's MediaPlayer own
the device. Finite tones include a short silent preroll/postroll inside the same
WAV so Android can open its higher-latency audio path before the requested tone
begins. The defaults are 400 ms preroll and 100 ms postroll; Termux users can
tune them without rebuilding with `SUM_TERMUX_AUDIO_PREROLL_MS` and
`SUM_TERMUX_AUDIO_POSTROLL_MS`. This avoids requiring direct ALSA access from the Unix process. If
that API is unavailable, the ordinary POSIX/Pygame/terminal fallbacks still
apply; language semantics remain independent from the selected backend.

<p align=center><b>- oOo -</b></p>
