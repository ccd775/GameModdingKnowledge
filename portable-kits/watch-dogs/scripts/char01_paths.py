"""Game paths of Aiden's default outfit (char01) that a character replacer overrides.

The diffuse/normal/specular textures exist as a low stream (<key>.xbt) and a high stream
(<key>_high.xbt); the shared eyelash texture has one stream.  FAT v8 names are the low 32 bits
of FNV-1 64 over the lower-case backslash path (see repack_fat8.path_hash).

  python char01_paths.py      lists every path with its FAT name hash
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repack_fat8 import path_hash  # noqa: E402

CHAR = "graphics/characters/char/char01/"
XBG = CHAR + "char01.xbg"
LASHES_KEY = "com_u_las_uni04_d"
LASHES = "graphics/characters/kits/common/unisex/lashes/" + LASHES_KEY + ".xbt"
# texture key -> (slot name, map kind); slots follow the char01 material table: head, coat, hair, lashes
TEXTURES = {
    "char01_head_v2_d2": ("head", "d"), "char01_head_v2_n": ("head", "n"), "char01_head_v2_s2": ("head", "s"),
    "char01_coat_d": ("coat", "d"), "char01_coat_e3_n": ("coat", "n"), "char01_coat_e3_s": ("coat", "s"),
    "char01_hair_v2_d": ("hair", "d"), "char01_hair_v2_n": ("hair", "n"), "char01_hair_v2_s": ("hair", "s"),
    LASHES_KEY: ("lashes", "d"),
}
SLOT_INDEX = {"head": 0, "coat": 1, "hair": 2, "lashes": 3}


def texture_paths(key: str) -> list[str]:
    """Low stream first, then the high stream when the texture has one."""
    if key == LASHES_KEY:
        return [LASHES]
    return [CHAR + key + ".xbt", CHAR + key + "_high.xbt"]


def stream_name(path: str) -> str:
    return path.rsplit("/", 1)[-1][: -len(".xbt")]


def texture_key(slot: str, kind: str) -> str | None:
    return next((k for k, v in TEXTURES.items() if v == (slot, kind)), None)


def main() -> None:
    argparse.ArgumentParser(description="List the char01 paths a replacer overrides, with their FAT name hashes.").parse_args()
    for path in [XBG] + [p for key in TEXTURES for p in texture_paths(key)]:
        print(f"{path_hash(path):08X}  {path}")


if __name__ == "__main__":
    main()
