# SUM terminal/session architecture

`sumTerminal` is a terminal/session host, not a shell. `sumbash` remains the default shell and can be replaced per session by another executable.

```text
HostTerminalView now             future GUI/drop-down / sumIDE view
          \                         /
                 TerminalSession
                       |
              platform adapter
             POSIX PTY / ConPTY
                       |
                    sumIO
                       |
                    sumFSA
```

The first implementation (`sumterminal 0.1.0a1`) contains the presentation-neutral session lifecycle and POSIX PTY adapter plus a standalone bridge that reuses the host terminal emulator. PTY bytes remain authoritative and are exposed together with incremental UTF-8 text events so a later SUM-owned terminal renderer can consume the same session engine.

`sumbash` is the default command. Explicit commands remain supported because the terminal is process-agnostic.

Windows ConPTY, a SUM-owned VT/xterm screen renderer, tabs/splits/profiles, SSH/serial presentation, drop-down presentation and sumIDE embedding remain subsequent slices.

<p align=center><b>- oOo -</b></p>
