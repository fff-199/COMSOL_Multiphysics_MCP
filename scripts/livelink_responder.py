#!/usr/bin/env python
"""COMSOL LiveLink 应答器（离线同步协议工具）
协议来源：反编译 LiveLinkCad（case comsol63-install-re E-013/E-015）。

用法：
  python livelink_responder.py inspect  <sync.zip>          # 解析请求或应答包
  python livelink_responder.py respond <request.zip> -o <response.zip> \
         --geom <file.dwg|sat|x_t> [--param name=value ...] \
         [--unit mm]                                       # 生成应答包

协议要点：
  - 交换 = ZIP。请求：requestinfo.txt + sync<N>/parameters.txt（行格式 `parameterName: value`）
  - 应答：exportinfo.txt（必须含 geomunitlength/geomunitangle）+ sync<N>/parameters.txt
    + sync<N>/<几何文件>（接受 .dwg/.sat/.x_t，AutoCAD=LiveLink 原生 dwg）
  - 参数扫掠：多个 sync<N> 目录 + exportinfo 可带 generatedFromParamSweep/hasExtraSync/studyStepTag
  - 接收方式：GUI LiveLink 特征 → Receive File 选应答包（离线模式）；
    headless 触发 requestData/receiveData 属 GUI 桥接命令层，未暴露（已实证）
"""
import argparse
import os
import sys
import zipfile


def inspect(path):
    with zipfile.ZipFile(path) as z:
        print(f"== {path} ({os.path.getsize(path)} bytes) ==")
        for n in z.namelist():
            print("  entry:", n)
        for n in z.namelist():
            if n.endswith(".txt"):
                print(f"--- {n} ---")
                print(z.read(n).decode("utf-8", "replace")[:1500])


def parse_request(path):
    """Return (info: dict, syncs: list[dict[param->value]])."""
    info, syncs = {}, []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            base = n.rsplit("/", 1)[-1]
            if base in ("requestinfo.txt", "exportinfo.txt"):
                for line in z.read(n).decode("utf-8", "replace").splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        info[k.strip()] = v.strip()
            elif base == "parameters.txt":
                d = {}
                for line in z.read(n).decode("utf-8", "replace").splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        d[k.strip()] = v.strip()
                syncs.append(d)
    return info, syncs


def respond(request, out, geom, params=None, unit="mm", angle="deg"):
    params = params or {}
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("exportinfo.txt",
                   f"geomunitlength: {unit}\n"
                   f"geomunitangle: {angle}\n")
        req_info, req_syncs = (parse_request(request) if os.path.exists(request)
                               else ({}, [{}]))
        # one sync step per requested step (or single step if none)
        steps = req_syncs or [{}]
        for i, step in enumerate(steps, 1):
            merged = dict(step)
            merged.update(params)
            lines = [f"{k}: {v}" for k, v in merged.items()]
            z.writestr(f"sync{i}/parameters.txt", "\n".join(lines) + "\n")
            z.write(geom, f"sync{i}/{os.path.basename(geom)}")
    print(f"response written: {out} ({os.path.getsize(out)} bytes, "
          f"{len(steps)} sync step(s), geom={os.path.basename(geom)})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("inspect")
    p1.add_argument("zip")
    p2 = sub.add_parser("respond")
    p2.add_argument("request", nargs="?", default="")
    p2.add_argument("-o", "--out", required=True)
    p2.add_argument("--geom", required=True,
                    help="geometry file to answer with (.dwg/.sat/.x_t)")
    p2.add_argument("--param", action="append", default=[],
                    help="override/add parameter name=value")
    p2.add_argument("--unit", default="mm")
    args = ap.parse_args()
    if args.cmd == "inspect":
        inspect(args.zip)
    else:
        params = dict(p.split("=", 1) for p in args.param if "=" in p)
        respond(args.request, args.out, args.geom, params, args.unit)


if __name__ == "__main__":
    main()
