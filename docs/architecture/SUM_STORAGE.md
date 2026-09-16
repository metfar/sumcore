# SUM storage contract

`sumFSA 0.1.0a1` establishes the first common storage boundary.

- SUM logical paths use `/` independently of the host.
- POSIX native paths map directly.
- Windows drives map to `/mnt/c`, `/mnt/d`, ... .
- `/mnt` is virtual on Windows and enumerates available drives.
- Linux mount discovery reads `/proc/self/mountinfo`.
- Mounts, Volumes, Locations and directory Entries have explicit common models.
- Applications can translate logical paths to native paths only when they need to call a native API.

Android SAF is intentionally **not implemented yet**. Android currently uses native paths visible to Python/Termux. SAF will require a provider/bridge above Android APIs; raw `content://` values should not become SUM application paths.

<p align=center><b>- oOo -</b></p>
