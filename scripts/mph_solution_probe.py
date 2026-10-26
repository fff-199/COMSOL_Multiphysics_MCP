#!/usr/bin/env python
"""Probe solved .mph model structure: list all zip entries with sizes,
identify SOLUTION/SOLUTIONBLOCK/MESH/XMESH segments (BinaryType naming:
<type-lowercase><N>.mphbin), detect raw-double payloads heuristically.
Usage: python mph_solution_probe.py <solved.mph>"""
import struct
import sys
import zipfile


def main():
    z = zipfile.ZipFile(sys.argv[1])
    total = 0
    segs = {}
    for i in z.infolist():
        total += i.compress_size
        n = i.filename
        kind = "other"
        for t in ("solutionblock", "solutionstatic", "solution", "xmeshpart",
                  "xmesh", "mesh", "geometry", "geommanager", "postdata",
                  "interpolationmatrix", "functiondata", "viewfactordata",
                  "meshimportassoc", "cghandler", "dnndata"):
            if n.lower().startswith(t):
                kind = t
                break
        segs.setdefault(kind, []).append((n, i.file_size, i.compress_size))
    print(f"total {len(z.namelist())} entries, compressed {total//1048576} MB")
    for k, v in sorted(segs.items(), key=lambda x: -sum(s[2] for s in x[1])):
        print(f"  {k:22s} n={len(v):3d} raw={sum(s[1] for s in v)//1048576:5d}MB "
              f"zip={sum(s[2] for s in v)//1048576:5d}MB  e.g. {v[0][0]}")
    # heuristic: peek biggest solution segment for double payload
    sol = segs.get("solution") or segs.get("solutionblock") or []
    if sol:
        biggest = max(sol, key=lambda s: s[1])
        d = z.read(biggest[0])[:4000]
        print(f"\npeek {biggest[0]} ({biggest[1]} bytes):")
        print("  head:", d[:96])
        nd = sum(1 for i in range(0, len(d) - 8, 8)
                 if 1e-12 < abs(struct.unpack("<d", d[i:i+8])[0]) < 1e12)
        print(f"  plausible little-endian doubles in first 4KB: {nd}/{len(d)//8}")


if __name__ == "__main__":
    main()
