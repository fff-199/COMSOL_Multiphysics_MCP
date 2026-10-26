#!/usr/bin/env python
"""Offline material-library reader: parse any data/*.mph material library
(zipped .mph, dmodel.xml typed entities) into a structured map, joined with
the E-021 material_requirement_map registry.

Usage: python material_lib_map.py [lib1.mph lib2.mph ...]   (default: all data libs)
Output: material_lib_map.json next to this script + console summary.
"""
import glob
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.dirname(HERE)
DATA = r"F:\comsol\COMSOL63\Multiphysics\data"


def parse_lib(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("dmodel.xml").decode("utf-8", "replace"))
    mats = []
    for m in root.iter("Material"):
        entry = {"name": m.get("name"), "tag": m.get("tag"),
                 "models": [], "n_functions": 0, "function_types": []}
        for mm in m.iter("MaterialModel"):
            entry["models"].append({"op": mm.get("op"), "name": mm.get("name"),
                                    "n_params": len(mm.findall(".//param"))})
        funcs = [f for f in m.iter("FunctionFeature")]
        entry["n_functions"] = len(funcs)
        entry["function_types"] = sorted(set(f.get("op") for f in funcs))
        mats.append(entry)
    return mats


def main():
    libs = sys.argv[1:] or sorted(glob.glob(os.path.join(DATA, "*_lib.mph")))
    req = json.load(open(os.path.join(CAT, "material_requirement_map.json"),
                         encoding="utf-8"))
    reg_models = set(req["material_models"])
    out = {}
    for p in libs:
        name = os.path.basename(p)
        try:
            mats = parse_lib(p)
        except Exception as e:
            print(name, "ERR", e); continue
        out[name] = {"n_materials": len(mats), "materials": mats}
        in_reg = sum(1 for m in mats for mm in m["models"] if mm["op"] in reg_models)
        total_mm = sum(len(m["models"]) for m in mats)
        nfun = sum(m["n_functions"] for m in mats)
        print(f"{name:32s} materials={len(mats):3d} materialModels={total_mm:3d} "
              f"(registry-hit {in_reg}) functions={nfun}")
        for m in mats[:3]:
            ms = [x["op"] for x in m["models"]][:4]
            print(f"    e.g. {m['name'][:44]:46s} models={ms} funcs={m['n_functions']}")
    dst = os.path.join(CAT, "material_lib_map.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("->", dst)


if __name__ == "__main__":
    main()
