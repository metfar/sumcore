# SUM ecosystem architecture

```text
native platform
    |
sumFSA ----> sumIO ----> sumTerminal
    |                         |
    +-------------------------+

sumCore / sumData / sumPlot / sumUI
    |
language runtimes + IDE + tools
```

Required dependencies in the matrix describe current package metadata. sumFSA/sumIO establish the storage/I/O boundary; sumTerminal is the first reusable PTY/session consumer built directly on it.

<p align=center><b>- oOo -</b></p>
