"""Shift the absolute SkipOffsets of inline shader maps after an export moved inside its package.

UE4 serializes every shader of an inline shader map (material instances with a static permutation resource) as
FName ShaderType, int32 SkipOffset, body. SkipOffset is the archive position after the body, i.e. an absolute file
offset. The loader seeks to it, so when the header grows (new names or imports) the export moves and every
SkipOffset must move with it, or the game reads garbage ("Invalid BufferCount=0 ... Pos=<far past the end>").

Records are found by structure: (shader-type name, 0, SkipOffset) where SkipOffset points forward inside the export.
The records must form chains: each SkipOffset lands on the next record or on the end of a shader list, and the last
one lands exactly on the end of the export.
"""
import re, struct

SHADER_NAME = re.compile(r'(PS|VS|HS|DS|GS|CS)\b|(PS|VS)(<|_)|VS\w*DepthOutputDepth|Pipeline$')

def skip_records(pkg, i=0):
    """positions (relative to the export start) of the SkipOffset fields of export i"""
    e = pkg.exports[i]
    lo, hi = e['SerialOffset'], e['SerialOffset'] + e['SerialSize']
    d = pkg.data
    shaderish = {k for k, n in enumerate(pkg.names) if SHADER_NAME.search(n) or 'PS' in n or 'VS' in n}
    recs = []
    for pos in range(lo, hi - 12):
        idx, num, v = struct.unpack_from('<iii', d, pos)
        if idx in shaderish and num == 0 and pos + 12 < v <= hi:
            recs.append((pos, v))
    if not recs:
        return []
    starts = {p for p, _ in recs}
    ends = [v for _, v in recs if v not in starts]
    if max(v for _, v in recs) != hi:
        raise ValueError('shader records do not end at the export end (%d != %d)' % (max(v for _, v in recs), hi))
    # every record except the first of a list is the target of the previous one
    targets = {v for _, v in recs}
    heads = [p for p, _ in recs if p not in targets]
    if len(heads) > len(ends) + 1:
        raise ValueError('shader records do not form chains: %d heads, %d ends' % (len(heads), len(ends)))
    return [p + 8 - lo for p, _ in recs]

def fix(old_pkg, new_data):
    """new_data: old_pkg rewritten with unchanged export bytes; returns new_data with SkipOffsets shifted"""
    import upkg
    new = upkg.Package(new_data)
    out = bytearray(new_data)
    n = 0
    for i, (eo, en) in enumerate(zip(old_pkg.exports, new.exports)):
        delta = en['SerialOffset'] - eo['SerialOffset']
        if not delta:
            continue
        if en['SerialSize'] != eo['SerialSize']:
            raise ValueError('export %d changed size; SkipOffsets cannot be shifted blindly' % i)
        for rel in skip_records(old_pkg, i):
            pos = en['SerialOffset'] + rel
            struct.pack_into('<i', out, pos, struct.unpack_from('<i', out, pos)[0] + delta)
            n += 1
    return bytes(out), n
