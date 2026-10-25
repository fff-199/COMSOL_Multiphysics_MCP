"""Tests for the offline static catalog tools (no COMSOL session needed)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.static_catalog import (
    _catalog_info,
    _interface_features,
    _layer_types,
    _search_couplings,
    _search_interfaces,
)


def test_info_counts():
    info = _catalog_info()
    counts = info["counts"]
    assert counts["interfaces"] >= 250          # 291 on COMSOL 6.3 full install
    assert counts["features"] >= 10000          # 14211 on COMSOL 6.3
    assert counts["couplings"] >= 100           # 170 on COMSOL 6.3


def test_search_battery_interfaces():
    hits = _search_interfaces("battery")
    ids = [h["id"] for h in hits]
    assert "LithiumIonBatteryMPH" in ids
    assert "LumpedBattery" in ids
    # supersets beyond the hand-verified electrochemistry registry
    assert any(i in ids for i in ("BatteryPack", "LeadAcidBattery", "BatteryBinaryElectrolyte"))


def test_interface_feature_tree():
    iface = _interface_features("SecondaryCurrentDistribution")
    assert iface is not None
    feat_ids = [f["id"] for f in iface["features"]]
    assert "ElectrodeSurface" in feat_ids
    assert "ExternalShort" in feat_ids
    # nesting: PorousElectrode has sub-features
    por = [f for f in iface["features"] if f["id"] == "PorousElectrode"]
    assert por, "PorousElectrode feature missing"
    subs = [f["id"] for f in iface["features"] if f.get("parent") == "PorousElectrode"]
    assert subs, "PorousElectrode has no sub-features"


def test_search_couplings():
    hits = _search_couplings("Electrochemical")
    ids = [c["id"] for c in hits]
    assert "ElectrochemicalHeating" in ids
    assert "ElectrochemicalHeatSource" in ids


def test_layers():
    mesh = _layer_types("mesh")
    assert mesh and "FreeTet" in mesh and "BndLayer" in mesh
    study = _layer_types("study")
    assert study and "CyclicVoltammetry" in study
    func = _layer_types("function")
    assert func and "Interpolation" in func and "DNN" in func
    geom = _layer_types("geometry")
    assert geom and "Block" in geom and "WorkPlane" in geom


if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        fn()
        print(f"PASS {name}")
    print("all static catalog tests passed")
