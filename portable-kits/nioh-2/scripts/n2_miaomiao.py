# SPDX-License-Identifier: MIT
"""仁王2妙妙换装器 — 把存档里当前穿着的五件护甲的外观改成 KarinN2 Mod 对应的隼套装。

效果等同于在铁匠处用「外观变更」把五件护甲的外观换成隼套装，但不要求拿到过这几件装备。
只改存档，不含游戏文件或 Mod 资源。存档格式（仁王2 Complete Edition PC，SAVEDATA.BIN 0x296F28 字节）：
- 加密与仁王1 相同：AES-128-CTR（自定义 S 盒），算法与密钥块出自 pawREP 的 Nioh Savedata Decryption Tool（MIT）。
  文件头 0x148 字节用固定密钥，解密后以 NIOHUSR 开头；存档体的子密钥在解密后的头里 0x40 起。
- 明文是固定布局（偏移与 alfizari/Nioh-2-Save-Editor 一致）：装备区 0xED508 起 700 格 × 0x90 字节，
  每格 +0 = 物品 ID，+2 = 外观 ID（外观变更写的就是这里，没变更时等于 +0），两个 ID 都按大端读；
  装备表 0x1CC510 = 11 个 u32 装备区格号：近战 ×2、头、胴、手、腰、脚、饰品 ×2、远程 ×2。
- 存档体有一段完整性校验，算法没有公开。社区编辑器的做法是把 4 个完整性检查标志
  （0x7B93C、0x7B9DA、0x7B9DC、0xED0A2）清零；本工具同样处理，只在确实要改外观时才清。

写回时不重新加密整个文件：CTR 下密文 = 明文 ⊕ 密钥流，所以只把改动字节的差量异或进原密文，其余字节一个不动。
"""

import csv
import ctypes
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from n2_armor import ARMOR

APP_NAME = "仁王2妙妙换装器"
VERSION = "0.1.0-preview"
GAME_EXE = "nioh2.exe"

SAVE_SIZE = 0x296F28
HEADER_SIZE = 0x148
BODY_SIZE = SAVE_SIZE - HEADER_SIZE
MAGIC = b"NIOHUSR\x00"
BODY_KEY_OFFSET = 0x40
LEVEL_OFFSET = 0x28                      # 存档头里的角色等级

GEAR_START, GEAR_SIZE, GEAR_SLOTS = 0xED508, 0x90, 700
EQUIP_TABLE, EQUIP_COUNT = 0x1CC510, 11
SLOTS = (("head", 2, "头"), ("torso", 3, "胴"), ("arms", 4, "手"), ("waist", 5, "腰"), ("feet", 6, "脚"))
INTEGRITY_FLAGS = (0x7B93C, 0x7B9DA, 0x7B9DC, 0xED0A2)

# KarinN2 Mod 做模型时测试存档里的护甲外观：Mod 按这五件的网格替换角色。
KARIN_TARGETS = {"head": 0x810E, "torso": 0x0C1F, "arms": 0x3F94, "waist": 0xA2EF, "feet": 0xAB9B}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- 加解密
# 自定义 S 盒与 148 字节密钥块：pawREP/Nioh-Savedata-Decryption-Tool（MIT，见 THIRD_PARTY_NOTICES）。
SBOX = bytes.fromhex(
    "1C2F0353A30149DAA6CDE08A19A704D4" "061ADA4908E2F6B29EE12249CE7B7E5E"
    "A0092A63AF49CE707B3C2380FA1747F2" "62626C5910CC299CB54658C74413E738"
    "D5AF2783D4D5A09EE3763B8504D9D698" "6066D47853EACA0E8D565344E2EFBDA9"
    "9B100AA11393F0430B7C398A47DFD3C5" "0E3431A6AE5AB8E7E63143C0AA0FE082"
    "124CD1DF8BA5AC70C53D1B8E93174D79" "4ECE63C4330E1457F0D8195B9B6171F2"
    "2B337EFD2C0BB62320B9D491199404A4" "30138AF1D005EC5EAC4AD4D6A5177FF9"
    "E5F60029D7932D5E2CF181A3B7633957" "C233872DA83F02CC08677460D8F0DA67"
    "40648755BB7FF210C90314B58066CB91" "F61F795888BC95C2065FE90932ED9B85")
ROOT_BLOB = bytes.fromhex(
    "5419313EF46BE424CDA7966FABF069CA" "000080BFEC3B9DA1460CDD33F3D258E0"
    "C09FC7D4F6EFDC70926F52D8F1BD5436" "A2CBACA399FCC8D2A961726BD78D15B8"
    "80ACA0B59AA0EE1E8BF5D9DA2C92AEB4" "9D92E079AA765531BCE302007AB9537F"
    "E260F5262B1E7DA75DD1BD84233BE432" "3303A481849897AB637A8225399FC073"
    "496394FDD8DEA8C8B03652CD07D6A20A" "F2008C62")
RCON = (0x8D, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)

_SB = np.frombuffer(SBOX, np.uint8)
_XT = np.array([((i << 1) ^ (0x1B if i & 0x80 else 0)) & 0xFF for i in range(256)], np.uint8)
_SHIFT = np.array([4 * ((c + r) % 4) + r for c in range(4) for r in range(4)])


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _flip_words(block):
    return b"".join(block[i:i + 4][::-1] for i in range(0, len(block), 4))


def _expand_key(key):
    """tiny-AES 的密钥扩展，但输入密钥按 32 位字反序装入（与游戏一致）。"""
    rk = bytearray(176)
    for i in range(4):
        rk[4 * i:4 * i + 4] = key[4 * i:4 * i + 4][::-1]
    for i in range(4, 44):
        t = list(rk[4 * (i - 1):4 * i])
        if i % 4 == 0:
            t = [SBOX[b] for b in t[1:] + t[:1]]
            t[0] ^= RCON[i // 4]
        for j in range(4):
            rk[4 * i + j] = rk[4 * (i - 4) + j] ^ t[j]
    return np.frombuffer(bytes(rk), np.uint8).reshape(11, 16)


def _encrypt_blocks(blocks, key):
    rk = _expand_key(key)
    s = blocks ^ rk[0]
    for r in range(1, 11):
        s = _SB[s][:, _SHIFT]
        if r < 10:
            a = s.reshape(-1, 4, 4)
            a0, a1, a2, a3 = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
            t = a0 ^ a1 ^ a2 ^ a3
            m = np.empty_like(a)
            m[:, :, 0] = a0 ^ _XT[a0 ^ a1] ^ t
            m[:, :, 1] = a1 ^ _XT[a1 ^ a2] ^ t
            m[:, :, 2] = a2 ^ _XT[a2 ^ a3] ^ t
            m[:, :, 3] = a3 ^ _XT[a3 ^ a0] ^ t
            s = m.reshape(-1, 16)
        s = s ^ rk[r]
    return s


def _aes_block(block, key):
    return _encrypt_blocks(np.frombuffer(block, np.uint8).reshape(1, 16), key).tobytes()


def _counters(iv, start, count):
    """128 位大端计数器 iv+start … iv+start+count-1。"""
    v = (int.from_bytes(iv, "big") + start) % (1 << 128)
    hi0, lo0 = v >> 64, v & ((1 << 64) - 1)
    lo = np.uint64(lo0) + np.arange(count, dtype=np.uint64)
    hi = np.uint64(hi0) + (lo < np.uint64(lo0)).astype(np.uint64)
    out = np.empty((count, 2), ">u8")
    out[:, 0], out[:, 1] = hi, lo
    return out.view(np.uint8).reshape(count, 16)


def _keystream(key, iv, nbytes, chunk=1 << 16):
    n = (nbytes + 15) // 16
    out = np.empty((n, 16), np.uint8)
    for s in range(0, n, chunk):
        e = min(n, s + chunk)
        out[s:e] = _encrypt_blocks(_counters(iv, s, e - s), key)
    return out.reshape(-1)[:nbytes]


def _root_pair(kind):
    r = ROOT_BLOB
    buf = bytearray(32)
    for i in range(4):
        if kind == "header":
            c1, c2, c3, c4 = r[8 + i], r[0 + i], r[12 + i], r[4 + i]
            buf[0 + i], buf[4 + i] = c1 ^ r[20 + i], c2 ^ r[24 + i]
            buf[8 + i], buf[12 + i] = c3 ^ r[28 + i], c4 ^ r[32 + i]
            buf[16 + i], buf[20 + i] = c1 ^ r[36 + i], c2 ^ r[40 + i]
            buf[24 + i], buf[28 + i] = c3 ^ r[44 + i], c4 ^ r[48 + i]
        else:
            c1, c2, c3, c7 = r[0 + i], r[8 + i], r[12 + i], r[4 + i]
            c4, c5, c6 = r[56 + i], r[52 + i], r[60 + i]
            buf[0 + i], buf[4 + i] = c2 ^ r[68 + i], c1 ^ r[72 + i]
            buf[8 + i], buf[12 + i] = c3 ^ r[76 + i], c7 ^ r[80 + i]
            buf[16 + i], buf[20 + i] = c2 ^ c5, c1 ^ c4
            buf[24 + i], buf[28 + i] = c3 ^ c6, c7 ^ r[64 + i]
    if kind == "header":
        key, iv = bytes(buf[:16]), bytes(buf[16:])
    else:
        iv, key = bytes(buf[:16]), bytes(buf[16:])
    return _flip_words(key), iv


def _sub_keys(kind, clear_header=None):
    root_key, root_iv = _root_pair(kind)
    if kind == "header":
        r = ROOT_BLOB
        k1, iv1, k2, iv2 = r[84:100], r[116:132], r[100:116], r[132:148]
    else:
        assert clear_header is not None
        h = clear_header[BODY_KEY_OFFSET:BODY_KEY_OFFSET + 64]
        k1, iv1, k2, iv2 = h[0:16], h[16:32], h[32:48], h[48:64]
    out = _aes_block(root_iv, root_key)
    k1, iv1 = _flip_words(_xor(k1, out)), _xor(iv1, out)
    out = _aes_block(iv1, k1)
    k2, iv2 = _flip_words(_xor(k2, out)), _xor(iv2, out)
    return k1, iv1, k2, iv2


def _double_stream(keys, nbytes):
    k1, iv1, k2, iv2 = keys
    return _keystream(k2, iv2, nbytes) ^ _keystream(k1, iv1, nbytes)


def header_keystream(nbytes=HEADER_SIZE):
    return _double_stream(_sub_keys("header"), nbytes)


def decrypt(cipher):
    """返回明文（bytes）。只检查长度和文件头，其余由 validate() 检查。"""
    require(len(cipher) == SAVE_SIZE, "不支持的存档大小，未执行修改。")
    c = np.frombuffer(cipher, np.uint8)
    header = (c[:HEADER_SIZE] ^ header_keystream()).tobytes()
    require(header[:8] == MAGIC, "不是支持的仁王2角色存档（解密后文件头不符）。")
    body = c[HEADER_SIZE:] ^ _double_stream(_sub_keys("body", header), BODY_SIZE)
    return header + body.tobytes()


def encrypt(plain):
    """decrypt() 的逆运算（测试用；写回存档走 make_candidate 的异或差量）。"""
    require(len(plain) == SAVE_SIZE and plain[:8] == MAGIC, "明文格式不符。")
    p = np.frombuffer(plain, np.uint8)
    header = p[:HEADER_SIZE] ^ header_keystream()
    body = p[HEADER_SIZE:] ^ _double_stream(_sub_keys("body", plain[:HEADER_SIZE]), BODY_SIZE)
    return header.tobytes() + body.tobytes()


# ---------------------------------------------------------------- 存档结构
def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def be16(data, offset):
    return struct.unpack_from(">H", data, offset)[0]


def item_name(value):
    entry = ARMOR.get(value)
    return entry[1] if entry else f"物品 0x{value:04X}"


def validate(plain):
    """严格检查已知布局；返回存档信息和五个护甲部位（装备区格号、物品、外观）。"""
    require(len(plain) == SAVE_SIZE, "不支持的存档大小。")
    require(plain[:8] == MAGIC, "不是支持的仁王2角色存档。")
    require(u32(plain, 0x14) == HEADER_SIZE and u32(plain, 0x18) == BODY_SIZE, "存档头结构不匹配。")
    for off in INTEGRITY_FLAGS:
        require(plain[off] in (0, 1), "完整性标志位置的数据不符，存档版本不受支持。未执行修改。")
    table = struct.unpack_from(f"<{EQUIP_COUNT}I", plain, EQUIP_TABLE)
    slots, known = {}, 0
    for slot, index, label in SLOTS:
        cell = table[index]
        require(cell < GEAR_SLOTS, f"{label}部位没有穿护甲。请先在游戏里给五个部位都穿上护甲（任意一件），存档后再用本工具。")
        base = GEAR_START + GEAR_SIZE * cell
        item, look = be16(plain, base), be16(plain, base + 2)
        require(item != 0, f"{label}部位没有穿护甲。请先在游戏里给五个部位都穿上护甲（任意一件），存档后再用本工具。")
        kind = ARMOR.get(item, (None,))[0]
        require(kind in (None, slot), "装备表与已知格式不符（部位和物品类型对不上），存档版本不受支持。未执行修改。")
        known += kind == slot
        slots[slot] = {"cell": cell, "offset": base + 2, "item": item, "look": look}
    require(known >= 3, "装备表里的物品大多无法识别，存档版本不受支持。未执行修改。")
    return {
        "account": u32(plain, 0x10),
        "saved_at": u32(plain, 0x20),
        "level": u32(plain, LEVEL_OFFSET),
        "slots": slots,
        "flags": [plain[off] for off in INTEGRITY_FLAGS],
    }


def plan(info, mode="karin"):
    """要写的外观值：{明文偏移: (旧值, 新值, 部位)}。mode = karin（隼套装外观）/ clear（取消外观变更）。"""
    wanted = {}
    for slot, _, label in SLOTS:
        s = info["slots"][slot]
        target = KARIN_TARGETS[slot] if mode == "karin" else s["item"]
        if s["look"] != target:
            wanted[s["offset"]] = (s["look"], target, label)
    return wanted


def make_candidate(cipher, mode="karin"):
    """返回 (新密文, 改动列表, 改变的字节数)。只允许改五个外观字段和 4 个完整性标志。"""
    plain = decrypt(cipher)
    info = validate(plain)
    changes = plan(info, mode)
    new = bytearray(plain)
    allowed = set()
    report = []
    for off, (old, value, label) in sorted(changes.items()):
        struct.pack_into(">H", new, off, value)
        allowed.update((off, off + 1))
        report.append({"slot": label, "before": f"0x{old:04X}", "after": f"0x{value:04X}",
                       "before_name": item_name(old), "after_name": item_name(value)})
    if changes:
        for off in INTEGRITY_FLAGS:
            new[off] = 0
            allowed.add(off)
    new = bytes(new)
    delta = np.frombuffer(plain, np.uint8) ^ np.frombuffer(new, np.uint8)
    output = (np.frombuffer(cipher, np.uint8) ^ delta).tobytes()

    changed = set(np.flatnonzero(np.frombuffer(cipher, np.uint8) != np.frombuffer(output, np.uint8)).tolist())
    require(changed <= allowed, "内部校验失败：修改超出外观字段。")
    check = decrypt(output)
    require(check == new, "内部校验失败：重新解密结果不一致。")
    after = validate(check)
    require({k: after[k] for k in ("account", "saved_at", "level")} ==
            {k: info[k] for k in ("account", "saved_at", "level")}, "角色信息意外变化。")
    require(plan(after, mode) == {}, "内部校验失败：写入后外观仍不符。")
    return output, report, len(changed)


def describe(cipher):
    plain = decrypt(cipher)
    info = validate(plain)
    lines = []
    for slot, _, label in SLOTS:
        s = info["slots"][slot]
        mark = "  ← Karin 需要的外观" if s["look"] == KARIN_TARGETS[slot] else ""
        lines.append(f"{label}：{item_name(s['item'])}　外观：{item_name(s['look'])}{mark}")
    done = all(info["slots"][slot]["look"] == KARIN_TARGETS[slot] for slot, _, _ in SLOTS)
    lines.append("")
    lines.append("五个部位都已是 Karin 需要的外观。" if done else "还有部位不是 Karin 需要的外观。")
    return info, lines


# ---------------------------------------------------------------- 文件操作（与浪人、仁王3 妙妙换装器相同的安全流程）
def ensure_game_closed():
    require(os.name == "nt", "此发行版仅支持 Windows。")
    tasklist = Path(os.environ["SystemRoot"]) / "System32" / "tasklist.exe"
    result = subprocess.run(
        [str(tasklist), "/FI", f"IMAGENAME eq {GAME_EXE}", "/FO", "CSV", "/NH"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=15, check=True)
    text = result.stdout.decode("mbcs", errors="replace")
    for row in csv.reader(io.StringIO(text)):
        if row and row[0].casefold() == GAME_EXE:
            raise RuntimeError("请先保存进度并退出《仁王2》，再执行修改。")


def read_target(path):
    require(path.name.casefold() == "savedata.bin" and path.parent.name.upper() != "SYSTEMSAVEDATA00",
            "请选择角色存档 SAVEDATA00（或 01…）里的 SAVEDATA.BIN，不要选择 BACKUP.BIN 或系统存档。")
    data = path.read_bytes()
    validate(decrypt(data))
    return data


def commit(path, original, output, action, changes):
    """先备份并验证，再以同目录临时文件替换；覆盖前复查源文件。"""
    ensure_game_closed()
    require(path.read_bytes() == original, "存档已变化，请重新选择最新存档。")
    validate(decrypt(output))

    backup_dir = path.parent / "MiaomiaoBackups"
    backup_dir.mkdir(exist_ok=True)
    stem = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    backup = backup_dir / f"{stem}.original.bin"
    manifest = backup_dir / f"{stem}.json"
    with backup.open("xb") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    require(backup.read_bytes() == original, "备份验证失败，未修改存档。")

    record = {
        "tool": APP_NAME, "version": VERSION, "action": action, "status": "prepared",
        "target": str(path.resolve()), "backup_file": backup.name,
        "before_sha256": sha256(original), "after_sha256": sha256(output), "changes": changes,
    }
    manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".miaomiao-", suffix=".tmp", dir=path.parent,
                                         delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        require(temp_path.read_bytes() == output, "临时文件验证失败。")
        ensure_game_closed()
        require(path.read_bytes() == original, "写入前发现存档已变化，已停止；备份仍保留。")
        os.replace(temp_path, path)
        temp_path = None
        require(path.read_bytes() == output, "写入后验证失败，请保留备份。")
        record["status"] = "verified"
        manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return manifest


def restore(path, manifest):
    record = json.loads(manifest.read_text(encoding="utf-8"))
    require(record.get("tool") == APP_NAME, "不是本工具创建的备份记录。")
    filename = record.get("backup_file", "")
    require(filename and Path(filename).name == filename, "备份文件名无效。")
    original = (manifest.parent / filename).read_bytes()
    require(sha256(original) == record.get("before_sha256"), "备份文件校验失败。")
    validate(decrypt(original))
    current = read_target(path)
    require(sha256(current) == record.get("after_sha256"),
            "当前存档已产生新进度、被同步或再次修改。\n为防止覆盖新进度，本工具不会直接回滚。")
    return commit(path, current, original, "restore", [])


def default_save_roots():
    docs = None
    if os.name == "nt":
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:   # 「文档」，含重定向
            docs = Path(buffer.value)
    return [(docs or Path.home() / "Documents") / "KoeiTecmo" / "NIOH2" / "Savedata"]


def find_saves(root):
    paths = list(root.glob("SAVEDATA.BIN")) + list(root.glob("SAVEDATA*/SAVEDATA.BIN"))
    paths += list(root.glob("*/SAVEDATA*/SAVEDATA.BIN"))
    return sorted({p.resolve() for p in paths if p.is_file() and p.parent.name.upper() != "SYSTEMSAVEDATA00"})


# ---------------------------------------------------------------- 命令行
def cli(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="n2_miaomiao", description=f"{APP_NAME} {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect", help="显示存档信息和五个护甲部位的外观")
    p.add_argument("save", type=Path)
    for name, helptext in (("apply", "改成 Karin 需要的隼套装外观"), ("clear", "取消五个部位的外观变更")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("save", type=Path)
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--out", type=Path, help="写到另一个文件（不动原存档）")
        g.add_argument("--in-place", action="store_true", help="直接改原存档（先备份）")
    p = sub.add_parser("restore", help="按本工具的备份记录恢复")
    p.add_argument("save", type=Path)
    p.add_argument("manifest", type=Path)
    a = ap.parse_args(argv)

    if a.cmd == "inspect":
        info, lines = describe(a.save.read_bytes())
        print(f"账号 {info['account']}  等级 {info['level']}  保存于 "
              f"{datetime.fromtimestamp(info['saved_at']):%Y-%m-%d %H:%M:%S}")
        print("\n".join(lines))
    elif a.cmd in ("apply", "clear"):
        original = read_target(a.save) if a.in_place else a.save.read_bytes()
        output, changes, count = make_candidate(original, "karin" if a.cmd == "apply" else "clear")
        for c in changes:
            print(f"{c['slot']}：{c['before_name']} → {c['after_name']}")
        print(f"{len(changes)} 项，{count} 字节")
        if not changes:
            return 0
        if a.in_place:
            print("备份记录:", commit(a.save, original, output, a.cmd, changes))
        else:
            a.out.write_bytes(output)
            print("已写出", a.out)
    elif a.cmd == "restore":
        print("恢复完成，备份记录:", restore(a.save, a.manifest))
    return 0


# ---------------------------------------------------------------- 图形界面
def run_gui(smoke_out=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"{APP_NAME}  {VERSION}")
            self.geometry("900x620")
            self.minsize(780, 520)
            self.paths = {}
            ttk.Label(self, text=APP_NAME, font=("Microsoft YaHei UI", 20, "bold")).pack(
                anchor="w", padx=20, pady=(18, 6))
            ttk.Label(self, text="把当前穿着的五件护甲的外观改成 KarinN2 Mod 需要的隼套装｜自动备份｜不改装备、属性和进度"
                      ).pack(anchor="w", padx=20)

            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=20, pady=12)
            ttk.Button(bar, text="查找默认存档", command=self.scan_default).pack(side="left")
            ttk.Button(bar, text="选择存档文件", command=self.choose_file).pack(side="left", padx=8)
            ttk.Button(bar, text="选择存档目录", command=self.choose_folder).pack(side="left")

            self.tree = ttk.Treeview(self, columns=("slot", "level", "date", "account"), show="headings",
                                     selectmode="browse", height=6)
            for key, text, width in (("slot", "存档", 220), ("level", "等级", 60),
                                     ("date", "存档内保存时间", 180), ("account", "账号 ID", 200)):
                self.tree.heading(key, text=text)
                self.tree.column(key, width=width)
            self.tree.pack(fill="x", padx=20)
            self.tree.bind("<<TreeviewSelect>>", self.selection_changed)

            self.detail = tk.Text(self, height=11, wrap="none", font=("Microsoft YaHei UI", 10))
            self.detail.pack(fill="both", expand=True, padx=20, pady=10)
            self.detail.configure(state="disabled")

            acts = ttk.Frame(self)
            acts.pack(fill="x", padx=20)
            ttk.Button(acts, text="改为 Karin 外观", command=lambda: self.apply("karin")).pack(side="left")
            ttk.Button(acts, text="取消外观变更", command=lambda: self.apply("clear")).pack(side="left", padx=10)
            ttk.Button(acts, text="从工具备份恢复", command=self.undo).pack(side="left")

            self.status = tk.StringVar(value="请选择要修改的存档。")
            ttk.Label(self, textvariable=self.status, wraplength=850).pack(anchor="w", padx=20, pady=8)
            ttk.Label(self, text="不包含 KarinN2 Mod，需自行安装。只改头、胴、手、腰、脚五件护甲的外观，武器外观不动；"
                      "五个部位都要穿着护甲。使用前请在神社存档并退出游戏。", wraplength=850).pack(anchor="w", padx=20, pady=(0, 14))
            self.after(100, self.scan_default)

        def set_detail(self, text):
            self.detail.configure(state="normal")
            self.detail.delete("1.0", "end")
            self.detail.insert("end", text)
            self.detail.configure(state="disabled")

        def populate(self, paths):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.paths.clear()
            rows, rejected = [], 0
            for path in paths:
                try:
                    info = validate(decrypt(path.read_bytes()))
                    rows.append((info["saved_at"], path, info))
                except (OSError, ValueError, struct.error):
                    rejected += 1
            for _, path, info in sorted(rows, key=lambda r: r[0], reverse=True):
                when = datetime.fromtimestamp(info["saved_at"]).strftime("%Y-%m-%d %H:%M:%S")
                item = self.tree.insert("", "end", values=(f"{path.parent.parent.name}/{path.parent.name}",
                                                           info["level"], when, info["account"]))
                self.paths[item] = path
            self.status.set(f"找到 {len(rows)} 个可修改的存档，按保存时间排序。不支持、不可读或部位没穿护甲：{rejected} 个。"
                            "请明确选择一项。")
            self.set_detail("")

        def scan_default(self):
            paths = []
            for root in default_save_roots():
                if root.is_dir():
                    paths += find_saves(root)
            self.populate(paths)

        def choose_folder(self):
            folder = filedialog.askdirectory(title="选择 Savedata 目录或账号目录")
            if folder:
                self.populate(find_saves(Path(folder)))

        def choose_file(self):
            name = filedialog.askopenfilename(title="选择角色存档 SAVEDATA.BIN",
                                              filetypes=[("角色存档", "SAVEDATA.BIN"), ("BIN 文件", "*.BIN")])
            if name:
                try:
                    read_target(Path(name))
                    self.populate([Path(name)])
                    self.tree.selection_set(self.tree.get_children()[0])
                except Exception as error:
                    messagebox.showerror(APP_NAME, str(error))

        def selected(self):
            items = self.tree.selection()
            require(bool(items), "请先选择要处理的存档。")
            return self.paths[items[0]]

        def selection_changed(self, _event=None):
            items = self.tree.selection()
            if not items:
                return
            path = self.paths[items[0]]
            try:
                _, lines = describe(path.read_bytes())
                self.set_detail(str(path) + "\n\n" + "\n".join(lines))
            except Exception as error:
                self.set_detail(f"{path}\n\n{error}")

        def apply(self, mode):
            try:
                path = self.selected()
                ensure_game_closed()
                original = read_target(path)
                output, changes, count = make_candidate(original, mode)
                if not changes:
                    messagebox.showinfo(APP_NAME, "外观已经是目标设置，无需修改。")
                    return
                text = "\n".join(f"{c['slot']}：{c['before_name']} → {c['after_name']}" for c in changes)
                if not messagebox.askyesno(APP_NAME, f"将修改 {len(changes)} 个部位的外观，共 {count} 字节：\n\n{text}\n\n"
                                           "同时关闭存档的完整性检查（与社区存档编辑器相同的做法）。\n"
                                           f"会先创建备份，其他存档数据保持不变。\n\n目标：{path}\n\n确认执行？"):
                    return
                record = commit(path, original, output, mode, changes)
                self.selection_changed()
                messagebox.showinfo(APP_NAME, f"已写入并校验。\n备份记录：\n{record}\n\n"
                                    "请在游戏中加载刚才选择的存档。本工具只校验文件数据，不自动验证游戏画面。")
            except Exception as error:
                messagebox.showerror(APP_NAME, str(error))

        def undo(self):
            try:
                path = self.selected()
                ensure_game_closed()
                name = filedialog.askopenfilename(title="选择本工具的备份记录 JSON",
                                                  initialdir=str(path.parent / "MiaomiaoBackups"),
                                                  filetypes=[("备份记录", "*.json")])
                if not name or not messagebox.askyesno(APP_NAME, f"将恢复所选备份至：\n{path}\n\n确认恢复？"):
                    return
                record = restore(path, Path(name))
                self.selection_changed()
                messagebox.showinfo(APP_NAME, f"已恢复并校验。\n恢复前状态也已备份：\n{record}")
            except Exception as error:
                messagebox.showerror(APP_NAME, str(error))

    app = App()
    if smoke_out:
        def finish():
            Path(smoke_out).write_text(json.dumps({"gui": "ok", "version": VERSION,
                                                   "detected_saves": len(app.paths)}), encoding="utf-8")
            app.destroy()
        app.after(2500, finish)
    app.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        run_gui(sys.argv[2])
    elif len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    else:
        run_gui()
