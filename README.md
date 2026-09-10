# sumcore

Core architecture, registry, diagnostics and shared runtime services for the Sum ecosystem.

## Shared audio service

`sumcore.audio` owns the Sum tone engine and ZX/GW music parsers. The same
language-neutral surface is used by sumBASIC, sumPY, sumR and sumX:

```python
from sumcore import beep, midi_frequency, play, sound, stop_audio, tone_pcm_bytes, tone_wav_bytes;

beep(.25, 12);
sound(440, 18.2);
play("T180O5cdefgabC");

# The same canonical sine renderer used by BASIC is available to GUI clients.
a4 = midi_frequency(69);
raw = tone_pcm_bytes(a4, .25, volume=.4);
wav = tone_wav_bytes(a4, .25, volume=.4);
stop_audio();
```

The package installs `sumbeep`, `sumsound` and `sumplay` as command-line
frontends to that same engine.

## `sumaudiod`

`sumcore` also owns `sumaudiod`, a persistent backend-neutral audio service.
The protocol carries tone/hold/stop commands rather than PulseAudio-specific
operations, so frontends do not depend on the host audio API. POSIX systems use
a private Unix-domain socket. The protocol reserves localhost TCP transport for
Windows, where a future WASAPI output can replace the POSIX backend without
changing any Sum language.

The daemon keeps one PCM stream open and writes silence while idle, avoiding
repeated device startup latency. Its mixer supports named concurrent voices,
finite tones, held tones and an 8 ms release envelope. Current persistent POSIX
outputs are attempted in this order when available:

1. PulseAudio through `pacat` (preferred on Termux);
2. SoX `play` raw PCM;
3. ALSA `aplay` raw PCM.

On Termux, normal Sum audio calls auto-start `sumaudiod` when possible. On other
hosts the daemon can be enabled explicitly or started once:

```text
sumaudiod start
sumaudiod status
sumaudiod stop
```

`SUM_AUDIO_SINK` can select a PulseAudio sink explicitly. Without an override,
AAudio is preferred when present, then OpenSL ES, then another non-null sink.
`SUM_AUDIO_DAEMON=0` disables daemon auto-use; `SUM_AUDIO_DAEMON=1` enables
auto-start on every supported host.

## `suminfo`

`suminfo` is a passive observer: collectors query local state without refreshing
repositories, installing/removing software, starting services, changing
configuration, or requesting privilege elevation.  The default command is a
compact overview; `-a/--all` expands every section.

```text
suminfo
suminfo -a
suminfo --group audio
suminfo --group packages
suminfo --group themes
suminfo --list-groups
suminfo --search python
suminfo --json
```

The structured groups are `platform`, `hardware`, `software`, `terminal`,
`audio`, `packages`, `themes`, `sum`, and `simulated`.  Explicit `--group`
requests are detailed even without `--all`.  Package inspection distinguishes
Python metadata/provenance (`pip`, local/editable, VCS, direct/unknown and,
when `dpkg-query` owns the installed files, OS-managed packages) and reports
APT/dpkg or Termux pkg/APT/dpkg inventory without network refreshes.

Theme inventory lists SUM, GTK, GNOME shell, XFCE, KDE and terminal schemes
plus their discovered search paths.  Optional frontends present the same
report in tabs:

```text
suminfo --tui
suminfo --gui
suminfo --gui --group themes
```

Snapshots preserve the structured `sum.info/1` model so later comparisons are
semantic rather than line-oriented:

```text
suminfo --save baseline
suminfo --compare baseline
suminfo --save after-update
suminfo --compare baseline after-update --group packages
```

Windows is recognised only as a standard-user, unsupported preview.  No
Administrator/UAC, Registry inventory or Windows package-manager support is
claimed yet; the code contains explicit extension points for a future tested
port.

<p align=center><b>- oOo -</b></p>
