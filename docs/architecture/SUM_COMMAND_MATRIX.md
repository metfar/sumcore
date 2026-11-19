# SUM ecosystem command/dependency matrix

| Package | Version | Required | Optional | Role |
|---|---|---|---|---|
| sumCore | 0.1.0a25 |  |  | core architecture, identity and shared services |
| sumUtilsRuntime | 0.1.0a1 |  |  | portable host-language adaptation runtime; independent of SUM packages |
| sumUtils | 0.1.0a1 | sumCore;sumUtilsRuntime |  | SUM-aware utility facade over portable runtime services |
| sumFSA | 0.1.0a1 |  |  | logical filesystem, mounts, volumes and locations |
| sumIO | 0.1.0a1 | sumFSA | pyserial | capability-based files, streams, pipes and serial I/O |
| sumData | 0.1.0a2 | sumCore | pyreadr | common data objects, datasets and RDS |
| sumPlot | 0.1.0a5 | sumCore;sumUI;sumUtilsRuntime | matplotlib;seaborn | plot semantics, coordinates and PlotSpec |
| sumR | 0.1.0a7 | sumCore;sumUI;sumTUI;sumData;sumPlot | sumGUI;Rscript | R-compatible runtime |
| sumPY | 0.1.0a10 | sumCore;sumUI;sumTUI;sumData;sumPlot |  | Python SUM runtime |
| sumUI | 0.1.0a22 | sumCore |  | backend-neutral UI contracts |
| sumTUI | 0.8.0a21 | sumUI | sumGUI | terminal presentation |
| sumGUI | 0.2.0a24 | sumCore;sumUI | matplotlib;seaborn;sumPlot;sumData | Pygame presentation |
| sumIDE | 0.2.22 | sumUI;sumTUI | sumGUI;sumR;sumPY | common multi-language IDE |
| sumBASIC | 0.2.37 | sumCore;sumUI;sumTUI;sumIDE;sumX;sumData;sumPlot | sumGUI | BASIC runtime |
| sumX | 0.2.22 | sumCore;sumUI;sumTUI;sumIDE;sumData | sumGUI | xBase runtime |
| sumbash | 0.1.0a16 | sumCore |  | portable shell and multicall toolbox |
| sumTerminal | 0.1.0a3 | sumFSA;sumIO;sumbash;sumGUI;sumKeyboard |  | terminal/session engine, ANSI graphical frontend, configurable fonts and drop-down host |
| sumdiff | 0.2.8 | sumUI;sumTUI | sumGUI | compare and merge |
| sumdoc | 0.3.2 | sumCore |  | document/format conversion, SUMTAB native format and help source tooling |
| sumbuild | 0.1.0a41 |  |  | host/Android build orchestration and runtime staging |
| sumKeyboard | 0.1.0a2 |  |  | portable keyboard profiles |

<p align=center><b>- oOo -</b></p>
