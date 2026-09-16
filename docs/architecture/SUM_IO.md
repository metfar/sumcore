# SUM I/O contract

`sumIO 0.1.0a1` introduces capability-based resources for files, standard streams, pipes, file descriptors and serial/COM endpoints.

The core read contract separates three states:

```text
data available
temporarily no data available
permanent EOF
```

`ReadResult` therefore carries `data`, `would_block` and `eof` independently. Unknown or meaningless resource length is represented as `None` at the common API boundary. Language adapters may translate that value to their own historical convention (for example BASIC `LOF()` now returns `-1`).

`FDResource` is intended to be usable by a future POSIX PTY-backed terminal session. Windows ConPTY integration will require its own native session adapter but can still expose the same higher-level resource semantics.

<p align=center><b>- oOo -</b></p>
