# SUM architecture

This directory is generated/maintained from the current SUM package contracts.

The first storage/I/O split is now concrete:

```text
native filesystem / devices
          |
       sumFSA
          |
        sumIO
          |
  runtimes / shell / future terminal
```

`sumFSA` owns path/storage identity. `sumIO` owns capabilities and I/O semantics. A future terminal/session layer can therefore consume file descriptors, pipes, standard streams and serial resources without reimplementing filesystem mapping.

<p align=center><b>- oOo -</b></p>
