"""Pack build_mod.py payloads into a self-contained, redeployable mod package (zip) for another PC.

  python make_release.py <out.zip> <label>=<payload_dir> [<label>=<payload_dir> ...]

Each payload becomes payload_<label>.tar.xz (solid xz: the per-forge copies of the same data file sit side by side and
compress against each other, 232 MB -> ~44 MB) with payload/vanilla_sizes.tsv added: the vanilla size of every forge
of THIS PC's game (the build source; touched forges are read from acu_install's state), so acu_install.py refuses a
game of another version. The zip (stored, the archives are already compressed) also holds acu_install.py,
install_<label>.cmd per payload, uninstall.cmd, status.cmd and README.txt. Target PC: Python 3.8+.
Game folder (the build source): ACU_GAME_DIR, else the Steam libraries (acu_install.find_game).
"""
import io
import json
import lzma
import os
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acu_install  # noqa: E402

CMD = """@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% acu_install.py {args} %*
echo.
pause
"""

README = """Karin_Original -> Arno (Assassin's Creed Unity) 替换 mod

适用：Steam 版 Assassin's Creed Unity 1.5.1（build 21970519），需要 Python 3.8 以上。
游戏目录自动从 Steam 库查找；找不到时在命令行加参数：install_xxx.cmd --game "D:\\...\\Assassin's Creed Unity"

使用（先关闭游戏）：
{installs}
  uninstall.cmd     卸载，恢复原版（换版本前先卸载）
  status.cmd        查看当前安装状态

说明：
- 安装是在原 forge 末尾追加数据并改写索引；状态记录在游戏目录 .karin_acu_state.json，卸载据此还原。
- 安装前会核对每个要改动的 forge 是否与制作时的原版大小一致，不一致（其他版本、或已装了别的 mod）则拒绝安装。
- 若在已安装状态下用 Steam“验证游戏文件完整性”或游戏更新了，请删除游戏目录里的 .karin_acu_state.json 再重新安装。
"""

LABELS = {"v2": "第一阶段：模型 + 材质（已实测可进游戏）",
          "v3": "第二阶段：在 v2 基础上加表情（嘴 / 眨眼 / 眼球）与次级物理（头发 / 尾巴 / 裙子等），尚未实机测试",
          "v4": "第二阶段修正版：v2 + 表情（嘴 / 眨眼 / 眼球）+ 次级物理（头发 / 尾巴 / 裙子等）；修复 v3 在 Logo 处闪退的物理骨骼数据",
          "v4p": "诊断用，仅在 v4 闪退时试：与 v4 相同的物理骨骼，但模型同 v2（看不到摆动和表情），用来区分问题在骨骼还是模型",
          "v5": "第二阶段：v4 + 收紧摆动幅度（尾巴 / 双马尾 / 裙子保持原形，只轻微摆动，裙片不再垂进大腿）",
          "v6": "第二阶段：静止时保持原形、摆动幅度更大更柔软（锥形中心逆重力偏移），裙子与大腿碰撞（跑动时被腿推开）",
          "v6n": "备用，仅在 v6 闪退时试：与 v6 相同的摆动设置，但不含裙子与大腿的碰撞体",
          "v7": "完整版：Karin 模型 + 材质 + 表情（嘴 / 眨眼 / 眼球）+ 次级物理（头发 / 双马尾 / 尾巴 / 裙子摆动，裙子与大腿碰撞）",
          "v7x": "诊断用，仅在 v7 跑动仍穿模时试：碰撞体半径放大一倍。站着时裙子若明显向外撑开，说明碰撞生效（只是不够大）；不撑开说明碰撞没起作用"}


def vanilla_sizes():
    game = acu_install.GAME = acu_install.find_game([])
    state = os.path.join(game, ".karin_acu_state.json")
    st = json.load(open(state)) if os.path.exists(state) else {"forges": {}}
    out = []
    for fg in acu_install.all_forges():
        size = st["forges"].get(fg, {}).get("size", os.path.getsize(os.path.join(game, fg)))
        out.append(f"{fg}\t{size}\n")
    return "".join(out).encode("utf-8")


def pack(payload, out, sizes):
    files = []
    for d, _, fs in os.walk(payload):
        files += [os.path.relpath(os.path.join(d, f), payload) for f in fs]
    files.sort(key=lambda p: (os.path.basename(p), p))  # the same data file of every forge side by side
    with tarfile.open(out, "w:xz", preset=9 | lzma.PRESET_EXTREME) as t:
        for p in files:
            if p != "vanilla_sizes.tsv":
                t.add(os.path.join(payload, p), arcname="payload/" + p.replace(os.sep, "/"))
        ti = tarfile.TarInfo("payload/vanilla_sizes.tsv")
        ti.size = len(sizes)
        t.addfile(ti, io.BytesIO(sizes))
    return len(files)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_zip")
    ap.add_argument("payloads", nargs="+", metavar="label=payload_dir", help="build_mod.py <out_dir>/payload folders")
    args = ap.parse_args()
    out = os.path.abspath(args.out_zip)
    items = [a.split("=", 1) for a in args.payloads]
    if any(len(i) != 2 for i in items):
        ap.error("payloads are label=payload_dir")
    sizes = vanilla_sizes()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_STORED) as z:
        installs = []
        for label, payload in items:
            name = f"payload_{label}.tar.xz"
            n = pack(payload, os.path.join(tmp, name), sizes)
            z.write(os.path.join(tmp, name), name)
            z.writestr(f"install_{label}.cmd", CMD.format(args=f'install "{name}"').replace("\n", "\r\n"))
            installs.append(f"  install_{label}.cmd  安装 {label}：{LABELS.get(label, label)}")
            print(f"{label}: {n} files -> {name} {os.path.getsize(os.path.join(tmp, name)):,} bytes")
        z.write(os.path.join(HERE, "acu_install.py"), "acu_install.py")
        z.writestr("uninstall.cmd", CMD.format(args="uninstall").replace("\n", "\r\n"))
        z.writestr("status.cmd", CMD.format(args="status").replace("\n", "\r\n"))
        z.writestr("README.txt", ("\ufeff" + README.format(installs="\n".join(installs))).replace("\n", "\r\n").encode("utf-8"))
    os.replace(out + ".tmp", out)
    print("RELEASE_OK", out, f"{os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
