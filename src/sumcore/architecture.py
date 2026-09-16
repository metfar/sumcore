#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018- William Martinez Bas <metfar@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
from pathlib import Path;
import argparse;
import csv;

DEFAULT_ARCHITECTURE = {
    "sumCore": {"version":"0.1.0a18", "requires":[], "optional":[], "role":"core architecture, identity and shared services"},
    "sumFSA": {"version":"0.1.0a1", "requires":[], "optional":[], "role":"logical filesystem, mounts, volumes and locations"},
    "sumIO": {"version":"0.1.0a1", "requires":["sumFSA"], "optional":["pyserial"], "role":"capability-based files, streams, pipes and serial I/O"},
    "sumData": {"version":"0.1.0a2", "requires":["sumCore"], "optional":["pyreadr"], "role":"common data objects, datasets and RDS"},
    "sumPlot": {"version":"0.1.0a2", "requires":["sumCore","sumUI"], "optional":["matplotlib","seaborn"], "role":"plot semantics and PlotSpec"},
    "sumR": {"version":"0.1.0a7", "requires":["sumCore","sumUI","sumTUI","sumData","sumPlot"], "optional":["sumGUI","Rscript"], "role":"R-compatible runtime"},
    "sumPY": {"version":"0.1.0a9", "requires":["sumCore","sumUI","sumTUI","sumData","sumPlot"], "optional":[], "role":"Python SUM runtime"},
    "sumUI": {"version":"0.1.0a16", "requires":[], "optional":[], "role":"backend-neutral UI contracts"},
    "sumTUI": {"version":"0.8.0a21", "requires":["sumUI"], "optional":["sumGUI"], "role":"terminal presentation"},
    "sumGUI": {"version":"0.2.0a24", "requires":["sumCore","sumUI"], "optional":["matplotlib","seaborn","sumPlot","sumData"], "role":"Pygame presentation"},
    "sumIDE": {"version":"0.2.22", "requires":["sumUI","sumTUI"], "optional":["sumGUI","sumR","sumPY"], "role":"common multi-language IDE"},
    "sumBASIC": {"version":"0.2.32", "requires":["sumCore","sumUI","sumTUI","sumIDE","sumX","sumData","sumPlot"], "optional":["sumGUI"], "role":"BASIC runtime"},
    "sumX": {"version":"0.2.21", "requires":["sumCore","sumUI","sumTUI","sumIDE","sumData"], "optional":["sumGUI"], "role":"xBase runtime"},
    "sumbash": {"version":"0.1.0a15", "requires":["sumCore"], "optional":[], "role":"portable shell and multicall toolbox"},
    "sumTerminal": {"version":"0.1.0a2", "requires":["sumFSA","sumIO","sumbash","sumGUI","sumKeyboard"], "optional":[], "role":"terminal/session engine, graphical frontend and drop-down host"},
    "sumdiff": {"version":"0.2.8", "requires":["sumUI","sumTUI"], "optional":["sumGUI"], "role":"compare and merge"},
    "sumdoc": {"version":"0.2.3", "requires":[], "optional":[], "role":"document conversion and help source tooling"},
    "sumbuild": {"version":"0.1.0a41", "requires":[], "optional":[], "role":"host/Android build orchestration and runtime staging"},
    "sumKeyboard": {"version":"0.1.0a2", "requires":[], "optional":[], "role":"portable keyboard profiles"},
};


def _yaml(data):
    lines=["schema: sum.architecture/1", "packages:"];
    for name,spec in data.items():
        lines.append("  {}:".format(name));
        lines.append("    version: {}".format(spec["version"]));
        lines.append("    role: {}".format(spec["role"]));
        lines.append("    requires: [{}]".format(", ".join(spec["requires"])));
        lines.append("    optional: [{}]".format(", ".join(spec["optional"])));
    return "\n".join(lines)+"\n";


def write_architecture_artifacts(directory="."):
    out=Path(directory); out.mkdir(parents=True,exist_ok=True);
    (out/"SUM_ARCHITECTURE.yaml").write_text(_yaml(DEFAULT_ARCHITECTURE),encoding="utf-8");
    rows=[];
    for name,spec in DEFAULT_ARCHITECTURE.items(): rows.append((name,spec["version"],";".join(spec["requires"]),";".join(spec["optional"]),spec["role"]));
    with (out/"SUM_COMMAND_MATRIX.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.writer(handle); writer.writerow(("package","version","requires","optional","role")); writer.writerows(rows);
    md=["# SUM ecosystem command/dependency matrix","","| Package | Version | Required | Optional | Role |","|---|---|---|---|---|"];
    for row in rows: md.append("| {} | {} | {} | {} | {} |".format(*row));
    md += ["","<p align=center><b>- oOo -</b></p>"]; (out/"SUM_COMMAND_MATRIX.md").write_text("\n".join(md)+"\n",encoding="utf-8");
    mapmd=["# SUM ecosystem architecture","","```text","native platform","    |","sumFSA ----> sumIO ----> sumTerminal","    |                         |","    +-------------------------+","","sumCore / sumData / sumPlot / sumUI","    |","language runtimes + IDE + tools","```","","Required dependencies in the matrix describe current package metadata. sumFSA/sumIO establish the storage/I/O boundary; sumTerminal is the first reusable PTY/session consumer built directly on it.","","<p align=center><b>- oOo -</b></p>"];
    (out/"SUM_ECOSYSTEM_MAP.md").write_text("\n".join(mapmd)+"\n",encoding="utf-8");
    columns=[["sumCore","sumFSA","sumUI"],["sumData","sumIO","sumTUI","sumGUI"],["sumPlot","sumPY","sumR","sumIDE","sumbash","sumTerminal"],["sumBASIC","sumX","sumdiff","sumdoc","sumbuild","sumKeyboard"]];
    coords={}; width=1120; height=660;
    for ci,column in enumerate(columns):
        for ri,name in enumerate(column): coords[name]=(50+ci*270,40+ri*95);
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>'];
    for src,spec in DEFAULT_ARCHITECTURE.items():
        if src not in coords: continue;
        for dst in spec["requires"]:
            if dst not in coords: continue;
            x1,y1=coords[dst]; x2,y2=coords[src]; svg.append(f'<line x1="{x1+190}" y1="{y1+26}" x2="{x2}" y2="{y2+26}" stroke="#444" stroke-width="2"/>');
        for dst in spec["optional"]:
            if dst not in coords: continue;
            x1,y1=coords[dst]; x2,y2=coords[src]; svg.append(f'<line x1="{x1+190}" y1="{y1+26}" x2="{x2}" y2="{y2+26}" stroke="#888" stroke-dasharray="6,5"/>');
    for name,(x,y) in coords.items():
        svg += [f'<rect x="{x}" y="{y}" width="190" height="52" rx="8" fill="#f7f7f7" stroke="#222"/>',f'<text x="{x+95}" y="{y+31}" text-anchor="middle" font-family="sans-serif" font-size="15">{name}</text>'];
    svg.append('</svg>'); (out/"SUM_ECOSYSTEM_MAP.svg").write_text("\n".join(svg)+"\n",encoding="utf-8");
    return tuple(out/name for name in ("SUM_ARCHITECTURE.yaml","SUM_ECOSYSTEM_MAP.svg","SUM_ECOSYSTEM_MAP.md","SUM_COMMAND_MATRIX.md","SUM_COMMAND_MATRIX.csv"));


def main(argv=None):
    from . import __version__;
    parser=argparse.ArgumentParser(prog="sum-architecture"); parser.add_argument("--version",action="version",version="sum-architecture {}".format(__version__)); parser.add_argument("directory",nargs="?",default="."); args=parser.parse_args(argv); write_architecture_artifacts(args.directory); return 0;
