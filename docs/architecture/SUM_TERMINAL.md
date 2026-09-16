# SUM Terminal architecture

`sumTerminal` is the SUM terminal/session host. It is deliberately separate from `sumbash`: `sumbash` is a shell, while `sumTerminal` owns terminal sessions, PTY transport and presentation.

The default command is `sumbash`, but a session may host any process that can run behind the platform terminal adapter.

```text
TerminalSession
      |
      +-- POSIX PTY adapter
      |       |
      |     sumIO
      |       |
      |     sumFSA
      |
      +-- TerminalScreen
              |
        GuiTerminalView
```

## 0.1.0a2 graphical/drop-down slice

The graphical frontend is now the normal `sumterminal` presentation when `sumGUI`/Pygame is available. `--host` keeps the original bridge to the terminal emulator that launched SUM, and `--gui` forces the graphical frontend.

`TerminalScreen` is a SUM-owned VT/xterm screen model. The first implementation covers the control sequences required by normal interactive shells and common applications: cursor movement, erase operations, SGR colours including 256/true-colour forms, scrolling regions, alternate screen, title OSC, and visible cursor state.

Drop-down mode is selected with:

```text
sumterminal --drop-down
```

The persistent drop-down session is toggled by an IPC command rather than starting a new shell each time. The default global shortcut is `Ctrl+F12`; the installed desktop shortcut executes:

```text
sumterminal --toggle
```

If no drop-down instance exists, `--toggle` starts one. If it already exists, the same command changes only its visibility, preserving the running shell and sessions.

Preferences are stored in the user's SUM configuration directory (`~/.config/sum/terminal.toml` on normal XDG/POSIX systems). The current drop-down preferences include shortcut, height, width and opacity. `sumterminal --preferences` opens the graphical preference editor, while `sumterminal --install` asks `sumKeyboard` to register the shortcut with a supported desktop keyboard backend.

Global shortcut registration belongs to `sumKeyboard`, not to terminal rendering. The initial automatic backends cover GNOME custom keybindings, XFCE keyboard shortcuts and `xbindkeys` when available. Unsupported desktops are reported explicitly rather than pretending installation succeeded.

Windows ConPTY, native Windows global-hotkey registration, Android presentation and richer VT compatibility remain later platform slices.

<p align=center><b>- oOo -</b></p>
