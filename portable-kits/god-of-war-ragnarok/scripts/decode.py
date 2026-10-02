import struct, math
from mesh import DT_SIZE
def r10(u):
    x=(u&1023); y=(u>>10)&1023; z=(u>>20)&1023; w=u>>30
    return ((x-511)/512.0,(y-511)/512.0,(z-511)/512.0,w/3.0)
def decode(m, buf, base=0):
    """buf: bytes containing the mesh's buffers; offsets relative to base."""
    V = m.vcount
    out = {}
    for (pt, dt, n, co, bi) in m.comps:
        st = m.strides[bi]; bo = base + m.buf_offs[bi] + co
        vals = []
        for v in range(V):
            p = bo + st*v
            if dt == 0: vals.append(struct.unpack_from('<%df'%n, buf, p))
            elif dt == 3: vals.append(tuple(r10(struct.unpack_from('<I', buf, p+4*k)[0]) for k in range(n)))
            elif dt == 6: vals.append(tuple(x/65535.0 for x in struct.unpack_from('<%dH'%n, buf, p)))
            elif dt == 7: vals.append(tuple(x/32767.0 for x in struct.unpack_from('<%dh'%n, buf, p)))
            elif dt == 8: vals.append(struct.unpack_from('<%dB'%n, buf, p))
            elif dt == 4: vals.append(struct.unpack_from('<%dH'%n, buf, p))
            elif dt == 2: vals.append(struct.unpack_from('<%dI'%n, buf, p))
            elif dt == 1: vals.append(struct.unpack_from('<%dH'%n, buf, p))
            else: vals.append(None)
        out[(pt, dt, n)] = vals
    istr = m.ind_stride
    fmt = '<H' if istr == 2 else '<I'
    ib = base + m.ind_off
    idx = [struct.unpack_from(fmt, buf, ib + istr*k)[0] for k in range(m.icount)]
    return out, idx
def pos_of(out):
    for k,v in out.items():
        if k[0]==0: return v
def uv_of(out, which=3):
    for k,v in out.items():
        if k[0]==which: return v
def write_obj(path, meshes):
    with open(path,'w') as f:
        vb=1
        for name, pos, uv, idx in meshes:
            f.write(f'o {name}\n')
            for p in pos: f.write('v %f %f %f\n'%tuple(p[:3]))
            if uv:
                for t in uv: f.write('vt %f %f\n'%(t[0],1-t[1]))
            for k in range(0,len(idx)-2,3):
                a,b,c=idx[k]+vb,idx[k+1]+vb,idx[k+2]+vb
                f.write(f'f {a}/{a} {b}/{b} {c}/{c}\n' if uv else f'f {a} {b} {c}\n')
            vb+=len(pos)

def unpack_joints(words):
    """10x11-bit MSB-first bitstream packed in 4 u32."""
    bits = 0
    for w in words: bits = (bits << 32) | w
    total = 32*len(words)
    n = (len(words)-1)*3 + 1
    return [(bits >> (total - 11*(k+1))) & 2047 for k in range(n)]

def unpack_weights(words):
    ws = []
    for w in words:
        ws += [(w & 1023)/1023.0, ((w>>10)&1023)/1023.0, ((w>>20)&1023)/1023.0]
    ws.append(max(0.0, 1.0 - sum(ws)))
    return ws

def skin_of(m, out):
    J = W = None
    for k, v in out.items():
        if k[0] == 9: J = (k, v)
        if k[0] == 10: W = (k, v)
    res = []
    jk, jv = J; wk, wv = W
    u16_joints = jk[1] == 2 and wk[1] == 2 and wk[2] == 2      # 7-influence layout: eight u16 joint slots
    for vi in range(m.vcount):
        if u16_joints: js = list(struct.unpack('<8H', struct.pack('<4I', *jv[vi])))[:7]
        elif jk[1] == 2: js = unpack_joints(jv[vi])
        else: js = list(jv[vi])
        if wk[1] == 2: ws = unpack_weights(wv[vi])
        else:   # R10G10B10A2 unorm: decode() returned (x-511)/512, undo that
            ws = []
            for t in wv[vi]: ws += [round(c * 512 + 511) / 1023.0 for c in t[:3]]
            ws.append(max(0.0, 1-sum(ws)))
        res.append(list(zip(js, ws)))
    return res
