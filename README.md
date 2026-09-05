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

The package also installs `sumbeep`, `sumplay`, and `sumsound`. Android may
currently fall back to a terminal bell/vibration when no PCM output backend is
available; language semantics remain independent from that backend limitation.

<p align=center><b>- oOo -</b></p>
