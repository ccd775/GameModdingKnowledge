"""Name the numeric joints of an AnvilToolkit Syndicate GLB export.

  python glb_names.py <in.glb> <out.glb> [--dict <names.json>] [--ref <named.glb> ...]

Syndicate skeletons carry no bone names: export-glb writes each bone as its numeric ID, which is the CRC32 of the
bone name (zlib.crc32, case-sensitive; checked on Reference, Hips, Spine..Spine2, LeftUpLeg, LeftFootThumb1, ...).
Every numeric node whose ID matches the CRC32 of a known name is renamed; import-glb hashes names back to the same
IDs, so the renaming is round-trip safe. Known names = the names in the --ref GLBs (AC Unity exports are named),
the --dict JSON ({crc: name}, written back with the new finds) and a generated list of humanoid bone names.
The true bone ID is the node's extras["Name"]: the toolkit names some bones by an alias whose CRC32 is NOT the ID
(Evie's face root "JAW" = Fx_Jaw 4253370951, "EYE_LEFT" = Fx_Eye_Left 485040451); such nodes are renamed to a known
name with the right CRC32, else to the decimal ID.
"""
import json
import os
import struct
import sys
import zlib

SIDES = ("Left", "Right")


def candidates():
    out = ["Reference", "Skeletal Mesh", "Hips", "Pelvis", "Root", "Spine", "Spine1", "Spine2", "Spine3", "Neck",
           "Neck1", "Head", "HeadEnd", "Head_End", "Jaw", "Fx_Jaw", "Head_Props", "Fx_Neck", "Fx_LowerJaw", "Fx_Eye_Left", "Fx_Eye_Right"]
    for s in SIDES:
        out += [f"{s}{b}" for b in ("UpLeg", "Leg", "Foot", "ToeBase", "Clavicle", "Shoulder", "Arm", "ForeArm", "Hand",
                                    "UpLegRoll", "LegRoll", "ArmRoll", "ForeArmRoll", "UpLegTwist", "ForeArmTwist",
                                    "ArmTwist", "Knee", "Elbow", "Wrist", "Breast", "Buttock", "Armpit", "HandProp",
                                    "HandAttach", "Weapon", "Scapula", "Calf")]
        out += [f"{s}FootThumb{i}" for i in range(1, 5)]
        for f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
            out += [f"{s}Hand{f}{i}" for i in range(0, 5)]
    return out


def load(path):
    b = open(path, "rb").read()
    clen = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + clen]), b[20 + clen:]


def save(path, doc, rest):
    j = json.dumps(doc, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    total = 12 + 8 + len(j) + len(rest)
    open(path, "wb").write(struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(j), 0x4E4F534A) + j + rest)


def main():
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        sys.exit(0)
    a = sys.argv
    src, dst = a[1], a[2]
    dpath = a[a.index("--dict") + 1] if "--dict" in a else None
    names = {}
    if dpath and os.path.exists(dpath):
        names.update({int(k): v for k, v in json.load(open(dpath, encoding="utf-8")).items()})
    for n in candidates():
        names.setdefault(zlib.crc32(n.encode()), n)
    for i, v in enumerate(a):
        if v == "--ref":
            for n in load(a[i + 1])[0].get("nodes", []):
                nm = n.get("name", "")
                if nm and not nm.isdigit():
                    names.setdefault(zlib.crc32(nm.encode()), nm)
    doc, rest = load(src)
    joints = {j for s in doc.get("skins", []) for j in s["joints"]}
    hit = miss = alias = 0
    for i, n in enumerate(doc.get("nodes", [])):
        nm = n.get("name", "")
        true = (n.get("extras") or {}).get("Name", "")
        if true.isdigit() and not nm.isdigit() and zlib.crc32(nm.encode()) != int(true):
            nm = n["name"] = true  # toolkit alias: fall back to the ID, named below if a matching name is known
            alias += 1
        if nm.isdigit():
            if int(nm) in names:
                n["name"] = names[int(nm)]
                hit += 1
            elif i in joints:
                miss += 1
    save(dst, doc, rest)
    if dpath:
        json.dump({str(k): v for k, v in sorted(names.items())}, open(dpath, "w", encoding="utf-8"), indent=0)
    print(f"named {hit} nodes ({alias} toolkit aliases replaced), {miss} numeric joints left -> {dst}")


if __name__ == "__main__":
    main()
