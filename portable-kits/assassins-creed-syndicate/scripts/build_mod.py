"""Build the Karin_Original -> Jacob / Evie Frye payload for acs_install.py (AC Syndicate PC v1.51, CODEX build).

  python build_mod.py <mesh_root> <out_dir> [--tex-size 2048] [--spec 40] [--gloss 90,90,120,70] [--workers 6]
                      [--phys <twin>=<Karin_Phys.Skeleton.xml> ...]

<mesh_root>/<twin>/karin_lod0..3.Mesh: export_karin_lods.py --profile acs_weapon --mat-base CHARS[twin]["base"], every
LOD rotated -90 (glb_rotate.py) and imported with the twin's vanilla head LOD ID (import-glb ... CHARS[twin]["lods"][i]).
Writes <out_dir>/payload/forge/<forge>/<IDHEX>_<name>.data and payload/skip.tsv (layout: acs_install.py).

Contract (2026-10-26, cache/twin_*.tsv from scan_objs.py + objs_to_tsv.py):
  - The twins' BuildTables are embedded (same object IDs) in many data files of every world forge and of the dlc_20 /
    dlc_21 patch forges: player (ACVI_CHR_P_*), unique NPC (ACVI_CHR_U_*, *_HID), menus (ACVI_DataAI_UIDataRoot_*),
    mission DataBlocks, the FightClub / FormalSuit variants and Lydia Frye (who wears Evie's head and bracers). Every
    copy of every such data file (all index rows with its ID) is rebuilt from itself.
  - TABLES: the visual columns (VISUAL_TYPES) are dropped from every row except the columns in TABLES[oid] (the head
    LODSelector / LOD0 mesh, which now draws the whole Karin); skeleton, sub-table and sound columns stay (holster and
    gadget bones). EXTRA_DROPS adds the outfits' ColorSets tables.
  - The head LOD meshes (CHARS[twin]["lods"]) live in the head containers, in the dlc_11..14 player files, in Lydia's
    head and Evie's SpecialLOD head; London_20 keeps them as standalone data files. Every copy is replaced by Karin
    (same ID) and that data file also gets the twin's 4 CN_Weapon_NoAlphaTest materials, texture sets, diffuse / flat
    normal maps (A = gloss) and specular map (IDs CHARS[twin]["base"] + MAT / SET / ... offsets).
  - --phys (stage 2): Karin_Phys_<twin> (acs_phys_skel.py, + its BallJointCommonData / LiteRagdoll) is appended to every
    data file holding a PHYS_HOSTS head table, whose hair add-on skeleton cell (column 14) is pointed at it.
compile-xml of every vanilla table is checked byte-identical per copy (the build stops otherwise).

Machine paths (portable kit): ACS_DOTNET, ACS_HARNESS, ACS_TEXCONV, ACS_SRC_TEX, ACS_TEMPLATES and ACS_CACHE are checked
before anything is written; ACS_SCRATCH (default <TEMP>/acs_work); game folder --game, ACS_GAME_DIR or the installs
acs_install.py finds (Steam, Ubisoft Connect, Epic).
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

from PIL import Image

os.environ.setdefault("ACU_GAME", "Syndicate")  # AnvilToolkit Game enum for the harness
HERE = os.path.dirname(os.path.abspath(__file__))
# machine paths (portable kit): environment variables, checked in main() before anything is written
ENV = ("ACS_DOTNET", "ACS_HARNESS", "ACS_TEXCONV", "ACS_SRC_TEX", "ACS_TEMPLATES", "ACS_CACHE")
DOTNET = os.environ.get("ACS_DOTNET", "")        # dotnet.exe of the .NET 9 runtime
HARNESS = os.environ.get("ACS_HARNESS", "")      # AcuHarness.dll (Unity kit acuharness/build.ps1, Syndicate.gfl)
TEXCONV = os.environ.get("ACS_TEXCONV", "")      # DirectXTex texconv.exe
SRC_TEX = os.environ.get("ACS_SRC_TEX", "")      # Karin_Face.png / Karin_Body.png / Karin_Hair.png / Karin_Costume.png
CACHE = os.environ.get("ACS_CACHE", "")          # index.tsv, twin_objs.tsv, twin_meshes.tsv, twin_objs2.tsv
# heavy, regenerable intermediates stay OFF the synced project folder (BaiduSync touches every unpacked file)
SCRATCH = os.environ.get("ACS_SCRATCH") or os.path.join(tempfile.gettempdir(), "acs_work")
VANILLA = os.path.join(SCRATCH, "vanilla")
TEMPLATES = os.environ.get("ACS_TEMPLATES", "")  # material / texture-set XML and inline-mip texture templates (kit README)
sys.path.insert(0, HERE)
import acs_forge  # noqa: E402
import acs_install  # noqa: E402
import bt_tool  # noqa: E402

CHARS = {  # base: new object IDs above the highest vanilla ID (0x8CBB3C827F); lods: vanilla head LOD0..3 mesh IDs
    "jacob": {"base": 0xC04B410000, "lods": [0x27CCC692C6, 0x38534E59BE, 0x38534E59C3, 0x38534E59C8]},
    "evie": {"base": 0xC04B450000, "lods": [0x3E33A56077, 0x5D2B51F63C, 0x5D2B51F641, 0x5D2B51F646]},
}
LOD_OF = {oid: (twin, i) for twin, c in CHARS.items() for i, oid in enumerate(c["lods"])}
VISUAL_TYPES = {"GraphicObject", "SoftBody", "TextureSet", "Material", "FX"}
TABLES = {  # BuildTable object ID -> columns kept although visual
    0x0FE84A8684: {"1"},   # ACVI_CHR_P_JacobFrye_Head (1 = head LODSelector -> Karin)
    0x0FE84A864A: set(),   # ACVI_CHR_P_JacobFrye_OutFits
    0x2FF072B654: set(),   # ACVI_CHR_P_JacobFrye_Belts
    0x2FF072B66E: set(),   # ACVI_CHR_P_JacobFrye_Bracers (multi-tool glove)
    0x5B2AF6EA66: set(),   # ACVI_CHR_P_JacobFrye_Bracers_DartGun
    0x5B2AF6EA67: set(),   # ACVI_CHR_P_JacobFrye_Bracers_RopeLauncher
    0x47C93F09B4: set(),   # ACVI_CHR_P_JacobFrye_FightClub_Body (head = Jacob's head table)
    0x483A8DECA4: set(),   # ACVI_CHR_P_JacobFrye_FormalSuit_Body
    0x14B2685216: {"1"},   # ACVI_CHR_P_EvieFrye_Head
    0x6CF114F8C1: {"1"},   # ACVI_CHR_P_EvieFrye_Head_SpecialLOD (FightClub / FormalSuit; 1 = LOD0 mesh)
    0x44F5C89FE1: set(),   # ACVI_CHR_P_EvieFrye_Outfits
    0x44F5C89FE2: set(),   # ACVI_CHR_P_EvieFrye_Cloak
    0x44F5C89FE3: set(),   # ACVI_CHR_P_EvieFrye_Bracers (also Lydia's)
    0x60E697FF79: set(),   # ACVI_CHR_P_EvieFrye_Bracers_DartGun
    0x60E697FF81: set(),   # ACVI_CHR_P_EvieFrye_Bracers_RopeLauncher
    0x58EAD0A853: set(),   # ACVI_CHR_P_EvieFrye_Necklace
    0x4855906D31: set(),   # ACVI_CHR_P_EvieFrye_FormalSuit_Body
    0x5C8B4C3D6B: set(),   # ACVI_CHR_P_EvieFrye_FightClub_Body
    0x5DCB8CAD55: {"1"},   # ACVI_CHR_P_LydiaFrye_Head (1 = Evie's head LODSelector)
    0x4479401BE8: set(),   # ACVI_CHR_P_LydiaFrye_Body
}
EXTRA_DROPS = {0x0FE84A864A: {"49"}, 0x44F5C89FE1: {"49"}}  # outfit ColorSets (material swaps of the dropped meshes)
PHYS_HOSTS = {0x0FE84A8684: "jacob", 0x14B2685216: "evie", 0x6CF114F8C1: "evie", 0x5DCB8CAD55: "evie"}
PHYS_COL = "14"  # head table: hair add-on skeleton (the hair meshes are dropped)
HITS = [os.path.join(CACHE, n) for n in ("twin_objs.tsv", "twin_meshes.tsv", "twin_objs2.tsv")]
# left vanilla: the Jack the Ripper old Jacob (158 MB data file) only embeds Jacob's gadget-glove tables
EXCLUDE = {0x77916812C5}  # ACVI_DLC_CHR_P_Jacob40
COLUMN = re.compile(r'<Unsigned32 Name="ColumnID">(\d+)</Unsigned32>.*?<DynamicProperty Name="Type"[^>]*ObjectType="(\w+)"', re.S)
OBJ_ID = re.compile(r'<Object ID="(\d+)"')

TPL_MAT = os.path.join(TEMPLATES, "9472_-_ACVI_Weapons_Kukri.Material.xml")        # CN_Weapon_NoAlphaTest (DataPC GBS)
TPL_SET = os.path.join(TEMPLATES, "12767_-_ACVI_Weapons_Kukri_Set.TextureSet.xml")
T_MAT, T_SET, T_SRC, T_DIFF, T_NORM, T_SPEC = ("149519537898", "147133230926", "147133230925",
                                               "147133230948", "148593984605", "148593985996")
TPL_DIFF = os.path.join(TEMPLATES, "0_-_ACVI_CHR_P_JacobFrye_Head_DiffuseMap.TextureMap")  # inline mips, sRGB
TPL_NORM = os.path.join(TEMPLATES, "0_-_ACVI_CHR_P_JacobFrye_Head_NormalMap.TextureMap")   # inline mips, linear
TPL_SPEC = os.path.join(TEMPLATES, "0_-_ACVI_Weapons_Kukri_SpecularMap.TextureMap")        # MapSpecular, sRGB
PARTS = [("Face", "Karin_Face.png"), ("Body", "Karin_Body.png"), ("Hair", "Karin_Hair.png"), ("Costume", "Karin_Costume.png")]
# per-twin offsets from CHARS[twin]["base"]; MAT = export_karin_lods.py --profile acs_weapon (--mat-base base)
MAT, SET, DIFF, NORM, SRC, SPEC, PHYS = 0x01, 0x11, 0x21, 0x31, 0x51, 0x41, 0xF00
PHYS_EXTRA = [("BallJointCommonData", 1), ("LiteRagdoll", 2)]  # written next to the skeleton XML by acs_phys_skel.py


def run(*args, check=True):
    r = subprocess.run([DOTNET, HARNESS, *args], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if check and (r.returncode != 0 or "Exception" in out):
        raise SystemExit(f"harness {args[0]} failed:\n{out[-3000:]}")
    return out


def batch(cmds, tmp):
    """several harness commands in one process (AcuHarness batch: absolute paths, one tab-separated line each)"""
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


def obj_id(path):
    """object ID of an unpacked object file: u64 at offset 2"""
    with open(path, "rb") as f:
        return struct.unpack("<Q", f.read(10)[2:])[0]


def vanilla(fg, did):
    """extract + unpack one copy into <SCRATCH>/vanilla/<forge>/<IDHEX>/ (cached) and export its BuildTables as XML"""
    base = os.path.join(VANILLA, fkey(fg), f"{did:016X}")
    datas = [f for f in os.listdir(base) if f.endswith(".data")] if os.path.isdir(base) else []
    if not datas:
        p = acs_forge.extract(os.path.join(acs_install.GAME, fg), base, [did])
        assert len(p) == 1, (fg, did, p)
        datas = [os.path.basename(p[0])]
    data = os.path.join(base, datas[0])
    stem = os.path.splitext(datas[0])[0]
    un, xml = os.path.join(base, "unpacked", stem), os.path.join(base, "xml", stem)
    ok = os.path.join(base, ".xml_ok")
    if not os.path.exists(ok):
        if not os.path.isdir(un):
            run("unpack-data", data, un)
        if any(f.endswith(".BuildTable") for f in os.listdir(un)):
            run("export-xml-dir", un, xml, "*.BuildTable")
        open(ok, "w").write("tables")
    return data, un, xml


def pack_cmd(folder, orig, out):
    for f in os.listdir(folder):  # compile-xml leaves <file>.bak next to what it overwrote
        if f.endswith(".bak"):
            os.remove(os.path.join(folder, f))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return ("pack-data", folder, orig, out)


def jobs_from_hits():
    """every copy (index rows of the same data file ID, any forge) of every data file holding a target object"""
    wanted = set(TABLES) | set(LOD_OF)
    dids = {}
    for h in HITS:
        if not os.path.exists(h):
            print("WARN missing", h)
            continue
        for line in open(h, encoding="utf-8"):
            fg, did, name, oid = line.rstrip("\n").split("\t")
            if int(oid, 16) in wanted and int(did, 16) not in EXCLUDE:
                dids[int(did, 16)] = name
    jobs = []
    for line in open(os.path.join(CACHE, "index.tsv"), encoding="utf-8", errors="replace"):
        fg, _, did, _, _, name = line.rstrip("\n").split("\t", 5)
        if int(did, 16) in dids:
            jobs.append((fg, int(did, 16), name))
    return sorted(set(jobs))


def job(fg, did, name, payload, tmp, mesh_root, twin_objs, phys):
    """rebuild one copy; returns a log line ending in 'nothing to edit' when the copy stays vanilla"""
    data, un, xml = vanilla(fg, did)
    ids = {obj_id(os.path.join(un, f)): f for f in os.listdir(un)}
    tables = [o for o in ids if o in TABLES]
    lods = [o for o in ids if o in LOD_OF]
    if not tables and not lods:
        return f"  {fg} {name}: nothing to edit"
    jt = os.path.join(tmp, "job_" + fkey(fg) + f"_{did:X}")
    d = os.path.join(jt, "data")
    shutil.copytree(un, d)
    cmds, checks, edited, hosts = [], [], [], set()
    for oid in sorted(tables):
        f = ids[oid]
        vxml = os.path.join(xml, f + ".xml")
        x = open(vxml, encoding="utf-8-sig").read()
        if OBJ_ID.search(x[:400]).group(1) != str(oid):
            raise SystemExit(f"{fg} {name} {f}: XML ID differs from the object header")
        drops = ({c for c, t in COLUMN.findall(x) if t in VISUAL_TYPES} - TABLES[oid]) | EXTRA_DROPS.get(oid, set())
        sets = {}
        if phys and oid in PHYS_HOSTS:
            twin = PHYS_HOSTS[oid]
            sets[PHYS_COL] = (str(CHARS[twin]["base"] + PHYS), f"Karin_Phys_{twin}.Skeleton")
            hosts.add(twin)
        exml = os.path.join(jt, f + ".edited.xml")
        bt_tool.edit(vxml, exml, drops, sets, False, quiet=True, add_missing=True)  # Lydia's head row lacks cell 14
        chk = os.path.join(jt, f + ".chk")
        os.remove(os.path.join(d, f))  # compile-xml would leave <file>.bak next to what it overwrites
        cmds += [("compile-xml", vxml, chk), ("compile-xml", exml, os.path.join(d, f))]
        checks.append((f, chk))
        edited.append(f"{f.split('_-_', 1)[-1].rsplit('.', 1)[0]}-{len(drops)}" + ("+phys" if sets else ""))
    twins = set()
    for oid in sorted(lods):
        twin, i = LOD_OF[oid]
        shutil.copy(os.path.join(mesh_root, twin, f"karin_lod{i}.Mesh"), os.path.join(d, ids[oid]))
        twins.add(twin)
        edited.append(f"{twin}_lod{i}")
    n = max(int(f.split("_-_")[0]) for f in os.listdir(un)) + 1  # d may lack the tables compile-xml writes later
    for twin in sorted(twins):
        for src, nm in twin_objs[twin]:
            shutil.copy(src, os.path.join(d, f"{n}_-_{nm}"))
            n += 1
    for twin in sorted(hosts):
        for src, nm in phys[twin]:
            shutil.copy(src, os.path.join(d, f"{n}_-_{nm}"))
            n += 1
    out = os.path.join(payload, "forge", fkey(fg), f"{did:016X}_{name}.data")
    log = batch(cmds + [pack_cmd(d, data, out)], jt)
    for f, chk in checks:
        if open(chk, "rb").read() != open(os.path.join(un, f), "rb").read():
            os.remove(out)
            raise SystemExit(f"{fg} {name} {f}: vanilla XML does not recompile byte-identical")
    shutil.rmtree(jt)
    tail = [l for l in log.splitlines() if not l.startswith("BATCH ")][-1]
    return f"  {fg} {name}: " + ", ".join(edited) + (f" +mats {','.join(sorted(twins))}" if twins else "") + " | " + tail


def twin_objects(twin, tmp, tex_size, spec, gloss):
    """compile the twin's 4 Materials + TextureSets, diffuse / flat normal maps and the specular map once;
    returns [(compiled file, object file name)] in the order they are appended to a data file"""
    b = CHARS[twin]["base"]
    od = os.path.join(tmp, "objs_" + twin)
    os.makedirs(od)
    mat_x = open(TPL_MAT, encoding="utf-8-sig").read()
    set_x = open(TPL_SET, encoding="utf-8-sig").read()
    objs = []
    for k, ((part, png), g) in enumerate(zip(PARTS, gloss)):
        nm = f"Karin_{twin}_{part}"
        ids = [(T_MAT, b + MAT + k), (T_SET, b + SET + k), (T_SRC, b + SRC + k), (T_DIFF, b + DIFF + k),
               (T_NORM, b + NORM + k), (T_SPEC, b + SPEC)]
        mx = subst(mat_x, ids).replace('<Bool Name="TwoSided">False</Bool>', '<Bool Name="TwoSided">True</Bool>')
        sx = subst(set_x, ids)
        for old, new in (("ACVI_Weapons_Kukri_DiffuseMap", f"{nm}_DiffuseMap"), ("ACVI_Weapons_Kukri_NormalMap", f"{nm}_NormalMap"),
                         ("ACVI_Weapons_Kukri_SpecularMap", f"Karin_{twin}_SpecularMap"), ("ACVI_Weapons_Kukri_Set", f"{nm}_Set")):
            mx, sx = mx.replace(old, new), sx.replace(old, new)
        for f, x in ((f"{nm}.Material", mx), (f"{nm}_Set.TextureSet", sx)):
            xp = os.path.join(od, f + ".xml")
            open(xp, "w", encoding="utf-8").write(x)
            run("compile-xml", xp, os.path.join(od, f))
            objs.append((os.path.join(od, f), f))
        dds = texconv(os.path.join(SRC_TEX, png), od, "BC7_UNORM_SRGB", tex_size)
        f = f"{nm}_DiffuseMap.TextureMap"
        print(" ", run("tex-import", TPL_DIFF, dds, os.path.join(od, f), "--id", f"{b + DIFF + k:X}").splitlines()[-1])
        objs.append((os.path.join(od, f), f))
        flat = os.path.join(od, f"{nm}_NormalMap.png")
        Image.new("RGBA", (64, 64), (128, 128, 0, g)).save(flat)
        f = f"{nm}_NormalMap.TextureMap"
        print(" ", run("tex-import", TPL_NORM, texconv(flat, od, "BC7_UNORM"), os.path.join(od, f), "--id", f"{b + NORM + k:X}").splitlines()[-1])
        objs.append((os.path.join(od, f), f))
    sp = os.path.join(od, f"Karin_{twin}_SpecularMap.png")
    Image.new("RGBA", (64, 64), (spec, spec, spec, 255)).save(sp)
    f = f"Karin_{twin}_SpecularMap.TextureMap"
    print(" ", run("tex-import", TPL_SPEC, texconv(sp, od, "BC7_UNORM_SRGB"), os.path.join(od, f), "--id", f"{b + SPEC:X}").splitlines()[-1])
    objs.append((os.path.join(od, f), f))
    return objs


def phys_objects(twin, src, tmp):
    """compile Karin_Phys_<twin> (+ its collision objects written next to it by acs_phys_skel.py)"""
    pid = CHARS[twin]["base"] + PHYS
    objs = [(src, f"Karin_Phys_{twin}.Skeleton", pid)] + [
        (src.replace(".Skeleton.xml", f".{k}.xml"), f"Karin_Phys_{twin}.{k}", pid + i)
        for k, i in PHYS_EXTRA if os.path.exists(src.replace(".Skeleton.xml", f".{k}.xml"))]
    out = []
    for x, nm, oid in objs:
        if OBJ_ID.search(open(x, encoding="utf-8-sig").read(400)).group(1) != str(oid):
            raise SystemExit(f"{x}: Object ID must be {oid} (acs_phys_skel.py --id {pid})")
        out.append((os.path.join(tmp, nm), nm))
        run("compile-xml", x, out[-1][0])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh_root", help="<mesh_root>/<twin>/karin_lod0..3.Mesh (make_meshes.py)")
    ap.add_argument("out_dir", help="deleted and rebuilt; the payload goes to <out_dir>/payload")
    ap.add_argument("--tex-size", type=int, default=2048)
    ap.add_argument("--spec", type=int, default=40, help="grey level of the shared specular map")
    ap.add_argument("--gloss", default="90,90,120,70", help="normal-map alpha (gloss) for Face,Body,Hair,Costume")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--phys", action="append", default=[], metavar="TWIN=SKELETON_XML",
                    help="Karin_Phys_<twin>.Skeleton.xml from make_meshes.py (stage 2; every twin)")
    ap.add_argument("--game", help="game folder with ACS.exe (default: ACS_GAME_DIR, else the installs acs_install.py finds)")
    a = ap.parse_args()
    missing = [n for n in ENV if not os.environ.get(n)]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see the kit README)")
    acs_install.GAME = acs_install.find_game(["--game", a.game] if a.game else [])
    mesh_root, out = os.path.abspath(a.mesh_root), os.path.abspath(a.out_dir)
    tex_size, spec, workers = a.tex_size, a.spec, a.workers
    gloss = [int(v) for v in a.gloss.split(",")]
    phys_src = dict(v.split("=", 1) for v in a.phys)
    for twin in CHARS:
        for i in range(4):
            assert os.path.exists(os.path.join(mesh_root, twin, f"karin_lod{i}.Mesh")), (twin, i)
    if os.path.exists(out):
        shutil.rmtree(out)
    payload, tmp = os.path.join(out, "payload"), os.path.join(SCRATCH, "build_tmp")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(payload)
    os.makedirs(tmp)
    twin_objs = {}
    for twin in CHARS:
        print("materials", twin)
        twin_objs[twin] = twin_objects(twin, tmp, tex_size, spec, gloss)
    phys = {}
    if phys_src:
        if set(phys_src) != set(CHARS):
            raise SystemExit(f"--phys needs every twin: {sorted(CHARS)}")
        phys = {twin: phys_objects(twin, os.path.abspath(p), tmp) for twin, p in phys_src.items()}
        print("phys objects:", {t: [n for _, n in v] for t, v in phys.items()})
    jobs = jobs_from_hits()
    print(f"{len(jobs)} data file copies")
    failed, skip = [], []
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(job, fg, did, name, payload, tmp, mesh_root, twin_objs, phys): (fg, did, name) for fg, did, name in jobs}
        for f in concurrent.futures.as_completed(futs):
            fg, did, name = futs[f]
            try:
                line = f.result()
                print(line, flush=True)
                if line.endswith("nothing to edit"):
                    skip.append(f"{did:016X}\t{fg}\n")
            except BaseException as e:  # keep going, report every failed job at the end
                failed.append(f"{fg} {name}: {e!r}"[:800])
                print("  FAILED", failed[-1], flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} jobs failed")
    open(os.path.join(payload, "skip.tsv"), "w", encoding="utf-8").writelines(sorted(skip))
    shutil.rmtree(tmp)
    print("BUILD_OK", out)


if __name__ == "__main__":
    main()
