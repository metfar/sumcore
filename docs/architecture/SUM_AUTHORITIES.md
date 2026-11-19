# SUM architecture authorities

| Contract | Authority | Implementation | Role |
|---|---|---|---|
| sum.types/1 | sumCore | sumcore.schema | canonical SUM logical and structured type vocabulary |
| sum.schema/1 | sumCore | sumcore.schema | portable table/schema contract above individual language runtimes |
| sum.indexes/1 | sumCore | sumdoc.sumtab | portable index definitions used to regenerate backend indexes without preserving native index files |
| sumtab/1 | sumCore | sumdoc.sumtab | native SUM tabular interchange and cache format |
| sum.table-conversion/1 | sumCore | sumdoc.tools.tableconvert | table/document conversion policy including automatic destination profiles |
| sum.runtime-utils/1 | sumUtilsRuntime | sumutilsruntime.runtime | portable host-language adaptation API used inside or outside SUM |
| sum.blocks/1 | sumUtilsRuntime | sumutilsruntime.runtime | copy/paste-safe envelope for native runtime serialization; not a cross-language interchange format |
| sum.angle/1 | sumPlot | sumplot.angle | mathematical angular convention: zero on +x and positive counterclockwise |

SUMTAB is a native SUM format. Type, schema and index-definition authority remains above individual language runtimes.

<p align=center><b>- oOo -</b></p>
