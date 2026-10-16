"""Patch Deacon's BendSkeletalMeshLook assets for the Karin build.

Every look's master part (the head part, the master pose component that runs the AnimBP) gets the Karin mesh and
Karin's material instances by slot index (the look overrides the mesh's materials per index); every other part's
mesh becomes null. Only int32 package indices change in the export data plus appended imports, so the property
layout stays byte-compatible with the game's version-500 serializer.

usage: python patch_looks.py <looks_src_root> <out_root> <config.json>
config: {"mesh": "/Game/Characters/Deacon/parts/head/deacon_head_standard",
         "materials": ["/Game/Karin/Materials/MI_Karin_Face", ...]}   # slot order of the Karin mesh
"""
import argparse, glob, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upkg

def patch(path, cfg):
    p = upkg.Package(open(path, "rb").read())
    d = bytearray(p.export_data(0))
    props = {x.name: x for x in upkg.parse_props(p, bytes(d))}
    master = struct.unpack_from("<i", d, props["MasterPartIndex"].vstart)[0] if "MasterPartIndex" in props else 0
    mesh_idx = p.ensure_object_import(cfg["mesh"], "/Script/Engine", "SkeletalMesh")
    mats = [p.ensure_object_import(m, "/Script/Engine", "MaterialInstanceConstant") for m in cfg["materials"]]
    report = {"master": master, "parts": []}
    for i, part in enumerate(props["PartsNEW"].children):
        P = {x.name: x for x in part}
        old = struct.unpack_from("<i", d, P["Mesh"].vstart)[0]
        if i == master:
            struct.pack_into("<i", d, P["Mesh"].vstart, mesh_idx)
            slots = P["Materials_Runtime_UsingMaterialIndex_NEW"].children
            if len(slots) < len(mats):
                raise SystemExit("%s: master part has %d material slots, need %d" % (path, len(slots), len(mats)))
            for k, slot in enumerate(slots):
                S = {x.name: x for x in slot}
                struct.pack_into("<i", d, S["Material"].vstart, mats[k] if k < len(mats) else 0)
            report["parts"].append({"i": i, "old": p.ref(old), "new": cfg["mesh"], "slots": len(slots)})
        else:
            struct.pack_into("<i", d, P["Mesh"].vstart, 0)
            report["parts"].append({"i": i, "old": p.ref(old), "new": None})
    return p.write([bytes(d)]), report

def main(src, out, cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    reports = {}
    for f in sorted(glob.glob(os.path.join(src, "**", "*.uasset"), recursive=True)):
        rel = os.path.relpath(f, src)
        data, rep = patch(f, cfg)
        # verify: reparse and check the master part
        q = upkg.Package(data)
        assert len(q.exports) == 1 and upkg.parse_props(q, q.export_data(0))
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)
        reports[rel.replace(os.sep, "/")] = rep
    json.dump(reports, open(os.path.join(out, "patch_looks_report.json"), "w"), indent=1)
    print("patched", len(reports), "looks")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="raw looks root"); ap.add_argument("out"); ap.add_argument("config")
    args = ap.parse_args()
    main(args.src, args.out, args.config)
