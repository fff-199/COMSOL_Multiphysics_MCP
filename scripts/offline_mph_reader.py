#!/usr/bin/env python
"""Offline .mph model dossier reader v2 (no COMSOL).

Real .mph dmodel.xml uses TYPED entities: <Physics op="Type" tag="t"> with
<param name-ish> children — different from .mphphb DesignEntity trees.

Usage: python offline_mph_reader.py <model.mph>
"""
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.dirname(HERE)

INTEREST = {"Physics", "Material", "Study", "MeshSequence", "GeomSequence",
            "SolverSequence", "MultiphysicsCoupling", "Probe", "Solution",
            "ModelParam", "Param", "ParamGroup", "Function", "Selection",
            "Component", "Model", "EvaluationFeature", "NumericalFeature",
            "DatasetFeature", "ExportFeature", "PlotGroup", "PlotFeature"}


def catalog_index():
    idx = {}
    p = os.path.join(CAT, "physics_catalog.json")
    if os.path.exists(p):
        cat = json.load(open(p, encoding="utf-8"))
        for mod, ifs in cat.items():
            for i in ifs:
                idx[i["id"]] = {"module": mod.replace("com.comsol.", ""),
                                "license": i.get("_license"),
                                "n_features": len(i.get("_features", []))}
    return idx


def read(mph):
    z = zipfile.ZipFile(mph)
    dossier = {"file": os.path.basename(mph),
               "size_kb": os.path.getsize(mph) // 1024,
               "entries": len(z.namelist()),
               "blobs": [n for n in z.namelist() if n.endswith(".mphbin")],
               "licenses": z.read("usedlicenses.txt").decode("utf-8", "replace").split(),
               "fileversion": z.read("fileversion").decode("utf-8", "replace").strip()}
    root = ET.fromstring(z.read("dmodel.xml").decode("utf-8", "replace"))

    census = Counter(el.tag for el in root.iter())
    dossier["entity_census"] = {k: v for k, v in census.most_common(35)
                                if not k.startswith(("entity", "#"))}

    # physics: op = interface type, features = child <Physics*> typed or op'd
    physics = []
    for el in root.iter("Physics"):
        entry = {"tag": el.get("tag"), "type": el.get("op"), "features": []}
        for sub in el.iter("PhysicsFeature"):
            t = sub.get("op") or sub.get("type")
            if t:
                entry["features"].append(t)
        entry["n_features"] = len(entry["features"])
        entry["feature_types"] = dict(Counter(entry["features"]).most_common(15))
        del entry["features"]
        physics.append(entry)
    dossier["physics"] = physics

    # params: <param ...> at model level are props; real global params in ModelParam/Param nodes
    params = {}
    for el in root.iter("ModelParam"):
        for ex in el.iter("expressions"):
            nm = ex.get("name")
            if nm and ex.get("expr") is not None:
                params[nm] = {"expr": ex.get("expr"), "descr": ex.get("descr", "")}
    dossier["parameters"] = params

    # studies: study steps typed
    studies = defaultdict(list)
    for el in root.iter():
        if el.tag == "Study":
            for st in el.iter():
                t = st.get("op") or st.tag
                if t and t not in ("param",):
                    studies[el.get("tag")].append(t)
    dossier["studies"] = {k: v[:12] for k, v in studies.items()}

    # materials / meshes / functions quick census with types
    for key, tag in (("materials", "Material"), ("meshes", "MeshSequence"),
                     ("functions", "Function"), ("multiphysics", "MultiphysicsCoupling")):
        dossier[key] = sorted(set(el.get("op") or el.tag for el in root.iter(tag)))

    # solver sequences: tag -> top feature types + full feature count
    solvers = {}
    for ss in root.iter("SolverSequence"):
        tops = [ (f.get("op") or f.tag) for f in ss.iter("SolverFeature") ][:6]
        solvers[ss.get("tag")] = {"n_features": sum(1 for _ in ss.iter("SolverFeature")),
                                  "top_types": tops}
    dossier["solver_sequences"] = solvers

    # explicit selections: name -> geom/dim/entities count
    sels = []
    for el in root.iter("explicit"):
        sels.append({"geom": el.get("geom"), "dim": el.get("dim"),
                     "n_entities": len((el.get("entities") or "").split())})
    dossier["explicit_selections"] = sels[:40]
    dossier["n_explicit_selections"] = len(sels)
    return dossier


def main():
    mph = sys.argv[1]
    d = read(mph)
    cat_idx = catalog_index()
    for p in d["physics"]:
        p["in_catalog"] = p["type"] in cat_idx
        p.update(cat_idx.get(p["type"], {}))
    out = os.path.splitext(mph)[0] + "_dossier.json"
    json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{d['file']}  {d['fileversion']}  licenses={d['licenses']}")
    for p in d["physics"]:
        print(f"  physics {p['tag']:6s} {p['type']:42s} cat={'Y' if p['in_catalog'] else 'N'} "
              f"{p.get('module','')} feats={p['n_features']}")
    print("  studies:", d["studies"])
    print("  materials:", d["materials"], "| multiphysics:", d["multiphysics"])
    print("  solvers:", {k: v["top_types"][:4] for k, v in d["solver_sequences"].items()})
    print("  explicit selections:", d["n_explicit_selections"])
    print("  params:", len(d["parameters"]), "entries:", d["entity_census"])
    print("  ->", out)


if __name__ == "__main__":
    main()
