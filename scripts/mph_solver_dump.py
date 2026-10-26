#!/usr/bin/env python
"""Offline solver-sequence dumper: extract complete solver trees (op/tag +
key parameters) from any .mph without COMSOL. Usage: python mph_solver_dump.py <model.mph>"""
import sys
import zipfile
import xml.etree.ElementTree as ET

KEEP = ("tol", "step", "iter", "damp", "method", "order", "solver", "cfl",
        "active", "keep", "tlist", "tmax", "range", "max", "min", "init")


def tree(el, d=0, md=12, out=None):
    op = el.get("op") or el.tag
    tg = el.get("tag", "")
    props = {p.get("param"): p.get("value") for p in el.findall("param")}
    keep = {k: v for k, v in props.items()
            if any(s in k.lower() for s in KEEP)}
    out.append("  " * d + f"{op}[{tg}]" + (f"  {keep}" if keep else ""))
    if d < md:
        for c in el:
            if c.tag in ("SolverFeature", "SolverFeatureList"):
                tree(c, d + 1, md, out)


def main():
    z = zipfile.ZipFile(sys.argv[1])
    root = ET.fromstring(z.read("dmodel.xml").decode("utf-8", "replace"))
    for ss in root.iter("SolverSequence"):
        nf = sum(1 for f in ss.iter("SolverFeature"))
        out = []
        tree(ss, 0, 12, out)
        print(f"\n===== {ss.get('tag')} ({nf} features) =====")
        print("\n".join(out))


if __name__ == "__main__":
    main()
