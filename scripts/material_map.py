# Material <-> physics requirement map:
# 1) full materialmodel registry (materialproperty children + modelinput + parent)
# 2) mat.<prop> references per decompiled physics class
# 3) join -> per-class required material properties + supplying material models
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

P = r"F:\comsol\COMSOL63\Multiphysics\plugins"
SRC = r"C:\Users\fff\ZCodeProject\reverse-skill\work\comsol63-install-re\artifacts\tools\src_all"
OUT = r"F:\comsol files\COMSOL逆向笔记\case数据\material_requirement_map.json"

# --- 1) registry ---
models = {}
for jp in sorted(glob.glob(os.path.join(P, "com.comsol.*.jar"))):
    try:
        z = zipfile.ZipFile(jp) if False else __import__("zipfile").ZipFile(jp)
        if "plugin.xml" not in z.namelist():
            continue
        txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "",
                     z.read("plugin.xml").decode("utf-8", "replace").replace("\ufeff", ""))
        r = ET.fromstring(txt)
        mod = os.path.basename(jp).replace("com.comsol.", "").replace("_1.0.0.jar", "")
        for ext in r.iter("extension"):
            if ext.get("point") != "com.comsol.model.physicalquantityprovider":
                continue
            for el in ext:
                if el.tag != "materialmodel":
                    continue
                m = {"module": mod, "parent": el.get("parent"),
                     "descr": el.get("descr"),
                     "properties": [], "model_inputs": []}
                for c in el:
                    if c.tag == "materialproperty":
                        m["properties"].append({
                            k: c.get(k) for k in
                            ("name", "materialtype", "unit", "expr",
                             "physicalquantity", "size", "descr") if c.get(k)})
                    elif c.tag == "modelinput":
                        m["model_inputs"].append(c.get("physicalquantity"))
                models[el.get("name")] = m
    except Exception:
        continue

# prop -> supplying models
prop2models = {}
for name, m in models.items():
    for p in m["properties"]:
        prop2models.setdefault(p["name"], []).append(
            {"model": name, "module": m["module"], "unit": p.get("unit"),
             "default": p.get("expr")})

# --- 2) mat.X references per class ---
re_mat = re.compile(r'"mat\.([a-zA-Z_][a-zA-Z0-9_]*)"')
classes = {}
for root, _, files in os.walk(SRC):
    for fn in files:
        if not fn.endswith(".java"):
            continue
        rel = os.path.relpath(os.path.join(root, fn), SRC).replace("\\", "/")
        txt = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        refs = sorted(set(re_mat.findall(txt)))
        if refs:
            classes[rel] = refs

# --- 3) join summary ---
unsupplied = {}
for rel, refs in classes.items():
    for p in refs:
        if p not in prop2models:
            unsupplied.setdefault(p, []).append(rel.split("/")[-1])

summary = {
    "registry": {"n_material_models": len(models)},
    "physics_side": {"n_classes_referencing_mat": len(classes)},
    "props_total": len(prop2models),
    "props_unsupplied_by_registry": {k: v[:3] for k, v in sorted(unsupplied.items())[:20]},
}
print(json.dumps(summary, ensure_ascii=False, indent=1))
top = sorted(classes.items(), key=lambda x: -len(x[1]))[:8]
for rel, n in top:
    print(f"  {rel.split('/')[-1]:45s} uses {n} mat props")
json.dump({"material_models": models,
           "prop2supplying_models": prop2models,
           "physics_class_mat_refs": classes},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", OUT)
