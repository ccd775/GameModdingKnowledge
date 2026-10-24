"""Tangent-space normal map Y (green) convention check (2026-10-24).

  python normal_curl.py <normal.png> [...]

A normal map baked from a height field h has nx = -dh/du, ny = -dh/dv, so d(nx)/d(row) and d(ny)/d(col) are both the
mixed derivative of h up to sign: their correlation is about -1 when green points toward the image top (vanilla Odyssey
Kassandra body/head maps: -0.30 / -0.25) and +1 when it points toward the image bottom (Karin_PicodraTech Hair_Head
atlas: +0.78 -> build_mod.py flips G). Weave/detail patterns are not height fields and give ~0 (inconclusive).
Empty (black) atlas space and seams (|step| >= 0.5) are skipped.
"""
import argparse

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("png", nargs="+", help="tangent-space normal map(s)")
for f in ap.parse_args().png:
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    nx, ny = a[..., 0] / 127.5 - 1, a[..., 1] / 127.5 - 1
    valid = a.max(-1) > 10
    g1 = np.diff(nx, axis=0)[:, :-1]
    g2 = np.diff(ny, axis=1)[:-1, :]
    v = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:]
    g1, g2 = g1[v], g2[v]
    m = (np.abs(g1) < 0.5) & (np.abs(g2) < 0.5)
    print(f"{f}: {np.corrcoef(g1[m], g2[m])[0, 1]:+.3f}")
