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
    "sumCore": {"version":"0.1.0a1", "requires":[], "optional":[], "role":"core architecture and registries"},
    "sumData": {"version":"0.1.0a1", "requires":["sumCore"], "optional":["pyreadr"], "role":"common data objects, datasets and RDS"},
    "sumPlot": {"version":"0.1.0a1", "requires":["sumCore","sumUI"], "optional":["matplotlib","seaborn"], "role":"plot semantics and PlotSpec"},
    "sumR": {"version":"0.1.0a1", "requires":["sumCore","sumData","sumPlot"], "optional":["Rscript"], "role":"R-compatible runtime"},
    "sumPY": {"version":"0.1.0a1", "requires":["sumCore","sumData","sumPlot"], "optional":[], "role":"Python SUM runtime"},
    "sumUI": {"version":"0.1.0a11", "requires":[], "optional":[], "role":"backend-neutral UI contracts"},
    "sumTUI": {"version":"0.8.0a11", "requires":["sumUI"], "optional":["sumGUI"], "role":"terminal presentation"},
    "sumGUI": {"version":"0.2.0a13", "requires":["sumUI"], "optional":["matplotlib","seaborn"], "role":"Pygame presentation"},
    "sumIDE": {"version":"0.2.17", "requires":["sumUI","sumTUI"], "optional":["sumGUI","sumR","sumPY"], "role":"common multi-language IDE"},
    "sumBASIC": {"version":"0.2.15", "requires":["sumUI","sumTUI","sumIDE","sumData","sumPlot"], "optional":["sumGUI"], "role":"BASIC runtime"},
    "sumX": {"version":"0.2.16", "requires":["sumUI","sumTUI","sumIDE","sumData"], "optional":["sumGUI"], "role":"xBase runtime"},
    "sumdiff": {"version":"0.2.8", "requires":["sumUI","sumTUI"], "optional":["sumGUI"], "role":"compare and merge"},
    "sumdoc": {"version":"0.2.3", "requires":[], "optional":[], "role":"document conversion"},
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
    out=Path(directory); out.mkdir(parents=True, exist_ok=True);
    (out/"SUM_ARCHITECTURE.yaml").write_text(_yaml(DEFAULT_ARCHITECTURE));
    rows=[];
    for name,spec in DEFAULT_ARCHITECTURE.items():
        rows.append((name,spec["version"],";".join(spec["requires"]),";".join(spec["optional"]),spec["role"]));
    with (out/"SUM_COMMAND_MATRIX.csv").open("w", newline="") as handle:
        writer=csv.writer(handle); writer.writerow(("package","version","requires","optional","role")); writer.writerows(rows);
    md=["# SUM ecosystem command/dependency matrix", "", "| Package | Version | Required | Optional | Role |", "|---|---|---|---|---|"];
    for row in rows: md.append("| {} | {} | {} | {} | {} |".format(*row));
    (out/"SUM_COMMAND_MATRIX.md").write_text("\n".join(md)+"\n");
    mapmd=["# SUM ecosystem architecture", "", "```text", "sumCore", "|- sumData --> sumR / sumPY / sumBASIC / sumX", "|- sumPlot --> sumR / sumPY / sumBASIC", "`- sumUI --> sumTUI / sumGUI --> sumIDE", "```", "", "Solid dependencies are required; GUI and external renderers are optional."];
    (out/"SUM_ECOSYSTEM_MAP.md").write_text("\n".join(mapmd)+"\n");
    width=900; height=520;
    names=list(DEFAULT_ARCHITECTURE); coords={};
    columns=[["sumCore"],["sumData","sumPlot","sumUI"],["sumR","sumPY","sumTUI","sumGUI"],["sumIDE","sumBASIC","sumX","sumdiff","sumdoc"]];
    for ci,col in enumerate(columns):
        for ri,name in enumerate(col): coords[name]=(90+ci*230,70+ri*90);
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>'];
    for src,spec in DEFAULT_ARCHITECTURE.items():
        if src not in coords: continue;
        for dst in spec["requires"]:
            if dst not in coords: continue;
            x1,y1=coords[dst]; x2,y2=coords[src]; svg.append(f'<line x1="{x1+160}" y1="{y1+25}" x2="{x2}" y2="{y2+25}" stroke="#444" stroke-width="2"/>');
        for dst in spec["optional"]:
            if dst not in coords: continue;
            x1,y1=coords[dst]; x2,y2=coords[src]; svg.append(f'<line x1="{x1+160}" y1="{y1+25}" x2="{x2}" y2="{y2+25}" stroke="#888" stroke-dasharray="6,5"/>');
    for name,(x,y) in coords.items():
        svg += [f'<rect x="{x}" y="{y}" width="160" height="50" rx="8" fill="#f7f7f7" stroke="#222"/>', f'<text x="{x+80}" y="{y+30}" text-anchor="middle" font-family="sans-serif" font-size="15">{name}</text>'];
    svg.append('</svg>'); (out/"SUM_ECOSYSTEM_MAP.svg").write_text("\n".join(svg)+"\n");
    return tuple(out/name for name in ("SUM_ARCHITECTURE.yaml","SUM_ECOSYSTEM_MAP.svg","SUM_ECOSYSTEM_MAP.md","SUM_COMMAND_MATRIX.md","SUM_COMMAND_MATRIX.csv"));

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("directory", nargs="?", default="."); args=parser.parse_args(argv); write_architecture_artifacts(args.directory); return 0;
