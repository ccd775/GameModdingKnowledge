"""Minimal numpy BC1 / BC4 / BC5 decoders (inspection only)."""
import numpy as np


def _565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.float64)


def bc1(data, w, h):
    bw, bh = max(1, w // 4), max(1, h // 4)
    a = np.frombuffer(data, np.uint8, count=bw * bh * 8).reshape(-1, 8)
    c0 = a[:, 0].astype(np.uint32) | (a[:, 1].astype(np.uint32) << 8)
    c1 = a[:, 2].astype(np.uint32) | (a[:, 3].astype(np.uint32) << 8)
    idx = a[:, 4:8].copy().view('<u4').reshape(-1)
    p0, p1 = _565(c0), _565(c1)
    four = c0 > c1
    pal = np.stack([p0, p1, np.where(four[:, None], (2 * p0 + p1) / 3, (p0 + p1) / 2),
                    np.where(four[:, None], (p0 + 2 * p1) / 3, 0)], 1)
    sel = (idx[:, None] >> (2 * np.arange(16))) & 3
    px = np.take_along_axis(pal, sel[:, :, None].repeat(3, 2), 1)
    return px.reshape(bh, bw, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 3)


def _bc4_block(a):
    r0, r1 = a[:, 0].astype(np.float64), a[:, 1].astype(np.float64)
    bits = np.zeros(len(a), np.uint64)
    for k in range(6):
        bits |= a[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    sel = ((bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)).astype(np.int64)
    pal = np.zeros((len(a), 8))
    pal[:, 0], pal[:, 1] = r0, r1
    gt = r0 > r1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(gt, ((7 - i) * r0 + i * r1) / 7, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(gt, pal[:, i + 1], ((5 - i) * r0 + i * r1) / 5)
    pal[:, 6] = np.where(gt, pal[:, 6], 0)
    pal[:, 7] = np.where(gt, pal[:, 7], 255)
    return np.take_along_axis(pal, sel, 1)


def bc4(data, w, h):
    bw, bh = max(1, w // 4), max(1, h // 4)
    a = np.frombuffer(data, np.uint8, count=bw * bh * 8).reshape(-1, 8)
    return _bc4_block(a).reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)


def bc5(data, w, h):
    bw, bh = max(1, w // 4), max(1, h // 4)
    a = np.frombuffer(data, np.uint8, count=bw * bh * 16).reshape(-1, 16)
    r = _bc4_block(a[:, :8]).reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)
    g = _bc4_block(a[:, 8:]).reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)
    return np.stack([r, g], -1)
