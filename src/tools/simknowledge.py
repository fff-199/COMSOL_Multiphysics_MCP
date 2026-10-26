"""Simulation-knowledge tools: offline model dossier + solver recipes.

- model_dossier: read any .mph WITHOUT a COMSOL session (E-023: .mph is a
  ZIP whose dmodel.xml holds typed entities). Cross-references physics
  interface types against the shipped static catalog.
- solver_recipe: return the distilled default-solver recipes (CFD / EC),
  decompiled from the official AutoSolverSuggestion classes (E-017/E-025).
"""

import json
import os
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "resources", "static_catalog")
_RECIPES = {"cfd": "CFD_solver_recipe.md", "ec": "EC_solver_recipe.md",
            "bfc": "EC_solver_recipe.md", "electrochemistry": "EC_solver_recipe.md",
            "heat": "Heat_SME_solver_recipe.md", "sme": "Heat_SME_solver_recipe.md",
            "structural": "Heat_SME_solver_recipe.md", "ht": "Heat_SME_solver_recipe.md"}


def _catalog_index():
    p = os.path.join(_DATA_DIR, "physics_interfaces.json")
    if not os.path.exists(p):
        return {}
    idx = {}
    for i in json.load(open(p, encoding="utf-8")):
        idx[i["id"]] = {"module": i["module"], "license": i.get("license"),
                        "n_features": len(i.get("features", []))}
    return idx


def _read_dossier(model_path: str) -> dict:
    z = zipfile.ZipFile(model_path)
    d = {"file": os.path.basename(model_path),
         "size_kb": os.path.getsize(model_path) // 1024,
         "fileversion": z.read("fileversion").decode("utf-8", "replace").strip(),
         "licenses": z.read("usedlicenses.txt").decode("utf-8", "replace").split(),
         "blobs": [n for n in z.namelist() if n.endswith(".mphbin")]}
    root = ET.fromstring(z.read("dmodel.xml").decode("utf-8", "replace"))

    params = {}
    for el in root.iter("ModelParam"):
        for ex in el.iter("expressions"):
            if ex.get("name") and ex.get("expr") is not None:
                params[ex.get("name")] = {"expr": ex.get("expr"),
                                          "descr": ex.get("descr", "")}
    d["parameters"] = params

    physics = []
    for el in root.iter("Physics"):
        feats = Counter()
        for sub in el.iter("PhysicsFeature"):
            t = sub.get("op") or sub.get("type")
            if t:
                feats[t] += 1
        physics.append({"tag": el.get("tag"), "type": el.get("op"),
                        "feature_types": dict(feats)})
    d["physics"] = physics

    studies = defaultdict(list)
    for el in root.iter("Study"):
        for st in el.iter():
            t = st.get("op") or ""
            if t and t not in ("", "Study"):
                studies[el.get("tag")].append(t)
    d["studies"] = {k: v for k, v in studies.items()}

    d["materials"] = sorted({m.get("op") or "?" for m in root.iter("Material")})

    # solver sequences: tag -> top-level feature types + count
    solvers = {}
    for ss in root.iter("SolverSequence"):
        tops = [(f.get("op") or f.tag) for f in ss.iter("SolverFeature")][:6]
        solvers[ss.get("tag")] = {"n_features": sum(1 for _ in ss.iter("SolverFeature")),
                                  "top_types": tops}
    d["solver_sequences"] = solvers

    # explicit selections: geom/dim/entity count
    sels = []
    for el in root.iter("explicit"):
        sels.append({"geom": el.get("geom"), "dim": el.get("dim"),
                     "n_entities": len((el.get("entities") or "").split())})
    d["explicit_selections"] = sels[:40]
    d["n_explicit_selections"] = len(sels)
    return d


def register_simknowledge_tools(mcp) -> None:
    """Register knowledge tools with the MCP server."""

    @mcp.tool()
    def model_dossier(model_path: str) -> dict:
        """Offline model dossier for any .mph file - NO COMSOL session needed
        (.mph is a ZIP; dmodel.xml holds the entity tree). Returns fileversion,
        licenses, all global parameters (name/expression/description), physics
        interfaces with feature-type counts (cross-checked against the static
        catalog: module + license), full study topology, materials. Use it to
        understand a received model in seconds before loading it."""
        d = _read_dossier(model_path)
        cat = _catalog_index()
        for p in d["physics"]:
            p["in_catalog"] = p["type"] in cat
            p.update(cat.get(p["type"], {}))
        return d

    @mcp.tool()
    def solver_recipe(module: str = "cfd") -> dict:
        """Default solver recipe distilled from the official AutoSolverSuggestion
        classes. module: 'cfd'|'ec'|'heat'|'sme' (pseudo-transient CFL/PID/Anderson, two-phase
        segregated segaacc) or 'ec' (electrochemistry: undamped Newton start,
        transient maxiter=5, PARDISO + mumpsalloc). Read BEFORE hand-tuning a
        non-converging solver - these are the design points COMSOL itself
        generates from."""
        key = (module or "cfd").lower()
        fname = _RECIPES.get(key)
        if not fname:
            return {"error": f"unknown module '{module}'", "available": sorted(set(_RECIPES))}
        p = os.path.join(os.path.dirname(_DATA_DIR), "solver_recipes", fname)
        if not os.path.exists(p):
            return {"error": f"recipe file missing: {fname}"}
        return {"module": key, "recipe": open(p, encoding="utf-8").read()}
