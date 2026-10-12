"""Generate the Karin_Original replacer script from the PicodraTech one (one code base, two mods).

reframework/karin_replacer.lua (Karin PicodraTech) -> karin_replacer_original.lua: own name, version, asset paths,
config file, pak name and API global; and it stays idle while the PicodraTech replacer is installed (both would take
the same character-build hooks and each hand over half a body).

usage: python make_original_lua.py --out <karin_replacer_original.lua> [--src <karin_replacer.lua>] [--check]
  --src defaults to this kit's reframework/karin_replacer.lua; --check: fail if --out is not what would be generated.
"""
import argparse
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SRC = KIT / "reframework/karin_replacer.lua"
OUT = None   # --out
VERSION = "1.0.1"

IDLE = '''
-- Only one Karin replacer can run: the PicodraTech one (karin_replacer.lua) takes the same character-build hooks, and
-- the two would each hand over half a body. While it is installed this one stays idle (karin_replacer.lua sorts
-- before this file, so it is normally loaded first; the check in decide() covers the other order).
local function other_replacer() return rawget(_G, "KarinReplacer") ~= nil end
if other_replacer() then
    log_info("idle: karin_replacer.lua (Karin PicodraTech) is installed; remove it to use this one")
    re.on_draw_ui(function()
        if imgui.tree_node(MOD .. " " .. VERSION) then
            imgui.text("Idle: the Karin PicodraTech replacer (karin_replacer.lua) is installed.")
            imgui.text("Only one Karin replacer can run: remove the other one's files to use this one.")
            imgui.tree_pop()
        end
    end)
    return
end
'''

SUBS = [
    ("-- Karin PicodraTech player replacer for Dragon's Dogma 2 (REFramework, TU3.2) -- v1.3.0\n",
     f"-- Karin (original outfit) player replacer for Dragon's Dogma 2 (REFramework, TU3.2) -- v{VERSION}\n"
     "-- Generated from karin_replacer.lua (Karin PicodraTech) by Scripts/make_original_lua.py: edit that one, not this.\n", 1),
    ("(resources in pak_mods/KarinPicodraTech.pak)", "(resources in pak_mods/KarinOriginal.pak)", 1),
    ('local MOD = "Karin Replacer"', 'local MOD = "Karin Original Replacer"', 1),
    ('local VERSION = "1.3.0"', f'local VERSION = "{VERSION}"', 1),
    ('"Character/_karin/karin_body.', '"Character/_karin_original/karin_original_body.', 3),
    ('local CFG_FILE = "karin_replacer/config.json"', 'local CFG_FILE = "karin_replacer_original/config.json"', 1),
    ('"resources missing (is pak_mods/KarinPicodraTech.pak installed?)"',
     '"resources missing (is pak_mods/KarinOriginal.pak installed?)"', 1),
    ('local function log_info(msg) log.info("[" .. MOD .. "] " .. msg) end\n',
     'local function log_info(msg) log.info("[" .. MOD .. "] " .. msg) end\n' + IDLE, 1),
    ('    if name ~= PLAYER_GO and name ~= MOCKUP_GO then return nil end\n',
     '    if name ~= PLAYER_GO and name ~= MOCKUP_GO then return nil end\n'
     '    if other_replacer() then return nil end   -- the PicodraTech replacer loaded after this one: it builds\n', 1),
    ("-- for other scripts (and testing): KarinReplacer.set_enabled(bool), KarinReplacer.set_option(name, bool),\n"
     "-- KarinReplacer.status();",
     "-- for other scripts (and testing): KarinOriginalReplacer.set_enabled(bool), KarinOriginalReplacer.set_option(name,\n"
     "-- bool), KarinOriginalReplacer.status();", 1),
    ("KarinReplacer = {", "KarinOriginalReplacer = {", 1),
    # her chains are tuned around her rest shape (see CHAIN_REST_POSE in the source)
    ("local CHAIN_REST_POSE = false", "local CHAIN_REST_POSE = true", 1),
]


def generate():
    s = SRC.read_text(encoding="utf-8")
    for old, new, n in SUBS:
        c = s.count(old)
        if c != n:
            raise SystemExit(f"expected {n}x, found {c}x: {old[:70]!r}")
        s = s.replace(old, new)
    for left in ("KarinPicodraTech.pak", '"Character/_karin/', "KarinReplacer = {"):
        if left in s:
            raise SystemExit(f"left over: {left}")
    return s


def main():
    global SRC, OUT
    ap = argparse.ArgumentParser(description="Generate karin_replacer_original.lua from karin_replacer.lua.")
    ap.add_argument("--out", required=True, help="generated script (karin_replacer_original.lua)")
    ap.add_argument("--src", default=str(SRC), help="PicodraTech script (default: this kit's reframework/karin_replacer.lua)")
    ap.add_argument("--check", action="store_true", help="only compare --out with what would be generated")
    a = ap.parse_args()
    SRC, OUT = Path(a.src), Path(a.out)
    s = generate()
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == s
        print("up to date" if ok else "OUT OF DATE")
        return 0 if ok else 1
    OUT.write_text(s, encoding="utf-8", newline="\n")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
