# Release package of a built profile: <release-dir>/<pak>/ (pak + sig + 安装说明.txt) and <release-dir>/<pak>_v<version>.zip.
# python package_release.py <profile> <version> <date> --out-root <dir> --release-dir <dir> [--game-dir <dir>]
#   pak/sig from <out-root>/<profile>/<pak>.pak|.sig (the cook_pak.ps1 outputs copied back from the UE machine).
#   --game-dir only fills the example path of the install text (default: SIFU_GAME_DIR, else a placeholder).
import argparse
import hashlib
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender"))   # profiles.py (no bpy)
import profiles

BS = chr(92)
GAME_DIR_PLACEHOLDER = "<Steam 库>" + BS + "steamapps" + BS + "common" + BS + "Sifu"
FAMILY = ("pakchunk99-KarinOriginal_P、pakchunk99-KarinOriginalPicodraTech_P、pakchunk99-KarinPicodraTech_P、"
          "pakchunk99-KarinUmbrella_P、pakchunk99-KarinY_P")
INFO = {
    "opt": ("Karin（Original 体型 + PicodraTech 服装）",
            ["双马尾、狐狸尾巴、侧发", "外套下摆 9 片（碰撞大腿）", "耳机线 2 根", "背后长飘带"], []),
    "pt": ("Karin（新版体型 + PicodraTech 服装）",
           ["及膝双马尾、大狐狸尾巴、侧发", "外套下摆 9 片（碰撞大腿）", "耳机线 2 根", "背后长飘带"], []),
    "umb": ("Karin Umbrella（新版体型 + 都市夹克、护目镜）",
            ["及膝双马尾、大狐狸尾巴、侧发", "两袖垂下的绳带"], []),
    "y": ("Karin Y（新版体型 + 月夜之舞和风服装）",
          ["及膝双马尾、大狐狸尾巴、侧发", "右臂长袖、袖上长带", "左后方长摆", "右侧两片腰摆", "前后腰布", "腰带垂饰"],
          ["源模型的两把苦无道具（左手握着的、嘴里叼着的）已去掉：空手格斗动作和表情动画会让它们穿模。"]),
}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(name, version, date, out_root, release_dir, game_dir=None):
    SIFU, OUT = release_dir, out_root
    game_dir = (game_dir or GAME_DIR_PLACEHOLDER).rstrip("/" + BS)
    P = profiles.activate(name)
    pak = P["pak"]
    title, physics, notes = INFO[name]
    dst = os.path.join(SIFU, pak)
    os.makedirs(dst, exist_ok=True)
    for ext in (".pak", ".sig"):
        shutil.copy2(f"{OUT}/{name}/{pak}{ext}", os.path.join(dst, pak + ext))
    sums = {ext: md5(os.path.join(dst, pak + ext)) for ext in (".pak", ".sig")}
    lines = [
        f"{title} → 师父 Sifu 女主默认服装",
        f"版本 v{version}（{date}）",
        "",
        "适用游戏：Sifu Steam 版 v_1.29（buildid 18739835）。游戏更新后，如果模型显示异常，需要用新版本重新制作。",
        "",
        "一、安装",
        "1. 先关闭游戏。",
        "2. 打开游戏目录下的 Sifu\\Content\\Paks\\ 文件夹，例如：",
        f"   {game_dir}\\Sifu\\Content\\Paks\\",
        "3. 如果里面没有 ~mods 文件夹，就新建一个（名字前面有波浪号）。",
        "4. 把下面两个文件一起复制进 ~mods：",
        f"   {pak}.pak",
        f"   {pak}.sig",
        "",
        "二、卸载",
        "关闭游戏，从 ~mods 里删掉上面两个文件。",
        "",
        "三、替换范围",
        "替换女主默认服装模型 SK_W_MainChar_01。",
        "同一模型也被女主的“复仇”“武德”两套服装，以及部分女性“分身”敌人使用，这些也会一起变成 Karin。",
        "",
        "四、内容",
        "- 模型、材质、贴图（源模型的贴图集，烘焙环境光遮蔽）",
        "- 表情：眨眼、口型、受击和发力表情（使用游戏自带的女主面部动画）",
        "- 眼球随注视方向转动",
        "- 骨骼物理：" + "；".join(physics),
        "",
        "五、注意",
        "- 这一组 Karin mod 都替换同一个模型，一次只装其中一个：",
        "  " + FAMILY + "。",
        "  也不要和旧版 pakchunk99-karin-BL-P 或其它替换女主默认服装的 mod 同时安装，否则会互相覆盖。",
        "- .sig 文件必须和 .pak 同名，并放在同一个文件夹里。",
    ] + [f"- {n}" for n in notes] + [
        "",
        "六、文件校验（MD5）",
        f"{pak}.pak  {sums['.pak']}",
        f"{pak}.sig  {sums['.sig']}",
        "",
    ]
    with open(os.path.join(dst, "安装说明.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines))
    z = os.path.join(SIFU, f"{pak}_v{version}.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in (pak + ".pak", pak + ".sig", "安装说明.txt"):
            zf.write(os.path.join(dst, fn), f"{pak}/{fn}")
    with zipfile.ZipFile(z) as zf:
        bad = zf.testzip()
    print("PACKAGED", dst, z, os.path.getsize(z), "testzip", bad, sums)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Release folder (pak, sig and the Chinese install text) and zip of a built variant profile.")
    ap.add_argument("profile", choices=sorted(INFO), help="profile name in profiles.py")
    ap.add_argument("version", help="release version, e.g. 1")
    ap.add_argument("date", help="release date for the install text, e.g. 2026-10-13")
    ap.add_argument("--out-root", required=True, help="folder holding <profile>/<pak>.pak and .sig")
    ap.add_argument("--release-dir", required=True, help="folder that receives <pak>/ and <pak>_v<version>.zip")
    ap.add_argument("--game-dir", default=os.environ.get("SIFU_GAME_DIR"),
                    help="Sifu install folder shown as the example in the install text (default: SIFU_GAME_DIR)")
    a = ap.parse_args()
    main(a.profile, a.version, a.date, a.out_root, a.release_dir, a.game_dir)
