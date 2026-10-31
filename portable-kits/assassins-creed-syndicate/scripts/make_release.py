"""Pack build_mod.py payloads into a self-contained, redeployable mod package (zip) for another PC.

  python make_release.py <out.zip> <label>=<payload_dir> [<label>=<payload_dir> ...] [--python <embed.zip>]

Each payload becomes payload_<label>.tar.xz (solid xz: the per-forge copies of the same data file sit side by side and
compress against each other, 232 MB -> ~44 MB) with payload/vanilla.tsv added: forge, ID and size:sha1 of the vanilla
copy behind every forge variant and skip.tsv line, read from THIS PC's game (the build source; rows the mod repointed
are read through acs_install's state), so acs_install.py can match the copies of any game version by content
(2026-10-30, replaces the whole-forge size lock of vanilla_sizes.tsv). The zip (stored, the archives are already
compressed) also holds acs_install.py, install_<label>.cmd per payload, uninstall.cmd, status.cmd and README.txt.
2026-10-30 (user): the target PC needs no Python and no PowerShell (some PCs block PowerShell scripts). The zip carries
the official Windows embeddable Python (--python, default ACS_PYTHON_EMBED; python-x.y.z-embed-amd64.zip from python.org,
Authenticode-signed by the PSF, ships its own vcruntime) as python/, and the .cmd files are plain batch that run
python\\python.exe -I (isolated: no PYTHON* variables, no user site). They stay ASCII so cmd reads them the same under
every console code page. acs_install.py needs only the standard library (tarfile + _lzma for the .tar.xz) and tasklist.
"""
import io
import json
import lzma
import os
import struct
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acs_install  # noqa: E402

CMD = """@echo off
setlocal
cd /d "%~dp0"
if not exist "python\\python.exe" (
  echo python\\python.exe not found: extract the whole zip into a folder first, then run this file from there.
  echo.
  pause
  exit /b 1
)
"python\\python.exe" -I -B acs_install.py {args} %*
echo.
pause
"""

README = """Karin_Original -> 雅各布 / 伊薇·弗莱 (Assassin's Creed Syndicate) 角色替换 mod

适用：PC 版 Assassin's Creed Syndicate（Steam / Ubisoft Connect / Epic 等，不限定具体版本），64 位 Windows 10 / 11。
不需要另装 Python，也不用 PowerShell：包里自带官方嵌入式 Python（python 文件夹），.cmd 都是普通批处理。
先把整个压缩包解压到一个文件夹（不要在压缩包里直接双击运行）。
游戏目录：自动查找 Steam 库、Ubisoft Connect（Uplay）、Epic 的安装位置；找到多个时会列出来让你选编号。
  都找不到时在命令行加参数：install_xxx.cmd --game "D:\\...\\Assassin's Creed Syndicate"
  Steam / Ubisoft Connect 默认装在 C:\\Program Files (x86) 下，需要管理员权限：右键 .cmd → 以管理员身份运行
  （没有权限时程序会提示并且不做任何改动）。

使用（先关闭游戏）：
{installs}
  uninstall.cmd     卸载，恢复原版（换版本前先卸载）
  status.cmd        查看当前安装状态

说明：
- 不论穿什么装备，雅各布和伊薇都显示为 Karin（外套、帽子、兜帽、腰带、护腕、项链、头发都去掉）；
  伊薇的特殊服装（搏击俱乐部 / 礼服）和雅各布的同类服装同样只剩 Karin。莉迪亚·弗莱（一战记忆）用的是伊薇的头部模型，也会变成 Karin。
- 预渲染过场视频（videos\\*.bk2）无法修改，里面仍是原版双胞胎。开膛手杰克 DLC 里的老年雅各布 / 伊薇未替换。
- 安装是在原 forge 末尾追加数据并改写索引；状态记录在游戏目录 .karin_acs_state.json，卸载据此还原。
- 不锁定游戏版本：安装时按 ID 在每个 forge 里找到要替换的数据文件，逐个和制作时的原版内容比对（大小 + SHA-1）。
  内容相同的直接替换；在别的 forge 里有相同内容的，用那份对应的替换；内容不同的（其他版本、或被别的 mod 改过）
  照样替换并列出清单，卸载时一并还原；没有对应替换文件的保持原版并列出；本机没有的 forge（例如没装的 DLC）跳过。
- 安装之后又装了新的 DLC：先 uninstall.cmd 再重新安装，新 DLC 里的双胞胎才会替换。
- 若在已安装状态下游戏文件被更新或校验修复，请删除游戏目录里的 .karin_acs_state.json，恢复原版文件后再重新安装。
"""

LABELS = {"s1": "第一阶段：模型 + 材质（无物理、无表情）",
          "s2": "完整版：Karin 模型 + 材质 + 表情（嘴 / 眨眼 / 眼球）+ 次级物理（头发 / 双马尾 / 尾巴 / 裙子摆动，裙子与大腿碰撞）"}


def vanilla_prints(payload):
    """vanilla.tsv of one payload: forge, IDHEX, size:sha1 of every copy behind a forge variant or skip.tsv line"""
    game = acs_install.GAME = acs_install.find_game([])
    state = os.path.join(game, ".karin_acs_state.json")
    st = json.load(open(state)) if os.path.exists(state) else {"forges": {}}
    orig = {os.path.normcase(fg): s["rows"] for fg, s in st["forges"].items()}
    want = {}  # forge -> ids
    vroot = os.path.join(payload, "forge")
    for d in sorted(os.listdir(vroot)) if os.path.isdir(vroot) else []:
        want.setdefault(d.replace("__", os.sep), set()).update(acs_install.scan(os.path.join(vroot, d)))
    if os.path.exists(os.path.join(payload, "skip.tsv")):
        for line in open(os.path.join(payload, "skip.tsv"), encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                i, fg = line.rstrip("\n").split("\t")
                want.setdefault(fg, set()).add(int(i, 16))
    out = []
    for fg in sorted(want):
        path = os.path.join(game, fg)
        rows = acs_install.rows_with_pos(path)
        with open(path, "rb") as f:
            for oid in sorted(want[fg]):
                row = orig.get(os.path.normcase(fg), {}).get(f"{oid:016X}")
                off, size = struct.unpack("<qQi", bytes.fromhex(row[1]))[::2] if row else rows[oid][2:]
                out.append(f"{fg}\t{oid:016X}\t{acs_install.fingerprint(f, off, size)}\n")
    return "".join(out).encode("utf-8")


def pack(payload, out):
    files = []
    for d, _, fs in os.walk(payload):
        files += [os.path.relpath(os.path.join(d, f), payload) for f in fs]
    files.sort(key=lambda p: (os.path.basename(p), p))  # the same data file of every forge side by side
    prints = vanilla_prints(payload)
    with tarfile.open(out, "w:xz", preset=9 | lzma.PRESET_EXTREME) as t:
        for p in files:
            if p not in ("vanilla.tsv", "vanilla_sizes.tsv"):
                t.add(os.path.join(payload, p), arcname="payload/" + p.replace(os.sep, "/"))
        ti = tarfile.TarInfo("payload/vanilla.tsv")
        ti.size = len(prints)
        t.addfile(ti, io.BytesIO(prints))
    return len(files)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if a else 2)
    py = a.pop(a.index("--python") + 1) if "--python" in a else os.environ.get("ACS_PYTHON_EMBED")
    if "--python" in a:
        a.remove("--python")
    if not py or not os.path.isfile(py):
        raise SystemExit("no embeddable Python: pass --python <python-x.y.z-embed-amd64.zip> (python.org) or set ACS_PYTHON_EMBED")
    out = os.path.abspath(a[0])
    items = [x.split("=", 1) for x in a[1:]]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_STORED) as z:
        installs = []
        for label, payload in items:
            name = f"payload_{label}.tar.xz"
            n = pack(payload, os.path.join(tmp, name))
            z.write(os.path.join(tmp, name), name)
            z.writestr(f"install_{label}.cmd", CMD.format(args=f'install "{name}"').replace("\n", "\r\n"))
            installs.append(f"  install_{label}.cmd  安装 {label}：{LABELS.get(label, label)}")
            print(f"{label}: {n} files -> {name} {os.path.getsize(os.path.join(tmp, name)):,} bytes")
        z.write(os.path.join(HERE, "acs_install.py"), "acs_install.py")
        with zipfile.ZipFile(py) as e:
            for i in e.infolist():
                if not i.is_dir():
                    z.writestr("python/" + i.filename, e.read(i), zipfile.ZIP_DEFLATED)
        print("python:", os.path.basename(py))
        z.writestr("uninstall.cmd", CMD.format(args="uninstall").replace("\n", "\r\n"))
        z.writestr("status.cmd", CMD.format(args="status").replace("\n", "\r\n"))
        z.writestr("README.txt", ("\ufeff" + README.format(installs="\n".join(installs))).replace("\n", "\r\n").encode("utf-8"))
    os.replace(out + ".tmp", out)
    print("RELEASE_OK", out, f"{os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
