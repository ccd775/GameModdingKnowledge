"""Build the Karin_Original -> Arno payload for acu_install.py (milestone 1: model + materials).

  python build_mod.py <mesh_dir> <out_dir> [--tex-size 2048] [--spec 40] [--gloss 90,90,120,70] [--phys <Skeleton.xml>]
                      [--game <game dir>]

<mesh_dir>: karin_lod0..3.Mesh (import-glb of export_karin_lods.py --profile acu_weapon, rotated -90, vanilla head IDs).
Writes <out_dir>/payload/ (see acu_install.py for the layout).

Data files (Steam build 21970519):
  Arno's BuildTables exist as COPIES WITH THE SAME OBJECT IDs in several data files of every world forge: CN_P_Arno
  (the player EntityBuilder, 0x70CF6709B), DataAI_UIDataRoot (0x1842175574, UI / customization data; its copies are
  the ones that reach the player - v1 edited only CN_P_Arno and nothing changed) and the legacy-avatar files (Heads).
  Every data file that holds one of TABLE_DROPS (list: <ACU_CACHE>/arno_tables.tsv from `harness scan-objs`) is rebuilt
  from its own vanilla copy (payload/forge/<forge>/<IDHEX>_<name>.data):
        - Body_All: column 8 (Body_Custom) dropped; the gear tables themselves (Body_Custom, Hoods, UpperBodies, Belts,
          Pants, ThrowBlade, Hood_Position with Arno's hair) lose every visual column -> no gear whatever is equipped
        - Heads / Arno_Head: Arno's eye/teeth (16), wet (20), eyelash (21), beard (31) and scar (33) meshes dropped;
          head rig (14) and the head LODSelector (15) kept
  000000313DB95D16 CN_U_FR_Arno_Head (head LODSelector container, 15 copies): LOD0..3 meshes -> Karin LOD0..3 (same IDs),
        + 4 CN_Weapon_NoAlphaTest Materials, TextureSets, diffuse maps (Face/Body/Hair/Costume), flat normals
        (A = gloss) and one shared specular map, all in the same data file. One payload for every copy.
compile-xml of vanilla Unity tables is byte-identical (checked per copy, the build stops otherwise).

Machine paths (portable kit): ACU_DOTNET, ACU_HARNESS, ACU_TEXCONV, ACU_SRC_TEX, ACU_TEMPLATES and ACU_CACHE are checked
before anything is written; ACU_SCRATCH (default <TEMP>/acu_work); game folder --game, ACU_GAME_DIR or the Steam libraries.
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# machine paths (portable kit): environment variables, checked in main() before anything is written
ENV = ("ACU_DOTNET", "ACU_HARNESS", "ACU_TEXCONV", "ACU_SRC_TEX", "ACU_TEMPLATES", "ACU_CACHE")
DOTNET = os.environ.get("ACU_DOTNET", "")        # dotnet.exe of the .NET 9 runtime
HARNESS = os.environ.get("ACU_HARNESS", "")      # AcuHarness.dll (acuharness/build.ps1)
TEXCONV = os.environ.get("ACU_TEXCONV", "")      # DirectXTex texconv.exe
SRC_TEX = os.environ.get("ACU_SRC_TEX", "")      # Karin_Face.png / Karin_Body.png / Karin_Hair.png / Karin_Costume.png
TEMPLATES = os.environ.get("ACU_TEMPLATES", "")  # material / texture-set XML and inline-mip texture templates (kit README)
CACHE = os.environ.get("ACU_CACHE", "")          # index.tsv (acu_forge.py index) and arno_tables.tsv (objs_to_tsv.py)
# heavy, regenerable intermediates (vanilla copies, job temp) stay OFF the synced project folder: every unpacked file
# there is picked up by the cloud-sync client (2026-10-24: ~30 s per data file). ACU_SCRATCH = a local directory.
SCRATCH = os.environ.get("ACU_SCRATCH") or os.path.join(tempfile.gettempdir(), "acu_work")
VANILLA = os.path.join(SCRATCH, "vanilla")
sys.path.insert(0, HERE)
import acu_forge  # noqa: E402
import acu_install  # noqa: E402
import bt_tool  # noqa: E402

HEAD = 0x313DB95D16
HEAD_SRC = ("DataPC_ACU_Paris.forge", "CN_U_FR_Arno_Head")
LODS = ["1_-_CN_U_FR_Arno_Head_LOD0.Mesh", "2_-_CN_U_FR_Arno_Head_LOD1.Mesh",
        "3_-_CN_U_FR_Arno_Head_LOD2.Mesh", "4_-_CN_U_FR_Arno_Head_LOD3.Mesh"]
TABLE_DROPS = {  # object ID -> BuildTable columns dropped from every row
    0x145368098E: {"8"},                                       # CN_P_ArnoAvatar_Body_All: Body_Custom
    0x2DFA9960D6: {"1", "2", "3", "4", "5", "6", "8"},         # CN_P_ArnoAvatar_Body_Custom: every gear table
    0x145368099F: {"2", "3", "4", "10", "11", "12", "14", "16"},  # Hoods (hood up/down meshes, cloth, skeletons)
    0x14536809A0: {"1", "2", "4", "5", "6", "7", "13", "14"},  # UpperBodies
    0x14536809A1: {"2", "4", "6", "7", "8", "10"},             # Belts
    0x14536809A2: {"1", "3"},                                  # Pants (+ boots skeletons)
    0x14536809A3: {"1", "3", "5", "6"},                        # ThrowBlade (bracer / iconic weapon visuals)
    0x1EB36B1C7C: {"5", "6", "7", "9", "10", "11"},            # Hood_Position: hood occlusion, Arno's hair + skeleton
    0x26A4C11760: {"16", "20", "21", "33"},                    # CN_P_ArnoAvatar_Heads: eyes/teeth, wet, lashes, scar
    0x10ED459755: {"16", "20", "21", "31", "33"},              # Arno_Head (own data file): + prisoner beard
}
# legacy outfits (Altair, Ezio, Connor, ..., ThomasCarneillon = PrologueAssassin): their own Body / Visuals / Softbody /
# gear tables only exist in their own data files, which are in the list anyway (they embed Heads / Hood_Position /
# Arno_Head copies): every GraphicObject / SoftBody / TextureSet column of those tables is dropped
LEGACY_TABLE = re.compile(r"LegacyAvatar|PrologueAssassin_(Body|Softbody|Skeleton)")
# stage 2 (--phys <Skeleton.xml> from acu_phys_skel.py): Karin's physics add-on skeleton is embedded as a new object in
# every data file holding a player add-on skeleton table (CN_P_ArnoAvatar_Skeleton = Body_All col 7, and each legacy
# outfit's *_Skeleton table) and takes the cell of a cloth add-on whose mesh is dropped anyway (first match below)
SKEL_TABLE = 0x1453680995
PHYS_HOST = [102605590575, 122171377058, 33489545264, 35532555327]  # Dress_Simple_HV_Col, Hood_3, Edward_Kenway_Hood, Dress_DoubleSpine
SKEL_CELL = re.compile(r'<DynamicProperty Name="(\d+)"[^>]*ObjectType="Skeleton"[^>]*>\s*<Reference [^>]*>(\d+)</Reference>')
COLUMN = re.compile(r'<Unsigned32 Name="ColumnID">(\d+)</Unsigned32>.*?<DynamicProperty Name="Type"[^>]*ObjectType="(\w+)"', re.S)
VISUAL_TYPES = {"GraphicObject", "SoftBody", "TextureSet"}
TABLES_TSV = os.path.join(CACHE, "arno_tables.tsv")   # forge, data file IDHEX, name, object IDHEX (tab-separated)
OBJ_ID = re.compile(r'<Object ID="(\d+)"')

TPL_MAT = os.path.join(TEMPLATES, "10001_-_1Handed_Sp2.Material.xml")            # CN_Weapon_NoAlphaTest (DataPC GBS)
TPL_SET = os.path.join(TEMPLATES, "12392_-_CN_W_1Handed_Sp2_Set.TextureSet.xml")
T_MAT, T_SET, T_SRC, T_DIFF, T_NORM, T_SPEC = ("150011561307", "150011560883", "150011560882",
                                               "150011561152", "150011561156", "150011561160")
TPL_DIFF = os.path.join(TEMPLATES, "0_-_CN_U_FR_Arno_Head_LOD0_DiffuseMap.TextureMap")   # inline mips, sRGB
TPL_NORM = os.path.join(TEMPLATES, "0_-_CN_U_FR_Arno_Head_LOD0_NormalMap.TextureMap")    # inline mips, linear
TPL_SPEC = os.path.join(TEMPLATES, "0_-_CN_W_ULC_Arno_Sword1_0_SpecularMap.TextureMap")  # MapSpecular, sRGB

BASE = 0x4B41520000  # just above the highest vanilla data-file ID (0x3F57BB287B)
PARTS = [("Face", "Karin_Face.png"), ("Body", "Karin_Body.png"), ("Hair", "Karin_Hair.png"), ("Costume", "Karin_Costume.png")]
MAT = {p: BASE + 0x01 + i for i, (p, _) in enumerate(PARTS)}   # = export_karin_lods.py --profile acu_weapon
SET = {p: BASE + 0x11 + i for i, (p, _) in enumerate(PARTS)}
DIFF = {p: BASE + 0x21 + i for i, (p, _) in enumerate(PARTS)}
NORM = {p: BASE + 0x31 + i for i, (p, _) in enumerate(PARTS)}
SRC = {p: BASE + 0x51 + i for i, (p, _) in enumerate(PARTS)}    # TextureSet "Source" handles (TextureFile)
SPEC = BASE + 0x41
PHYS_ID = BASE + 0xF00   # Karin_Phys.Skeleton (its bones / modifiers: acu_phys_skel.PTR_BASE = BASE + 0x1000..)
PHYS_NAME = "Karin_Phys.Skeleton"
# skirt collision objects written next to the skeleton XML by acu_phys_skel.py (IDs PHYS_ID + 1 / + 2), embedded with it
PHYS_EXTRA = [("BallJointCommonData", PHYS_ID + 1), ("LiteRagdoll", PHYS_ID + 2)]


def run(*args, check=True):
    r = subprocess.run([DOTNET, HARNESS, *args], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if check and (r.returncode != 0 or "Exception" in out):
        raise SystemExit(f"harness {args[0]} failed:\n{out[-3000:]}")
    return out


def batch(cmds, tmp):
    """run several harness commands in one process (AcuHarness batch: absolute paths, one tab-separated line each)"""
    lst = os.path.join(tmp, "batch.tsv")
    open(lst, "w", encoding="utf-8").write("".join("\t".join(c) + "\n" for c in cmds))
    out = run("batch", lst, check=False)
    bad = [l for l in out.splitlines() if l.startswith("BATCH ") and not l.endswith(" rc=0")]
    if bad or "Exception" in out or out.count("BATCH ") != len(cmds):
        raise SystemExit(f"harness batch failed ({bad[:3]}):\n{out[-3000:]}")
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


def fkey(fg):
    return fg.replace(os.sep, "__").replace("/", "__")


def vanilla(fg, oid, tables_only=False):
    """extract + unpack one copy into work/vanilla/<forge>/<IDHEX>/ (cached) and export schema XML (every object, or
    only the BuildTables: a full export of a big legacy-outfit file takes ~40 s); returns (data, unpacked dir, xml dir)"""
    base = os.path.join(VANILLA, fkey(fg), f"{oid:016X}")
    datas = [f for f in os.listdir(base) if f.endswith(".data")] if os.path.isdir(base) else []
    if not datas:
        p = acu_forge.extract(os.path.join(acu_install.GAME, fg), base, [oid])
        assert len(p) == 1, (fg, oid, p)
        datas = [os.path.basename(p[0])]
    data = os.path.join(base, datas[0])
    stem = os.path.splitext(datas[0])[0]
    un, xml = os.path.join(base, "unpacked", stem), os.path.join(base, "xml", stem)
    ok = os.path.join(base, ".xml_ok")
    if not os.path.exists(ok):
        if tables_only:
            if not os.path.isdir(un):
                run("unpack-data", data, un)
            run("export-xml-dir", un, xml, "*.BuildTable")
        else:
            run("unpack-export", base, data, check=False)  # some object types have no XML exporter; tables do
        open(ok, "w").write("tables" if tables_only else "all")
    return data, un, xml


def pack(folder, orig, out):
    for f in os.listdir(folder):  # compile-xml leaves <file>.bak next to what it overwrote
        if f.endswith(".bak"):
            os.remove(os.path.join(folder, f))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(" ", run("pack-data", folder, orig, out).splitlines()[-1], "->", os.path.relpath(out, os.path.dirname(os.path.dirname(out))))


def table_hits():
    """{(forge, data file id, name): {object ids}} from <ACU_CACHE>/arno_tables.tsv"""
    hits = {}
    for line in open(TABLES_TSV, encoding="utf-8"):
        fg, did, name, oid = line.rstrip("\n").split("\t")
        hits.setdefault((fg, int(did, 16), name), set()).add(int(oid, 16))
    known = {(fg, did) for fg, did, _ in hits}
    for line in open(os.path.join(CACHE, "index.tsv"), encoding="utf-8", errors="replace"):
        fg, _, did, _, _, name = line.rstrip("\n").split("\t", 5)
        # e.g. Comet: no embedded Arno table; *Map = the outfits' texture data files (no tables)
        if "LegacyAvatar" in name and not name.endswith("Map") and (fg, int(did, 16)) not in known:
            hits[(fg, int(did, 16), name)] = set()
    return hits


def build_tables(payload, tmp, phys=None, workers=6):
    jobs = sorted(table_hits().items())
    failed, skip = [], []
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(table_job, fg, did, name, oids, payload, tmp, phys): (fg, did, name) for (fg, did, name), oids in jobs}
        for f in concurrent.futures.as_completed(futs):
            fg, did, name = futs[f]
            try:
                line = f.result()
                print(line, flush=True)
                if line.endswith(("nothing to edit", "no tables")):
                    skip.append(f"{did:016X}\t{fg}\n")
            except BaseException as e:  # keep going, report every failed job at the end
                failed.append(f"{fg} {name}: {e!r}"[:600])
                print("  FAILED", failed[-1], flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} table jobs failed")
    # copies left vanilla (e.g. Comet / ThomasCarneillon: full data file in Paris only, ~1-23 KB stubs elsewhere);
    # acu_install.py needs them listed when another copy of the same ID has a payload
    open(os.path.join(payload, "skip.tsv"), "w", encoding="utf-8").writelines(sorted(skip))


def phys_host(x):
    """column of the first PHYS_HOST skeleton referenced by a skeleton table, or None"""
    cells = {int(oid): col for col, oid in SKEL_CELL.findall(x)}
    return next((cells[h] for h in PHYS_HOST if h in cells), None)


def table_job(fg, did, name, oids, payload, tmp, phys=None):
    """edit the Arno / legacy tables of one data file copy and pack it; returns a log line"""
    data, un, xml = vanilla(fg, did, tables_only=True)
    if not os.path.isdir(xml):
        return f"  {fg} {name}: no tables"
    jt = os.path.join(tmp, "job_" + fkey(fg) + f"_{did:X}")
    d = os.path.join(jt, "data")
    shutil.copytree(un, d)
    done, edited, skel_path, cmds, checks = set(), [], None, [], []
    for xf in sorted(os.listdir(xml)):
        x = open(os.path.join(xml, xf), encoding="utf-8-sig").read()
        m = OBJ_ID.search(x[:400])
        oid = int(m.group(1)) if m else -1
        drops = TABLE_DROPS.get(oid)
        legacy = LEGACY_TABLE.search(xf) and xf.endswith(".BuildTable.xml")
        if drops is None and legacy:
            drops = {c for c, t in COLUMN.findall(x) if t in VISUAL_TYPES}  # legacy outfit visuals
        sets = {}
        if phys and (oid == SKEL_TABLE or (legacy and xf.endswith("_Skeleton.BuildTable.xml"))):
            col = phys_host(x)
            if col is None:
                print(f"  WARN {fg} {name} {xf}: no cloth add-on cell for {PHYS_NAME}", flush=True)
            else:
                if skel_path is None:
                    ref = re.search(r'Path="([^"\\]+\\[^"\\]+)\\', x)  # <forge base>\<data file>
                    skel_path = (ref.group(1) if ref else name) + "\\" + PHYS_NAME
                sets[col] = (str(PHYS_ID), skel_path)
        drops = drops or set()
        if not drops and not sets:
            continue
        tname = xf[:-4]
        vxml = os.path.join(xml, xf)
        exml = os.path.join(jt, tname + ".edited.xml")
        bt_tool.edit(vxml, exml, drops, sets, False, quiet=True)
        chk = os.path.join(jt, tname + ".chk")
        os.remove(os.path.join(d, tname))  # compile-xml would leave <file>.bak next to what it overwrites
        cmds += [("compile-xml", vxml, chk), ("compile-xml", exml, os.path.join(d, tname))]
        checks.append((tname, chk))
        done.add(oid)
        edited.append(f"{tname.split('_-_', 1)[-1]}-{len(drops)}" + (f"+phys@{next(iter(sets))}" if sets else ""))
    if skel_path:  # the physics skeleton object itself (+ its collision objects), appended to the data file
        n = max(int(f.split("_-_")[0]) for f in os.listdir(d)) + 1
        for i, (src, obj_name) in enumerate(phys):
            shutil.copy(src, os.path.join(d, f"{n + i}_-_{obj_name}"))
    missing = (oids & (set(TABLE_DROPS) | ({SKEL_TABLE} if phys else set()))) - done
    if missing:
        raise SystemExit(f"{fg} {name}: tables {sorted(f'{o:X}' for o in missing)} not found in the XML export")
    line = f"  {fg} {name}: " + (", ".join(edited) if edited else "nothing to edit")
    if done:
        out = os.path.join(payload, "forge", fkey(fg), f"{did:016X}_{name}.data")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        log = batch(cmds + [("pack-data", d, data, out)], jt)
        for tname, chk in checks:
            if open(chk, "rb").read() != open(os.path.join(un, tname), "rb").read():
                os.remove(out)
                raise SystemExit(f"{fg} {name} {tname}: vanilla XML does not recompile byte-identical")
        line += " | " + [l for l in log.splitlines() if not l.startswith("BATCH ")][-1]
    shutil.rmtree(jt)
    return line


def add_materials(folder, n, tmp, tex_size, spec, gloss):
    """4 Materials + TextureSets + diffuse/normal maps and the shared specular map as objects n, n+1, ... of folder"""
    mat_x = open(TPL_MAT, encoding="utf-8-sig").read()
    set_x = open(TPL_SET, encoding="utf-8-sig").read()
    hpath = r"DataPC_ACU_Paris\CN_U_FR_Arno_Head" + "\\"
    for (part, png), g in zip(PARTS, gloss):
        nm = f"Karin_{part}"
        ids = [(T_MAT, MAT[part]), (T_SET, SET[part]), (T_SRC, SRC[part]), (T_DIFF, DIFF[part]), (T_NORM, NORM[part]), (T_SPEC, SPEC)]
        mx = subst(mat_x, ids)
        mx = mx.replace('<Bool Name="TwoSided">False</Bool>', '<Bool Name="TwoSided">True</Bool>')
        mx = mx.replace('<Enum Name="Category" Type="ResourceCategory" Value="RC_Environment">0</Enum>',
                        '<Enum Name="Category" Type="ResourceCategory" Value="RC_Character">1</Enum>')
        sx = subst(set_x, ids)
        for old, new in (("CN_W_1Handed_Sp2_DiffuseMap", f"{nm}_DiffuseMap"), ("CN_W_1Handed_Sp2_NormalMap", f"{nm}_NormalMap"),
                         ("CN_W_1Handed_Sp2_SpecularMap", "Karin_SpecularMap"), ("CN_W_1Handed_Sp2_Set", f"{nm}_Set")):
            mx, sx = mx.replace(old, new), sx.replace(old, new)
        mx = re.sub(r'Path="(?:DataPC|DataPC\\Game Bootstrap Settings)\\', lambda _: f'Path="{hpath}', mx)
        sx = re.sub(r'Path="DataPC\\', lambda _: f'Path="{hpath}', sx)
        for f, x in ((f"{nm}.Material", mx), (f"{nm}_Set.TextureSet", sx)):
            xp = os.path.join(tmp, f + ".xml")
            open(xp, "w", encoding="utf-8").write(x)
            run("compile-xml", xp, os.path.join(folder, f"{n}_-_{f}"))
            n += 1
        dds = texconv(os.path.join(SRC_TEX, png), tmp, "BC7_UNORM_SRGB", tex_size)
        print(" ", run("tex-import", TPL_DIFF, dds, os.path.join(folder, f"{n}_-_{nm}_DiffuseMap.TextureMap"), "--id", f"{DIFF[part]:X}").splitlines()[-1])
        n += 1
        flat = os.path.join(tmp, f"{nm}_NormalMap.png")
        Image.new("RGBA", (64, 64), (128, 128, 0, g)).save(flat)
        print(" ", run("tex-import", TPL_NORM, texconv(flat, tmp, "BC7_UNORM"), os.path.join(folder, f"{n}_-_{nm}_NormalMap.TextureMap"), "--id", f"{NORM[part]:X}").splitlines()[-1])
        n += 1
    sp = os.path.join(tmp, "Karin_SpecularMap.png")
    Image.new("RGBA", (64, 64), (spec, spec, spec, 255)).save(sp)
    print(" ", run("tex-import", TPL_SPEC, texconv(sp, tmp, "BC7_UNORM_SRGB"), os.path.join(folder, f"{n}_-_Karin_SpecularMap.TextureMap"), "--id", f"{SPEC:X}").splitlines()[-1])
    return n + 1


def build_head(mesh_dir, payload, tmp, tex_size, spec, gloss):
    data, un, _ = vanilla(*HEAD_SRC[:1], HEAD)
    d = os.path.join(tmp, "head")
    shutil.copytree(un, d)
    for i, f in enumerate(LODS):
        assert os.path.exists(os.path.join(d, f)), f
        shutil.copy(os.path.join(mesh_dir, f"karin_lod{i}.Mesh"), os.path.join(d, f))
    n = max(int(f.split("_-_")[0]) for f in os.listdir(d)) + 1
    add_materials(d, n, tmp, tex_size, spec, gloss)
    pack(d, data, os.path.join(payload, f"{HEAD:016X}_{HEAD_SRC[1]}.data"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh_dir", help="karin_lod0..3.Mesh")
    ap.add_argument("out_dir", help="deleted and rebuilt; the payload goes to <out_dir>/payload")
    ap.add_argument("--tex-size", type=int, default=2048)
    ap.add_argument("--spec", type=int, default=40, help="grey level of the shared specular map")
    ap.add_argument("--gloss", default="90,90,120,70", help="normal-map alpha (gloss) for Face,Body,Hair,Costume")
    ap.add_argument("--phys", help="Karin_Phys Skeleton XML from acu_phys_skel.py --id PHYS_ID (stage 2)")
    ap.add_argument("--game", help="game folder with ACU.exe (default: ACU_GAME_DIR, else the Steam libraries)")
    a = ap.parse_args()
    missing = [n for n in ENV if not os.environ.get(n)]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see the kit README)")
    acu_install.GAME = acu_install.find_game(["--game", a.game] if a.game else [])
    mesh_dir, out = os.path.abspath(a.mesh_dir), os.path.abspath(a.out_dir)
    tex_size, spec = a.tex_size, a.spec
    gloss = [int(v) for v in a.gloss.split(",")]
    if os.path.exists(out):
        shutil.rmtree(out)
    payload, tmp = os.path.join(out, "payload"), os.path.join(SCRATCH, "build_tmp")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(payload)
    os.makedirs(tmp)
    print("tables")
    phys = None
    if a.phys:  # stage 2: Karin's physics add-on skeleton (acu_phys_skel.py output, Object ID = PHYS_ID)
        px = os.path.abspath(a.phys)
        objs = [(px, PHYS_NAME, PHYS_ID)] + [(px.replace(".Skeleton.xml", f".{k}.xml"), f"Karin_Phys.{k}", i)
                                              for k, i in PHYS_EXTRA if os.path.exists(px.replace(".Skeleton.xml", f".{k}.xml"))]
        phys = []  # [(compiled file, object name)], the skeleton first
        for src, obj_name, oid in objs:
            if OBJ_ID.search(open(src, encoding="utf-8-sig").read(400)).group(1) != str(oid):
                raise SystemExit(f"{src}: Object ID must be {oid} (acu_phys_skel.py --id {PHYS_ID})")
            phys.append((os.path.join(tmp, obj_name), obj_name))
            run("compile-xml", src, phys[-1][0])
        print("phys objects:", ", ".join(n for _, n in phys))
    build_tables(payload, tmp, phys)
    print("CN_U_FR_Arno_Head")
    build_head(mesh_dir, payload, tmp, tex_size, spec, gloss)
    shutil.rmtree(tmp)
    print("BUILD_OK", out)


if __name__ == "__main__":
    main()
