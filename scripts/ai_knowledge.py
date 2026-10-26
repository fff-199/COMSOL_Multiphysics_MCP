#!/usr/bin/env python
"""Local AI knowledge interface - one command to query any knowledge asset.
No MCP needed. Works on any machine with Python.

Usage:
  python ai_knowledge.py                       # list all keys
  python ai_knowledge.py cfd_recipe            # read CFD solver recipe
  python ai_knowledge.py variables eta bfc     # search variables for 'eta' in bfc module
  python ai_knowledge.py expr_funcs integrate  # look up function signature
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(BASE), "")  # case数据/

KEYS = {
    "geometry_map": ("geometry_map.json", "135 geom features/16 categories"),
    "mesh_map": ("mesh_map.json", "46 mesh features/9 categories"),
    "results_map": ("results_map.json", "7 result families"),
    "orchestration_map": ("orchestration_map.json", "3 sweep types + batch commands"),
    "material_map": ("material_requirement_map.json", "87 models/375 props/103 classes"),
    "material_lib": ("material_lib_map.json", "17 official material libraries"),
    "discretization": ("discretization_index.json", "181 interfaces/371 orders"),
    "expr_funcs": ("expression_functions.json", "165 expression functions"),
    "variables": ("physics_variables.json", "19,170 physics variables"),
    "couplings": ("coupling_wiring.json", "142 coupling classes"),
    "dmodel_schema": ("mph_dmodel_schema.json", "338 entity tags"),
    "cfd_recipe": ("CFD_solver_recipe.md", "CFD solver defaults"),
    "ec_recipe": ("EC_solver_recipe.md", "EC solver defaults"),
    "heat_sme_recipe": ("Heat_SME_solver_recipe.md", "Heat/Structural solver defaults"),
    "binary_format": ("mph_binary_format.md", ".mph binary format doc"),
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in KEYS:
        print("COMSOL Knowledge Query")
        print("Usage: python ai_knowledge.py <key> [query] [limit]")
        print()
        for k, (_, desc) in sorted(KEYS.items()):
            print(f"  {k:24s} {desc}")
        sys.exit(0)

    fname, desc = KEYS[sys.argv[1]]
    p = os.path.join(DATA, fname)
    if not os.path.exists(p):
        print(f"ERROR: {fname} not found at {p}")
        sys.exit(1)

    if p.endswith(".md"):
        print(open(p, encoding="utf-8").read())
        sys.exit(0)

    data = json.load(open(p, encoding="utf-8"))
    query = sys.argv[2].lower() if len(sys.argv) > 2 else None
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    if not query:
        if isinstance(data, dict):
            print(f"{desc}")
            print(f"Top keys: {list(data)[:15]}")
        elif isinstance(data, list):
            print(f"{desc}; {len(data)} entries")
        sys.exit(0)

    hits = []
    if isinstance(data, dict):
        for k, v in data.items():
            if query in k.lower():
                hits.append({k: v})
            elif isinstance(v, list):
                for item in v:
                    if query in json.dumps(item, ensure_ascii=False).lower():
                        hits.append({k: item})
                        break
            elif isinstance(v, dict):
                # nested: e.g. {class: {variables: [{name, expression}]}}
                if "variables" in v:
                    for var in v["variables"]:
                        if query in var.get("name", "").lower():
                            hits.append({"class": k.split("/")[-1],
                                         "name": var["name"],
                                         "expr": var.get("expression", "")[:120]})
                            if len(hits) >= limit: break
                else:
                    for k2, v2 in v.items():
                        if query in k2.lower() or (isinstance(v2, str) and query in v2.lower()):
                            hits.append({f"{k}.{k2}": v2})
                            break
            if len(hits) >= limit:
                break
    elif isinstance(data, list):
        for item in data:
            if query in json.dumps(item, ensure_ascii=False).lower():
                hits.append(item)
                if len(hits) >= limit:
                    break

    for h in hits:
        print(json.dumps(h, ensure_ascii=False, indent=1))
    print(f"\n{len(hits)} hits for '{query}' in {sys.argv[1]}")

if __name__ == "__main__":
    main()
