"""Per-submesh table: vertex/index counts, material, shader, palette size, position bounds.
usage: g1m_subs.py <file.g1m>"""
import argparse
import sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('file', help='.g1m')
args = ap.parse_args()
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool as gt  # noqa: E402
from g1m_render import submesh_tris  # noqa: E402

m = gt.embedded_models(Path(args.file).read_bytes())[-1]
for s in m.submeshes:
    t = submesh_tris(m, s)
    b = '' if t is None or not len(t) else f'lo={np.round(t.reshape(-1,3).min(0),1).tolist()} hi={np.round(t.reshape(-1,3).max(0),1).tolist()}'
    print(f"sub{s['id']:3d} vb={s['vertex_buffer']} pal={s['palette']}({len(m.palettes[s['palette']]) if s['palette'] < len(m.palettes) else '-'}) "
          f"mat={s['material']} sh={s['shader']} v={s['vertex_count']} i={s['index_count']} flags={s['flags']:#x} hidden={gt.is_hidden(m, s)} {b}")
lod = m.section('MESH_LOD')
print('MESH_LOD', lod and {k: lod[k] for k in ('size', 'count')})
