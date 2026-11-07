"""Pose a TotkMdl Head export with TotK face-anim frames (LBS) for rendering.
usage: python face_preview.py <head_export.json> <out_dir> [anim:frame ...]
Writes face_<anim>_<frame>.json (Head model only) for blender_preview.py.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import face_anim as fa


def main(src, out_dir, specs):
    sk = fa.Skeleton()
    A = {a['name']: a for a in fa.load_face_anims()}
    os.makedirs(out_dir, exist_ok=True)
    for spec in specs:
        an, t = spec.rsplit(':', 1)
        S = fa.pose(sk, A[an], int(t)) if an != 'rest' else {}
        d = json.load(open(src, encoding='utf-8'))
        for mdl in d['models']:
            for s in mdl['shapes']:
                P = np.c_[np.array(s['pos']), np.ones(len(s['pos']))]
                out = np.zeros((len(P), 3))
                for v, (names, ws) in enumerate(zip(s['boneNames'], s['boneWeights'])):
                    acc = np.zeros(3); tot = 0.0
                    for n, w in zip(names, ws):  # signed weights (v5 blink) are valid; they sum to 1
                        if w == 0: continue
                        M = S.get(n)
                        acc += w * ((M @ P[v])[:3] if M is not None else P[v, :3]); tot += w
                    out[v] = acc / tot if tot > 0 else P[v, :3]
                s['pos'] = out.tolist()
        p = os.path.join(out_dir, f'face_{an}_{t}.json')
        json.dump(d, open(p, 'w')); print('posed', p)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('head_export'); ap.add_argument('out_dir')
    ap.add_argument('specs', nargs='*', help='anim:frame, or rest:0')
    a = ap.parse_args()
    main(a.head_export, a.out_dir, a.specs)
