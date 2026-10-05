# sumcore: STREAM, ASC and sumfont

Commands `sum-audio-server`, `sum-audio-admin`, `sum-audio-client`, `sum-charset` are installed using `python3 -m pip install --user .` (when user installs are enabled). Their executables normally appear in `~/.local/bin`.

`sumcore.stream.StreamPlayer` handles HTTP audio with FFplay: STOP disconnects immediately, CONT reconnects to live, CLOSE releases saved URL. A reconnect is **not** a time-shift seek. The `sumcore.charset` catalogue is the shared 3135-slot extended ASC table; Spectrum/BASIC command annotations are legacy metadata and must not drive other language runtimes. Existing `sumgui.fontcatalog` and `sumdoc.tools.fontbitmap` contain font-related functions. **sumfont is not an independently verified package in this tree**: the font APIs and glyph formats must be documented and stabilized before claiming a shared sumfont service.

<p align=center><b>- oOo -</b></p>
