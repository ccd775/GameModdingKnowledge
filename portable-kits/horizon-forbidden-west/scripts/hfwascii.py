"""Reader/writer for id-daemon HFW XNALara-style .ascii meshes and skeletons (h2_pc_mi_091)."""
import numpy as np


def read_skeleton(path):
    L = open(path, encoding='utf-8').read().split('\n')
    n = int(L[0]); bones = []
    i = 1
    for _ in range(n):
        name = L[i].strip(); parent = int(L[i + 1]); v = [float(x) for x in L[i + 2].split()]
        bones.append(dict(name=name, parent=parent, pos=v[:3], quat=v[3:7]))
        i += 3
    return bones


def read_meshes(path, has_skeleton=False):
    """Returns (bones or None, meshes). Each mesh: name, nuv, textures[(name,uvidx)], pos,nrm,col,uv[list],bi,bw,faces."""
    L = open(path, encoding='utf-8').read().split('\n')
    i = 0
    bones = None
    if has_skeleton:
        nb = int(L[0]); i = 1; bones = []
        for _ in range(nb):
            v = [float(x) for x in L[i + 2].split()]
            bones.append(dict(name=L[i].strip(), parent=int(L[i + 1]), pos=v[:3], quat=v[3:7])); i += 3
    nm = int(L[i]); i += 1
    meshes = []
    for _ in range(nm):
        name = L[i].strip(); nuv = int(L[i + 1]); nt = int(L[i + 2]); i += 3
        texs = []
        for _ in range(nt):
            texs.append((L[i].strip(), int(L[i + 1]))); i += 2
        nv = int(L[i]); i += 1
        per = 5 + nuv
        block = L[i:i + nv * per]; i += nv * per
        pos = np.array([block[k * per].split() for k in range(nv)], float).reshape(nv, 3)
        nrm = np.array([block[k * per + 1].split() for k in range(nv)], float).reshape(nv, 3)
        col = np.array([block[k * per + 2].split() for k in range(nv)], int).reshape(nv, 4)
        uvs = [np.array([block[k * per + 3 + u].split() for k in range(nv)], float).reshape(nv, 2) for u in range(nuv)]
        bi_rows = [block[k * per + 3 + nuv].split() for k in range(nv)]
        bw_rows = [block[k * per + 4 + nuv].split() for k in range(nv)]
        nf = int(L[i]); i += 1
        faces = np.array([L[i + k].split() for k in range(nf)], int).reshape(nf, 3); i += nf
        meshes.append(dict(name=name, nuv=nuv, textures=texs, pos=pos, nrm=nrm, col=col, uv=uvs,
                           bi=[[int(x) for x in r] for r in bi_rows], bw=[[float(x) for x in r] for r in bw_rows],
                           faces=faces))
    return bones, meshes


def _f(x):
    return f'{x:.6f}'


def write(path, meshes, bones=None):
    out = []
    if bones is not None:
        out.append(str(len(bones)))
        for b in bones:
            out += [b['name'], str(b['parent']), ' '.join(_f(v) for v in b['pos']) + ' ' + ' '.join(f'{q:g}' for q in b['quat'])]
    out.append(str(len(meshes)))
    for m in meshes:
        out += [m['name'], str(m['nuv']), str(len(m['textures']))]
        for t, u in m['textures']:
            out += [t, str(u)]
        nv = len(m['pos'])
        out.append(str(nv))
        for k in range(nv):
            out.append(' '.join(_f(v) for v in m['pos'][k]))
            out.append(' '.join(_f(v) for v in m['nrm'][k]))
            out.append(' '.join(str(int(c)) for c in m['col'][k]))
            for u in range(m['nuv']):
                out.append(' '.join(_f(v) for v in m['uv'][u][k]))
            out.append(' '.join(str(int(b)) for b in m['bi'][k]))
            out.append(' '.join(f'{w:.6f}' for w in m['bw'][k]))
        out.append(str(len(m['faces'])))
        for f in m['faces']:
            out.append(f'{f[0]} {f[1]} {f[2]}')
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
