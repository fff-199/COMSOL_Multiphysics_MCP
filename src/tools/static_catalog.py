"""Static COMSOL catalog tools (no live session required).

Data source: the declarative registries shipped with every COMSOL install -
plugins/com.comsol.*.jar plugin.xml (OSGi extension points) and
data/completion/*.xml - extracted offline by scripts/generate_static_catalog.py.
This covers ALL installed modules, not just electrochemistry, and includes
license gating, supported space dimensions, feature nesting, multiphysics
couplings, and per-layer type lists (geometry/mesh/solver/study/...).

Use these tools to validate type names BEFORE calling the live create/feature
tools (physics_add, physics_feature_create, electrochemistry_add_feature,
multiphysics_add, ...), and to discover available types for any layer.
Property NAME lists per feature are not statically available (props tokens in
completion data are opaque); query a live session for those.
"""

import json
import os
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "resources", "static_catalog")

_LAYER_DOC = {
    "geometry": "geometry feature types (geom.xml)",
    "mesh": "mesh feature types (mesh.xml)",
    "solver": "top-level solver feature types (sol.xml)",
    "solver_sub": "solver sub-feature types (linear/nonlinear solvers, adaption...)",
    "study": "study step types (study.xml)",
    "function": "function types incl. DNN/GaussianProcess/PolynomialChaosExpansion (func.xml)",
    "plot": "plot types (result.xml)",
    "numerical": "numerical evaluation node types (numerical.xml)",
    "dataset": "dataset types (dataset.xml)",
    "export": "export types (export.xml)",
}


def _load(name):
    with open(os.path.join(_DATA_DIR, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _catalog_info() -> dict:
    return _load("meta")


def _search_interfaces(query: str) -> list:
    q = query.lower()
    interfaces = _load("physics_interfaces")
    out = []
    for i in interfaces:
        hay = " ".join(filter(None, [i.get("id"), i.get("shortname"), i.get("module")])).lower()
        if q in hay:
            out.append({
                "id": i["id"],
                "shortname": i.get("shortname"),
                "module": i["module"],
                "sdimtypes": i.get("sdimtypes"),
                "license": i.get("license"),
                "n_features": len(i["features"]),
            })
    return out


def _interface_features(interface_id: str) -> Optional[dict]:
    interfaces = _load("physics_interfaces")
    for i in interfaces:
        if i["id"].lower() == interface_id.lower():
            return {
                "id": i["id"],
                "module": i["module"],
                "sdimtypes": i.get("sdimtypes"),
                "license": i.get("license"),
                "features": i["features"],
            }
    return None


def _search_couplings(query: str) -> list:
    q = query.lower()
    out = []
    for c in _load("couplings"):
        hay = " ".join(filter(None, [c.get("id"), c.get("descr"), c.get("module")])).lower()
        if q in hay:
            out.append(c)
    return out


def _layer_types(layer: str) -> list:
    layers = _load("layer_types")
    return layers.get(layer)


def register_static_catalog_tools(mcp) -> None:
    """Register static catalog tools with the MCP server."""
    from mcp.server.fastmcp import FastMCP  # noqa: F401  (type kept local)

    @mcp.tool()
    def static_catalog_info() -> dict:
        """Show what the offline static COMSOL catalog covers (version, counts,
        data provenance). Works without a running COMSOL session."""
        info = _catalog_info()
        info["layers"] = _LAYER_DOC
        return info

    @mcp.tool()
    def static_catalog_search(query: str, kind: Optional[str] = None) -> dict:
        """Search physics interfaces and multiphysics couplings in the offline
        static catalog (all modules). Matches interface id / shortname / module
        (e.g. "battery", "LithiumIonBatteryMPH", "NonIsothermalFlow").

        kind: "interface", "coupling", or None for both.

        Returns id, module jar, supported space dimensions (sdimtypes), license
        feature string, and feature count per interface. Use before
        physics_add / multiphysics_add to validate type names and license needs.
        """
        kind = (kind or "both").lower()
        result = {}
        if kind in ("interface", "both"):
            result["interfaces"] = _search_interfaces(query)[:50]
        if kind in ("coupling", "both"):
            result["couplings"] = _search_couplings(query)[:50]
        return result

    @mcp.tool()
    def static_catalog_features(interface_id: str) -> dict:
        """List the full feature type tree of a physics interface from the
        offline static catalog, including nesting (sub-features), domain levels
        (domain/boundary/global) and singleton flags. No live session needed.

        Example: interface_id="SecondaryCurrentDistribution" shows
        ElectrodeSurface, ExternalShort, PorousElectrodeReaction ... and their
        allowed levels - exactly what electrochemistry_add_feature /
        physics_feature_create accept for that interface.
        """
        iface = _interface_features(interface_id)
        if iface is None:
            return {"error": f"interface '{interface_id}' not found; use "
                             "static_catalog_search to discover ids"}
        return iface

    @mcp.tool()
    def static_catalog_layer(layer: str) -> dict:
        """List known type names for one modeling layer from the offline static
        catalog: geometry, mesh, solver, solver_sub, study, function, plot,
        numerical, dataset, export. Use to validate feature/study/function type
        strings before creating them in a live session."""
        types = _layer_types(layer)
        if types is None:
            return {"error": f"unknown layer '{layer}'", "available": sorted(_LAYER_DOC)}
        return {"layer": layer, "types": types,
                "note": _LAYER_DOC.get(layer, "")}
