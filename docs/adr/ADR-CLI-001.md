# ADR-CLI-001 — SUM command-line contract and implementations

**Date:** 2026-11-15  
**Status:** Accepted architecture; initial implementation tested locally (not merged or released)  
**Scope:** SUM command-line tools and future language runtimes

## Context and history

The first version of this decision placed both the authoritative contract and the general `argparse` implementation inside `sumCore`. The design was refined in discussion: `sumCore` remains the upper **architectural authority**, not a dependency on any UI layer. The reusable Python parser belongs to `sumUI`.

This ADR supersedes the parser-location and implementation sections of the earlier draft **SUM-ADR-CLI-001**; the history and rationale are retained here rather than silently erased.

## Decisions

1. **`sumcore.cli_contract` describes, but does not parse:** `CommandSpec`, `OptionSpec`, `ArgumentSpec`, `ExampleSpec`, `ParseResult`. The names represent semantic contracts, not a required class hierarchy in other languages.
2. **The `sumcore` executable is intentionally exceptional:** it handles `--version` and `--help`/`-h` directly using `sys.argv`, without `argparse`, `sumUI`, graphical libraries, or any other CLI framework. Empty input shows help. Unrecognized arguments exit with status 2.
3. **`sumui.cli.SumArgumentParser` is the preferred parser** for new SUM Python applications and command-line tools; it may use standard Python `argparse` internally. Existing commands retain their flags during gradual migrations.
4. **Core library is below UI in runtime dependencies but above it in contract authority:** `sumUI → sumCore`. The reverse dependency is forbidden. No application needs `sumTUI` or `sumGUI` merely to process CLI options.
5. **`--help` (`-h`) and `--version` are baseline conventions.** `--version` refers to the application version, not to the parser package. The `sumCore` standalone command demonstrates the minimal exception.
6. **Theme flags form an opt-in standard** for applications that have a theme provider: `--list-themes`, `--get-theme`/`--getTheme`, and `--set-theme`/`--setTheme THEME`. The kebab-case spelling is canonical. The latter persists a validated preference, using application-owned storage. Query flags do not mutate state. The parser itself never invents a theme catalogue or opens a window. Without a provider, these flags are not advertised or accepted.
7. **A provider implements `list_themes`, `get_theme` and `set_theme`.** A valid theme name is matched case-insensitively to a catalog entry and passed to the provider with its canonical spelling. The provider owns persistence, default fallback and configuration precedence. Failures return a nonzero exit status and must not persist invalid names.
8. **`--theme THEME` for a temporary (nonpersistent) override is deferred**, not part of the initial implemented contract. A universal global-theme vs per-application preference policy is also deferred until a shared settings service is agreed.
9. **A declarative contract should remain language-neutral.** The Python dataclasses are one serialization-friendly expression of SUM semantics. An eventual `sumJava` is a *projected intention*, not a committed deliverable: possible Java interpreter on Python plus a conventional `sumutils.java` runtime library targeting OpenJDK while remaining compatible with standard Oracle JDK. Nothing in the CLI contract assumes a native Java implementation of the parser.
10. **Readability and traceability:** no release/version claim is made by this ADR alone. Documentation and code must distinguish implemented features from future proposals, and all SUM README files close with the traditional vignette below.

## Stable command-line behavior

| Option | Without theme provider | With theme provider | Side effect |
| --- | --- | --- | --- |
| `-h`, `--help` | Help | Help | None |
| `--version` | Application version | Application version | None |
| `--list-themes` | Not available | Alphabetical catalog | None |
| `--get-theme`, `--getTheme` | Not available | Effective theme | None |
| `--set-theme T`, `--setTheme T` | Not available | Validate and save `T` | Persistent theme preference |

Successful commands exit 0; argument errors and invalid theme names exit 2. Ordinary application options are still parsed by the same parser.

## Initial implementation and compatibility

- `sumcore.cli` now uses only `sys.argv`; no `argparse` import.
- `sumcore.cli_contract` provides an initial minimal set of specifications. Command nesting, richer value types, cross-language serialization and advanced validation remain future extensions.
- `sumui.cli` provides `SumArgumentParser`, `ThemeProvider` and a conversion from a simple `CommandSpec` to `argparse`. It preserves `sumui --version` output and the prior CLI entry point.
- Existing tools such as `sumdisp`, `suminfo`, `SES`, `sumdoc` and language runtimes are **not yet migrated**. Adding a common parser does not silently enable theme flags in those tools.
- Theme persistence is delegated to each registered provider. A shared storage/precedence policy remains open.

## Verification targets

Version/help and invalid-argument exit codes; alias equivalence; alphabetized theme list; nonmutating queries; validated persistent saves; no theme capability without a provider; spec-based options; and application-specific flags.

<p align=center><b>- oOo -</b></p>
