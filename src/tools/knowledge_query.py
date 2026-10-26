"""Generic knowledge query tool: serve any static JSON/MD from the resources
directory through one MCP interface. Eliminates 'AI needs to know file path' overhead.

Query keys map to files in src/resources/static_catalog/ and src/resources/solver_recipes/:
  geometry_map, mesh_map, results_map, orchestration_map, material_requirement_map,
  material_lib_map, discretization_index, expression_functions, physics_variables,
  coupling_wiring, mph_dmodel_schema, CFD_solver_recipe, EC_solver_recipe, mph_binary_format
"""
import json
import os
from typing import Optional

_RES_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "resources", "static_catalog"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "resources", "solver_recipes"),
]

# description of each key for the tool docstring
_KEYS = {
    "geometry_map": "135 geometry features / 16 categories + finalize/kernel/tolerance",
    "mesh_map": "46 mesh features / 9 categories + adapt/BLM/reuse mechanics",
    "results_map": "7 result families (plot/dataset/numerical/probe/export/table/evalGroup)",
    "orchestration_map": "3 sweep types essence + batch job command + study schemas",
    "material_requirement_map": "87 models/375 props + 103 physics classes mat.X needs",
    "material_lib_map": "17 official material libraries (battery/fce/corr/acdc...)",
    "discretization_index": "181 interfaces / 371 element-order fields",
    "expression_functions": "165 built-in expression function signatures",
    "physics_variables": "19,170 physics variables with defining expressions",
    "coupling_wiring": "142 coupling classes: arg.X_here conventions + interface refs",
    "mph_dmodel_schema": "338 entity tags in .mph dmodel.xml",
    "CFD_solver_recipe": "CFD default solver: pseudo-transient CFL/PID/Anderson, two-phase segaacc",
    "EC_solver_recipe": "Electrochemistry default solver: initstep=1/pardiso/mumpsalloc",
    "mph_binary_format": ".mph binary format: 17 segment types, LE f64 solution vectors",
    "Heat_SME_solver_recipe": "Heat/Structural solver defaults (4-module comparison + AI guide)",
}


def _find(key: str) -> Optional[str]:
    for d in _RES_DIRS:
        for ext in (".json", ".md"):
            p = os.path.join(d, key + ext)
            if os.path.exists(p):
                return p
    return None


def register_knowledge_query_tools(mcp) -> None:
    @mcp.tool()
    def knowledge_query(key: str, query: Optional[str] = None, limit: int = 20) -> dict:
        """Query the COMSOL knowledge base (offline, no session). Returns structured
        data from the reverse-engineered registries, solver recipes, and format docs.

        Keys: geometry_map, mesh_map, results_map, orchestration_map,
        material_requirement_map, material_lib_map, discretization_index,
        expression_functions, physics_variables, coupling_wiring, mph_dmodel_schema,
        CFD_solver_recipe, EC_solver_recipe, mph_binary_format

        Args:
            key: which knowledge asset to query (see list above)
            query: optional sub-query (e.g. search within variables/functions)
            limit: max results when query is used
        """
        path = _find(key)
        if not path:
            return {"error": f"unknown key '{key}'", "available": sorted(_KEYS)}
        if path.endswith(".md"):
            return {"key": key, "content": open(path, encoding="utf-8").read()}
        data = json.load(open(path, encoding="utf-8"))
        if not query:
            # return summary + first entries
            if isinstance(data, dict):
                summary = {k: (len(v) if isinstance(v, (list, dict)) else v)
                           for k, v in list(data.items())[:10]}
                return {"key": key, "summary": summary, "note": _KEYS.get(key, ""),
                        "full_size": len(json.dumps(data))}
            return {"key": key, "note": _KEYS.get(key, ""), "data": data}
        # sub-query search
        q = query.lower()
        hits = []
        if isinstance(data, dict):
            for k, v in data.items():
                if q in k.lower():
                    hits.append({"match": k, "data": v})
                elif isinstance(v, list):
                    for item in v:
                        s = json.dumps(item, ensure_ascii=False)
                        if q in s.lower():
                            hits.append({"match": k, "data": item})
                            break
                if len(hits) >= limit:
                    break
        return {"key": key, "query": query, "hits": hits[:limit]}
