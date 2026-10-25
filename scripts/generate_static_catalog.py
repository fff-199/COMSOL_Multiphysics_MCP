#!/usr/bin/env python
"""Regenerate the static COMSOL catalog data for the static_catalog_* tools.

Reads an installed COMSOL tree (default: F:\\comsol\\COMSOL63\\Multiphysics)
and extracts, fully offline:

1. Physics interface registry from plugins/com.comsol.*.jar plugin.xml
   (`com.comsol.model.applmodecreator` extension point: physicsid +
   nested featureid, plus couplingid multiphysics couplings).
2. Model Wizard navigation tree (physics areas, physics entries,
   multiphysics presets with their physics combinations) from
   `com.comsol.guimph.modelnavigatorphysicsinfoprovider`.
3. Layer type lists (geometry / mesh / solver / study / function / plot /
   dataset / numerical / export) from data/completion/*.xml.
4. Material models, tensor functions and physical quantities from
   `com.comsol.model.physicalquantityprovider`.

Output: src/resources/static_catalog/*.json next to this repository.

Usage:
    python scripts/generate_static_catalog.py [COMSOL_ROOT]

The extraction mirrors the reverse-engineering case documented in
reverse-skill work/comsol63-install-re (E-002/E-004): plugin.xml and
data/completion are declarative, unobfuscated registries shipped with
every COMSOL install.
"""

import json
import os
import re
import sys
import zipfile
import glob
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_DIR = os.path.join(REPO, "src", "resources", "static_catalog")


def _clean_xml(raw: bytes) -> str:
    txt = raw.decode("utf-8", "replace").replace("\ufeff", "")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", txt)


def _iter_plugin_xml(comsol_root):
    for sub in ("plugins", "apiplugins"):
        for jp in sorted(glob.glob(os.path.join(comsol_root, sub, "*.jar"))):
            try:
                z = zipfile.ZipFile(jp)
            except Exception:
                continue
            if "plugin.xml" not in z.namelist():
                continue
            base = os.path.basename(jp).replace("_1.0.0.jar", "").replace(".jar", "")
            try:
                yield base, ET.fromstring(_clean_xml(z.read("plugin.xml")))
            except Exception:
                continue


def extract_registry(comsol_root):
    """plugin.xml physics interfaces + features + couplings + navtree."""
    interfaces = []
    couplings = []
    navtree = {"physicsarea": [], "physics": [], "multiphysics": []}

    def walk_features(el, parent, depth):
        out = []
        for f in el.findall("featureid"):
            node = {
                "id": f.get("id"),
                "depth": depth,
                "parent": parent,
                "domainlevels": f.get("domainlevels"),
                "singleton": f.get("singleton") == "true" or None,
            }
            out.append(node)
            out.extend(walk_features(f, f.get("id"), depth + 1))
        return out

    for base, root in _iter_plugin_xml(comsol_root):
        for ext in root.iter("extension"):
            point = ext.get("point")
            if point == "com.comsol.model.applmodecreator":
                for p in ext.findall("physicsid"):
                    lic = p.find("license")
                    interfaces.append({
                        "id": p.get("id"),
                        "shortname": p.get("shortname"),
                        "sdimtypes": p.get("sdimtypes"),
                        "license": lic.get("licenses") if lic is not None else None,
                        "module": base,
                        "features": walk_features(p, p.get("id"), 1),
                    })
                for c in ext.findall("couplingid"):
                    couplings.append({
                        "id": c.get("id"),
                        "descr": c.get("descr"),
                        "module": base,
                    })
            elif point == "com.comsol.guimph.modelnavigatorphysicsinfoprovider":
                for tag in ("physicsarea", "physics", "multiphysics"):
                    for el in ext.iter(tag):
                        entry = dict(el.attrib)
                        entry["module"] = base
                        if tag == "multiphysics":
                            entry["physics"] = [
                                c.get("id") or c.get("name")
                                for c in el.iter("physics")
                            ]
                        navtree[tag].append(entry)
    return interfaces, couplings, navtree


def extract_quantity_providers(comsol_root):
    materialmodels, tensorfunctions, quantities = [], [], []
    for base, root in _iter_plugin_xml(comsol_root):
        for ext in root.iter("extension"):
            if ext.get("point") != "com.comsol.model.physicalquantityprovider":
                continue
            for el in ext:
                key = {"materialmodel": materialmodels,
                       "tensorfunction": tensorfunctions,
                       "physicalquantity": quantities}.get(el.tag)
                if key is None:
                    continue
                key.append({
                    "id": el.get("id") or el.get("name") or el.get("quantity"),
                    "module": base,
                })
    return materialmodels, tensorfunctions, quantities


def extract_completion_layers(comsol_root):
    """Node-type lists from data/completion/*.xml (props tokens are opaque;
    element names are the human/API type names)."""
    comp_dir = os.path.join(comsol_root, "data", "completion")
    layers = {}

    def child_types(tree, container_tag):
        found = {}

        def walk(n):
            if n.tag == container_tag:
                for c in n:
                    found[c.tag] = found.get(c.tag, 0) + 1
            for c in n:
                walk(c)

        for t in tree:
            walk(t)
        return sorted(found)

    spec = {
        "geometry": ("geom.xml", "GeomFeature"),
        "mesh": ("mesh.xml", "MeshFeature"),
        "solver": ("sol.xml", "SolverFeature"),
        "solver_sub": ("sol.xml", None),  # handled specially below
        "study": ("study.xml", "StudyFeature"),
        "function": ("func.xml", "FunctionFeature"),
        "numerical": ("numerical.xml", "NumericalFeature"),
        "dataset": ("dataset.xml", "DatasetFeature"),
        "export": ("export.xml", "ExportFeature"),
    }
    for layer, (fname, cont) in spec.items():
        path = os.path.join(comp_dir, fname)
        if not os.path.exists(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except Exception:
            continue
        if cont is not None:
            layers[layer] = child_types(root, cont)
    # plot types: children of PlotGroup* nodes (2D/3D/1D groups hold the types)
    res = os.path.join(comp_dir, "result.xml")
    if os.path.exists(res):
        root = ET.parse(res).getroot()
        plots = {}

        def walk_plots(n):
            if n.tag.startswith("PlotGroup"):
                for c in n:
                    plots[c.tag] = plots.get(c.tag, 0) + 1
            for c in n:
                walk_plots(c)

        walk_plots(root)
        layers["plot"] = sorted(plots)
    # solver sub-features: children of solver feature children
    sol = os.path.join(comp_dir, "sol.xml")
    if os.path.exists(sol):
        root = ET.parse(sol).getroot()
        sub = {}

        def walk(n, in_feat):
            if in_feat:
                for c in n:
                    sub[c.tag] = sub.get(c.tag, 0) + 1
                    walk(c, True)
            else:
                for c in n:
                    walk(c, c.tag == "SolverFeature")

        walk(root, False)
        layers["solver_sub"] = sorted(sub)
    return layers


def main():
    comsol_root = sys.argv[1] if len(sys.argv) > 1 else r"F:\comsol\COMSOL63\Multiphysics"
    if not os.path.isdir(os.path.join(comsol_root, "plugins")):
        sys.exit(f"not a COMSOL install root: {comsol_root}")
    os.makedirs(OUT_DIR, exist_ok=True)

    interfaces, couplings, navtree = extract_registry(comsol_root)
    mm, tf, pq = extract_quantity_providers(comsol_root)
    layers = extract_completion_layers(comsol_root)

    def dump(name, obj):
        path = os.path.join(OUT_DIR, name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        print(f"wrote {path} ({os.path.getsize(path)} bytes)")

    dump("physics_interfaces", interfaces)
    dump("couplings", couplings)
    dump("navtree", navtree)
    dump("quantity_providers", {
        "material_models": mm,
        "tensor_functions": tf,
        "physical_quantities": pq,
    })
    dump("layer_types", layers)
    readme = os.path.join(comsol_root, "readme.txt")
    version = None
    if os.path.exists(readme):
        m = re.search(r"COMSOL ([0-9.]+)", open(readme, encoding="utf-8", errors="ignore").read())
        if m:
            version = m.group(1)
    dump("meta", {
        "comsol_root": comsol_root,
        "comsol_version": version,
        "source": "static extraction: plugin.xml (OSGi) + data/completion/*.xml",
        "counts": {
            "interfaces": len(interfaces),
            "features": sum(len(i["features"]) for i in interfaces),
            "couplings": len(couplings),
            "multiphysics_presets": len(navtree["multiphysics"]),
            "material_models": len(mm),
        },
    })
    print(f"interfaces={len(interfaces)} "
          f"features={sum(len(i['features']) for i in interfaces)} "
          f"couplings={len(couplings)}")


if __name__ == "__main__":
    main()
