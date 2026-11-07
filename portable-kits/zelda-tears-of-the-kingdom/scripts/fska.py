"""Minimal reader for TotK (BFRES v10) skeletal animations (FSKA) + curve evaluation.

Layout (verified against Player_Demo_Animation / Player_Animation):
  FSKA (0x50): magic, flags u32, name u64, path u64, bindSkeleton u64, bindIndex u64, boneAnims u64, userData u64,
               userDataDict u64, frameCount u32, numCurve u32, bakedSize u32, numBoneAnim u16, numUserData u16
  BoneAnim (0x38): name u64, curves u64, baseData u64, u64, u64, flags u32, beginRotate u8, beginTranslate u8,
               numCurve u8, beginBaseTranslate u8, beginCurve u32, pad u32
  AnimCurve (0x30): frames u64, keys u64, flags u16, numKey u16, animDataOffset u32, start f32, end f32, scale f32,
               offset f32, delta f32, pad u32
Strings: u64 offset -> u16 length + ascii.
"""
import re, struct
import numpy as np

FRAME_FMT = {0: ('f', 4), 1: ('h', 2), 2: ('B', 1)}       # Single, Decimal10x5 (/32), Byte
KEY_FMT = {0: ('f', 4), 1: ('h', 2), 2: ('b', 1)}         # Single, Int16, SByte
ELEMS = {0: 4, 1: 2, 2: 1, 4: 1, 5: 1, 6: 1, 7: 1}        # cubic, linear, bakedFloat, stepInt, bakedInt, stepBool, bakedBool


class Reader:
    def __init__(self, data):
        self.d = data

    def s(self, off):
        if not off: return None
        n = struct.unpack_from('<H', self.d, off)[0]
        return self.d[off + 2: off + 2 + n].decode('ascii', 'replace')

    def curve(self, off):
        d = self.d
        fo, ko, fl, nk, ado, st, en, sc, of, de = struct.unpack_from('<QQHHIfffff', d, off)
        ft, kt, ct = fl & 3, (fl >> 2) & 3, (fl >> 4) & 7
        fc, fs = FRAME_FMT[ft]
        frames = np.array(struct.unpack_from('<%d%s' % (nk, fc), d, fo), float)
        if ft == 1: frames /= 32.0
        ne = ELEMS[ct]
        kc, ks = KEY_FMT[kt]
        keys = np.array(struct.unpack_from('<%d%s' % (nk * ne, kc), d, ko), float).reshape(nk, ne)
        return dict(offset=ado, type=ct, frames=frames, keys=keys, scale=sc, voff=of, delta=de, start=st, end=en)

    def anims(self, bone_filter=None):
        d = self.d
        out = []
        for m in re.finditer(b'FSKA', d):
            o = m.start()
            try:
                _, fl, nm, path, skel, bidx, bao, ud, udd, fc, ncv, baked, nb, nud = struct.unpack_from('<4sI7QIIIHH', d, o)
            except struct.error:
                continue
            if not (0 < bao < len(d)) or nb == 0 or nb > 1024: continue
            name = self.s(nm)
            bind = struct.unpack_from('<%dH' % nb, d, bidx) if bidx else None
            bones = []
            for i in range(nb):
                b = bao + i * 0x38
                bn, co, bd, _, _, bfl, br, bt, ncu, bbt, bc, _ = struct.unpack_from('<QQQQQIBBBBII', d, b)
                bname = self.s(bn)
                if bone_filter and not bone_filter(bname): continue
                curves = [self.curve(co + k * 0x30) for k in range(ncu)] if co else []
                # base data: present components in order scale(3), rotate(4), translate(3) as flagged
                base, p = {}, bd
                if bfl & (1 << 3): base['scale'] = struct.unpack_from('<3f', d, p); p += 12
                if bfl & (1 << 4): base['rotate'] = struct.unpack_from('<4f', d, p); p += 16
                if bfl & (1 << 5): base['translate'] = struct.unpack_from('<3f', d, p); p += 12
                bones.append(dict(name=bname, flags=bfl, base=base, curves=curves, bind=bind[i] if bind else None,
                                  beginRotate=br, beginTranslate=bt))
            out.append(dict(name=name, frames=fc, flags=fl, bones=bones))
        return out


def eval_curve(c, t):
    """Value of curve c at frame t (cubic/linear/baked), with scale/offset applied."""
    fr, k = c['frames'], c['keys']
    if len(fr) == 0: return c['voff']
    t = min(max(t, fr[0]), fr[-1])
    i = int(np.searchsorted(fr, t, side='right') - 1); i = max(0, min(i, len(fr) - 1))
    ct = c['type']
    if ct == 0:   # cubic hermite-ish coefficients: v = c0 + c1 u + c2 u^2 + c3 u^3, u in [0,1] over the segment
        f0 = fr[i]; f1 = fr[i + 1] if i + 1 < len(fr) else f0 + 1
        u = 0.0 if f1 == f0 else (t - f0) / (f1 - f0)
        c0, c1, c2, c3 = k[i]
        v = c0 + c1 * u + c2 * u * u + c3 * u ** 3
    elif ct == 1:
        f0 = fr[i]; f1 = fr[i + 1] if i + 1 < len(fr) else f0 + 1
        u = 0.0 if f1 == f0 else (t - f0) / (f1 - f0)
        v = k[i, 0] + k[i, 1] * u
    else:
        v = k[i, 0]
    return c['voff'] + v * c['scale']
