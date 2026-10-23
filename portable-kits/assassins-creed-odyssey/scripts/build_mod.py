"""Build the Karin_Original -> Kassandra payload (model + materials; milestone 2: + physics skeleton).

  python build_mod.py <mesh_dir> <out_dir> [--tex-size 2048] [--gloss 70] [--skeleton <aco_phys_skel.py xml>]

<mesh_dir>: karin_lod0.Mesh / karin_lod1.Mesh (import-glb of export_karin_lods --profile aco_tex1, rotated -90).
Writes <out_dir>/payload/<IDHEX>_<name>.data; aco_install.py puts each into every forge holding that ID.

Data files (vanilla sources unpacked under <ACO_WORK>/x1, x2, x5; layout in the kit README). Override order in the main
world (test 2026-10-19):
DataPC_patch_01 > dlc_<n> forges (dlc_43, dlc_58 incl. DataPC_ACD_Connection repackage these files) > SharedGroup_00.
  00000104280E4653 standalone LOD0 (patch_01 wins): Karin LOD0 + 4 ACD_Tex1 Materials, TextureSets, diffuse maps
        (Face/Body/Hair/Costume) + shared flat normal (B metal 0, A gloss) + Mask0. Same data file as the mesh: the DLC
        copies of the BodyKassandra container are stubs, so materials inside the SG container were never loaded (v1).
  0000018482B71630 standalone LOD1: Karin LOD1 (its materials resolve to the objects in the LOD0 data file)
  00000104280E464B BodyKassandra container: LODSelector LOD2-4 -> Karin LOD1 (the shared female body otherwise),
        Karin copies of the inner LOD0/LOD1 meshes
  00000103E739C903 VisualMaster: Outfit column (2) dropped -> no gear visuals whatever is equipped
  0000016424DFAD4B Head table: face/eyes/shadow/sweat/lashes/brows/teeth (1-7), eyeball material (8) and the
        legendary-outfit skin overrides (14) dropped; head skeleton, hair skeleton/offsets, tags kept
  00000146D5F5EB4C Hair table: hair meshes (9 normal, 10 hood, 13 helmet GraphicVisualProperty cells) and the row's
        DynamicResources dropped (v2 still showed Kassandra's braid); hair skeleton + braid offsets kept.
        Not installed into the older SharedGroup_00 revision (payload skip.tsv).
  00000194D13C465D ACD_CHF_PLA_Hair_NEW skeleton (Hair table col 3, Kassandra-only; --skeleton): Karin's KP bones +
        Reflex3 Physics records (aco_phys_skel.py); the mesh dir must then hold the matching KP-skinned LODs.
No .prefetch edit: data-file root references (LOD meshes, the ACD_Tex1 template) load on demand.
Machine paths (portable kit): ACO_WORK, ACO_DOTNET, ACO_HARNESS, ACO_TEXCONV, ACO_SRC_TEX; all are checked before
anything is written.
"""
import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# machine paths (portable kit): environment variables, checked in main() before anything is written
ENV = ("ACO_WORK", "ACO_DOTNET", "ACO_HARNESS", "ACO_TEXCONV", "ACO_SRC_TEX")
WORK = os.environ.get("ACO_WORK", "")         # project work folder with the unpacked vanilla data files (x1, x2, x5)
DOTNET = os.environ.get("ACO_DOTNET", "")     # dotnet.exe of the .NET 9 runtime
HARNESS = os.environ.get("ACO_HARNESS", "")   # AcoHarness.dll (acoharness/build.ps1)
TEXCONV = os.environ.get("ACO_TEXCONV", "")   # DirectXTex texconv.exe
SRC_TEX = os.environ.get("ACO_SRC_TEX", "")   # Karin_Face.png / Karin_Body.png / Karin_Hair.png / Karin_Costume.png
sys.path.insert(0, HERE)
import bt_tool  # noqa: E402

X1, X2, X5 = os.path.join(WORK, "x1"), os.path.join(WORK, "x2"), os.path.join(WORK, "x5")
CONTAINER = ("00000104280E464B", "ACD_CHF_PLA_B01_A01_BodyKassandra", os.path.join(X1, "sg", "unpacked", "6365_-_ACD_CHF_PLA_B01_A01_BodyKassandra"),
             os.path.join(X1, "SharedGroup_00", "6365_-_ACD_CHF_PLA_B01_A01_BodyKassandra.data"))
LOD0 = ("00000104280E4653", "ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0", os.path.join(X1, "p1", "unpacked", "19901_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0"),
        os.path.join(X1, "patch_01", "19901_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0.data"))
LOD1 = ("0000018482B71630", "ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1", os.path.join(X1, "p1", "unpacked", "19900_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1"),
        os.path.join(X1, "patch_01", "19900_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.data"))
VMASTER = ("00000103E739C903", "ACD_CHF_PLA_Kassandra_VisualMaster", os.path.join(X1, "sg", "unpacked", "6518_-_ACD_CHF_PLA_Kassandra_VisualMaster"),
           os.path.join(X1, "SharedGroup_00", "6518_-_ACD_CHF_PLA_Kassandra_VisualMaster.data"))
HEAD = ("0000016424DFAD4B", "ACD_CHF_PLA_Kassandra_Head", os.path.join(X1, "p1", "unpacked", "19505_-_ACD_CHF_PLA_Kassandra_Head"),
        os.path.join(X1, "patch_01", "19505_-_ACD_CHF_PLA_Kassandra_Head.data"))
HAIR = ("00000146D5F5EB4C", "ACD_CHF_PLA_Kassandra_Hair", os.path.join(X1, "p1", "unpacked", "19506_-_ACD_CHF_PLA_Kassandra_Hair"),
        os.path.join(X1, "patch_01", "19506_-_ACD_CHF_PLA_Kassandra_Hair.data"))
HAIRSKEL = ("00000194D13C465D", "ACD_CHF_PLA_Hair_NEW", os.path.join(X2, "p1", "unpacked", "19511_-_ACD_CHF_PLA_Hair_NEW"),
            os.path.join(X2, "patch_01", "19511_-_ACD_CHF_PLA_Hair_NEW.data"))
LOD1_ID = 0x18482B71630
LOD1_PATH = r"DataPC_patch_01\ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1\ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.Mesh"
SKIN_DIR = os.path.join(X2, "sg", "unpacked", "6369_-_ACD_CHF_PLA_Kassandra_Head")
TPL_DIFF = os.path.join(SKIN_DIR, "3_-_ACD_CHF_PLA_Kassandra_Head_DiffuseMap.TextureMap")     # inline mips, sRGB
TPL_NORM = os.path.join(SKIN_DIR, "1_-_ACD_CHR_P_Kassandra_Body_NormalMap.TextureMap")      # inline mips, linear
BOW = os.path.join(X5, "sg", "xml", "9245_-_ACD_CHW_PLA_01_BowAlexios")

BASE = 0x2A0CA5A0000
PARTS = [("Face", "Karin_Face.png"), ("Body", "Karin_Body.png"), ("Hair", "Karin_Hair.png"), ("Costume", "Karin_Costume.png")]
MAT = {p: BASE + 1 + i for i, (p, _) in enumerate(PARTS)}       # matches export_karin_lods.py --profile aco_tex1
SET = {p: BASE + 0x11 + i for i, (p, _) in enumerate(PARTS)}
DIFF = {p: BASE + 0x21 + i for i, (p, _) in enumerate(PARTS)}
NORM, MASK0 = BASE + 0x31, BASE + 0x32
# bow material/texture set (ACD_Tex1, opaque) used as XML templates
BOW_MAT, BOW_SET, BOW_DIFF, BOW_NORM, BOW_MASK = "535855619145", "535855618945", "535855618950", "535855618954", "535855618958"


def run(*args):
    r = subprocess.run([DOTNET, HARNESS, *args], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or "Exception" in out:
        raise SystemExit(f"harness {args[0]} failed:\n{out[-3000:]}")
    return out


def texconv(png, out_dir, fmt, size=None):
    cmd = [TEXCONV, "-nologo", "-y", "-f", fmt, "-m", "0", "-bc", "q", "-o", out_dir]
    if size:
        cmd += ["-w", str(size), "-h", str(size)]
    if fmt.endswith("SRGB"):
        cmd += ["-srgb"]
    subprocess.run(cmd + [png], check=True, stdout=subprocess.DEVNULL)
    return os.path.join(out_dir, os.path.splitext(os.path.basename(png))[0] + ".dds")


def subst(x, pairs):
    for a, b in pairs:
        x = re.sub(r'(?<=[">])%s(?=[<"])' % a, str(b), x)
    return x


def pack(entry, folder, out_payload):
    oid, name, _, orig = entry
    for f in os.listdir(folder):  # compile-xml leaves <file>.bak next to what it overwrote
        if f.endswith(".bak"):
            os.remove(os.path.join(folder, f))
    out = os.path.join(out_payload, f"{oid}_{name}.data")
    print(run("pack-data", folder, orig, out).splitlines()[-1])
    return out


def compile_fixed(xml, out, vanilla_bin=None, vanilla_xml=None):
    """compile-xml, then restore the null-Reference padding bytes the Odyssey writer zeroes (see bt_tool.py)."""
    run("compile-xml", xml, out)
    if vanilla_bin is None:
        return
    tmp = out + ".vanilla"
    run("compile-xml", vanilla_xml, tmp)
    a, b, c = open(vanilla_bin, "rb").read(), open(tmp, "rb").read(), bytearray(open(out, "rb").read())
    os.remove(tmp)
    assert len(a) == len(b), "vanilla recompile changed size"
    diffs = [i for i in range(len(a)) if a[i] != b[i]]
    assert all(a[i] == 1 and b[i] == 0 and b[i - 1] == 3 for i in diffs), "unexpected vanilla recompile difference"
    # map each zeroed byte of the vanilla recompile into the edited compile through the unchanged blocks; a byte inside
    # a dropped cell has no counterpart (its reference is gone)
    blocks = difflib.SequenceMatcher(None, b, bytes(c), autojunk=False).get_matching_blocks()
    restored = lost = 0
    for i in diffs:
        hit = next((k + i - j for j, k, n in blocks if j < i < j + n), None)  # i - 1 (the pointer type) matched too
        if hit is None:
            lost += 1
            continue
        assert c[hit] == 0 and c[hit - 1] == 3, f"null-ref padding mapped to an unexpected byte at {hit}"
        c[hit] = 1
        restored += 1
    open(out, "wb").write(c)
    print(f"  {os.path.basename(out)}: restored {restored} null-ref padding bytes ({lost} inside dropped cells)")


def add_materials(folder, n, tmp, tex_size, gloss):
    """4 ACD_Tex1 Materials + TextureSets + diffuse maps, shared flat normal (B metal 0, A gloss) and Mask0 (B occlusion 1),
    written as objects n, n+1, ... of <folder>; returns the next free index"""
    bow_mat = open(os.path.join(BOW, "0_-_ACD_CHW_PLA_01_BowAlexios.Material.xml"), encoding="utf-8-sig").read()
    bow_set = open(os.path.join(BOW, "1_-_ACD_CHW_PLA_01_BowAlexios_Set.TextureSet.xml"), encoding="utf-8-sig").read()
    lpath = r"DataPC_patch_01\ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0" + "\\"
    for part, png in PARTS:
        nm = f"Karin_{part}"
        mx = subst(bow_mat, [(BOW_MAT, MAT[part]), (BOW_SET, SET[part]), (BOW_DIFF, DIFF[part]), (BOW_NORM, NORM), (BOW_MASK, MASK0)])
        mx = mx.replace('<Bool Name="TwoSided">False</Bool>', '<Bool Name="TwoSided">True</Bool>')
        mx = re.sub(r'Path="DataPC_SharedGroup_00\\ACD_CHW_PLA_01_BowAlexios\\ACD_CHW_PLA_01_BowAlexios_Set\.TextureSet"', lambda _: f'Path="{lpath}{nm}_Set.TextureSet"', mx)
        sx = subst(bow_set, [(BOW_SET, SET[part]), (BOW_DIFF, DIFF[part]), (BOW_NORM, NORM), (BOW_MASK, MASK0)])
        for f, x in ((f"{nm}.Material", mx), (f"{nm}_Set.TextureSet", sx)):
            xp = os.path.join(tmp, f + ".xml")
            open(xp, "w", encoding="utf-8").write(bt_tool.fix_null_refs(x))
            run("compile-xml", xp, os.path.join(folder, f"{n}_-_{f}"))
            n += 1
        dds = texconv(os.path.join(SRC_TEX, png), tmp, "BC7_UNORM_SRGB", tex_size)
        print(" ", run("tex-import", TPL_DIFF, dds, os.path.join(folder, f"{n}_-_{nm}_DiffuseMap.TextureMap"), "--id", f"{DIFF[part]:X}").splitlines()[-1])
        n += 1
    flat = os.path.join(tmp, "karin_flat_normal.png")
    Image.new("RGBA", (64, 64), (128, 128, 0, gloss)).save(flat)
    print(" ", run("tex-import", TPL_NORM, texconv(flat, tmp, "BC7_UNORM"), os.path.join(folder, f"{n}_-_Karin_FlatNormal_NormalMap.TextureMap"), "--id", f"{NORM:X}").splitlines()[-1])
    n += 1
    m0 = os.path.join(tmp, "karin_mask0.png")
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(m0)
    # Odyssey MapMask0 = 12 (AnvilToolkit's TextureMapType has no name for it)
    print(" ", run("tex-import", TPL_NORM, texconv(m0, tmp, "BC7_UNORM"), os.path.join(folder, f"{n}_-_Karin_Mask0Map.TextureMap"), "--id", f"{MASK0:X}", "--maptype", "12").splitlines()[-1])
    return n + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--tex-size", type=int, default=2048)
    ap.add_argument("--gloss", type=int, default=70)
    ap.add_argument("--skeleton", help="Hair_NEW skeleton XML written by aco_phys_skel.py")
    a = ap.parse_args()
    missing = [n for n in ENV if not os.environ.get(n)]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see the kit README)")
    mesh_dir, out = a.mesh_dir, a.out_dir
    tex_size, gloss = a.tex_size, a.gloss
    skel_xml = os.path.abspath(a.skeleton) if a.skeleton else None
    if os.path.exists(out):
        shutil.rmtree(out)
    payload, tmp = os.path.join(out, "payload"), os.path.join(out, "tmp")
    os.makedirs(payload)
    os.makedirs(tmp)

    # --- container: LODSelector (LOD2-4 -> Karin LOD1) + Karin copies of the inner LOD0/LOD1 meshes --------------
    cdir = os.path.join(out, "container")
    shutil.copytree(CONTAINER[2], cdir)
    lodsel = os.path.join(cdir, "0_-_ACD_CHF_PLA_B01_A01_BodyKassandra.LODSelector")
    lodsel_xml = os.path.join(X1, "sg", "xml", os.path.basename(CONTAINER[2]), os.path.basename(lodsel) + ".xml")
    edited = os.path.join(tmp, "lodsel.xml")
    bt_tool.lodsel(lodsel_xml, edited, {2: (LOD1_ID, LOD1_PATH), 3: (LOD1_ID, LOD1_PATH), 4: (LOD1_ID, LOD1_PATH)})
    run("compile-xml", edited, lodsel)
    shutil.copy(os.path.join(mesh_dir, "karin_lod0.Mesh"), os.path.join(cdir, "1_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0.Mesh"))
    shutil.copy(os.path.join(mesh_dir, "karin_lod1.Mesh"), os.path.join(cdir, "2_-_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.Mesh"))
    pack(CONTAINER, cdir, payload)

    # --- standalone LODs (patch_01 wins over every other copy); LOD0 also carries the materials ----------------
    for entry, mesh in ((LOD0, "karin_lod0.Mesh"), (LOD1, "karin_lod1.Mesh")):
        d = os.path.join(out, entry[1])
        shutil.copytree(entry[2], d)
        target = [f for f in os.listdir(d) if f.endswith(".Mesh")]
        assert len(target) == 1 and target[0].startswith("0_-_")
        shutil.copy(os.path.join(mesh_dir, mesh), os.path.join(d, target[0]))
        if entry is LOD0:
            add_materials(d, 1, tmp, tex_size, gloss)
        pack(entry, d, payload)

    # --- tables -------------------------------------------------------------------------------------------
    for entry, drops, dynres in ((VMASTER, {"2"}, False), (HEAD, {"1", "2", "3", "4", "5", "6", "7", "8", "14"}, False),
                                 (HAIR, {"9", "10", "13"}, True)):
        d = os.path.join(out, entry[1])
        shutil.copytree(entry[2], d)
        tname = [f for f in os.listdir(d) if f.endswith(".BuildTable")][0]
        vxml = os.path.join(os.path.dirname(entry[2]).replace(os.sep + "unpacked", os.sep + "xml"), os.path.basename(entry[2]), tname + ".xml")
        exml = os.path.join(tmp, tname + ".edited.xml")
        bt_tool.edit(vxml, exml, drops, {}, dynres)
        compile_fixed(exml, os.path.join(d, tname), os.path.join(entry[2], tname), vxml)
        pack(entry, d, payload)
    # --- physics skeleton (replaces Kassandra's hair skeleton in every copy) -------------------------------------
    if skel_xml:
        d = os.path.join(out, HAIRSKEL[1])
        shutil.copytree(HAIRSKEL[2], d)
        sname = [f for f in os.listdir(d) if f.endswith(".Skeleton")]
        assert len(sname) == 1
        vxml = os.path.join(X2, "p1", "xml", os.path.basename(HAIRSKEL[2]), sname[0] + ".xml")
        compile_fixed(skel_xml, os.path.join(d, sname[0]), os.path.join(HAIRSKEL[2], sname[0]), vxml)
        pack(HAIRSKEL, d, payload)
    # the SG Hair table is an older revision (it also carries the old ACD_CHF_PLA_Hair skeleton); patch_01 wins over it
    open(os.path.join(payload, "skip.tsv"), "w").write(f"{HAIR[0]}\tDataPC_SharedGroup_00.forge\n")
    shutil.rmtree(tmp)
    print("BUILD_OK", out)


if __name__ == "__main__":
    main()
