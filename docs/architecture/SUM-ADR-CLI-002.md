# ADR-CLI-002 — SUM theme options, integration and persistence

**Status:** Implemented in a local development revision; not published.
**Date:** 2026-11-15.
**Supersedes:** The conditional/manual provider requirement of ADR-CLI-001.

## Context

The first migration to `SumArgumentParser` converted argument parsing, but
`--list-themes`, `--get-theme` and `--set-theme` were only registered when an
application manually passed `theme_provider`. Consequently those options did
not appear in most executables despite the shared parser being installed.

## Decision

- `sumCore` is the normative architecture/contract owner; its own CLI remains
  minimal and independent of sumUI, using `sys.argv`. Other core services may
  retain their existing independent argument handling.
- `sumUI.SumArgumentParser` installs the SUM theme options automatically,
  unless a caller explicitly opts out with `theme_provider=None`. Caller-
  supplied providers remain supported to preserve application-specific data.
- `--list-themes` lists available names; `--get-theme`/`--getTheme` returns
  the effective preferred theme without a write; `--set-theme`/`--setTheme`
  validates and atomically persists the preference. All three actions exit
  without executing the normal command.
- `sumui --set-theme` defines the ecosystem fallback. A command-specific
  `--set-theme` defines an override for that command. Existing session-scoped
  `--theme NAME` arguments remain stronger than a saved preference.
- SUM theme preference metadata is stored at
  `$XDG_CONFIG_HOME/sumui/theme-preferences.json` (or `~/.config/sumui/`).
  This does not rewrite theme definition files or overwrite a program's
  existing JSON configuration. The user-theme catalog is discovered from
  `$XDG_CONFIG_HOME/sumtui/themes/` (or `~/.config/sumtui/themes/`), including
  hidden-theme metadata. Built-ins: ZX, DOS, XBASE, C64, Dark and Light.
- `sumTUI.Application` and `sumGUI.EasyApp` consult the preference when no
  theme is explicitly supplied; explicitly selected themes remain authoritative.
- Existing `sumX` settings are retained and the shared parser uses a provider
  compatible with its preexisting config; `sumdisp` uses one canonical key
  for all aliases. The `sumdoc` and `sumbash` dispatchers expose the common
  informational options without taking over arguments intended for tools,
  scripts or applets.
- The parser and preference manager have no dependence on pygame, Rich, or
  on a Python runtime for a future SUM language: the contract is semantic.

## Limitations

- Programs that explicitly hard-code a theme do not change merely because
  a preference was saved. This is intentional to preserve explicit requests;
  migrating historical hard-coded defaults is separate work.
- The scope of `sumgui` dynamic themes is the palette/color subset supported
  by that renderer; full style-role fidelity is not yet claimed.
- Side-effect-free theme management is validated locally. Full GUI and device
  behavior requires on-device tests; no publication is implied.
- sumJava remains a possible future Python-based interpreter plus an
  independent Java `sumutils.java` runtime usable on OpenJDK/Oracle JDK,
  not a scheduled implementation or Java-native CLI dependency.

<p align=center><b>- oOo -</b></p>
