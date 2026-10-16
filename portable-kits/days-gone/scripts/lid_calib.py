"""Eyelid calibration for blink_amp.py: where Deacon's lid joints sit with the eyes open and closed.

New file for the portable kit (no project original). It reproduces the one-off command the project ran in a session to
write runs/t28/lid_calib.json (= configs/lid_calib_t28.json). Deacon's neutral face mood
(Animation/Deacon/facial/FaceMoods/dcn_face_neutral) blinks. Per lid joint the translation offsets from his reference
pose (misc/dcn_ref_pose, frame 0) are taken over every frame of the mood: "open" = the per-axis median, "closed" = the
frame where the joint is lowest along Head X. Both anims are raw packages decoded with anim_pertrack.py (CUE4Parse
decodes these per-track compressed face anims as constant tracks); track bone indices map to names through DgExport's
skel JSON of deacon_master_Skeleton.

Defaults: --cache from DG_CACHE; --skeleton <cache>/deacon_master_Skeleton.deacon_master_Skeleton.skel.json; --anim and
--ref are taken relative to <cache>/anim/raw/animj/BendGame/Content/Animation/Deacon/ unless absolute; joints face_1544
(left lid) and face_1911 (right lid); --out lid_calib.json.
Output: {joint: {"open": [x, y, z], "closed": [x, y, z]}} in cm, the joint's parent (Head) space.
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim_pertrack as A
import dgpaths

JOINTS = ('face_1544', 'face_1911')
ANIM = 'facial/FaceMoods/dcn_face_neutral.uasset'
REF = 'misc/dcn_ref_pose.uasset'


def calib(names, neutral, ref, joints=JOINTS):
    """names: skeleton bone names (track bone_index -> name); neutral, ref: anim_pertrack.decode() results"""
    T = {names[t['bone_index']]: t['t'] for t in neutral['tracks']}
    R = {names[t['bone_index']]: t['t'][0] for t in ref['tracks']}
    out = {}
    for j in joints:
        d = T[j] - R[j]; x = d[:, 0]; op = np.median(d, axis=0); cl = d[np.argmin(x)]
        out[j] = {'open': op.tolist(), 'closed': cl.tolist()}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', help='cache root (default: the DG_CACHE environment variable)')
    ap.add_argument('--skeleton', help='DgExport skel JSON of deacon_master_Skeleton')
    ap.add_argument('--anim', default=ANIM, help='face mood to calibrate on (default %(default)s)')
    ap.add_argument('--ref', default=REF, help='reference pose anim (default %(default)s)')
    ap.add_argument('--joints', nargs='+', default=list(JOINTS), help='lid joints (default: %(default)s)')
    ap.add_argument('--out', default='lid_calib.json', help='output JSON (default %(default)s)')
    args = ap.parse_args(argv)

    def under(*parts):
        return os.path.join(args.cache, *parts) if args.cache else dgpaths.cache(*parts)

    def anim(p):
        return p if os.path.isabs(p) else under(*dgpaths.ANIM_DIR, p)

    skeleton = args.skeleton or under(dgpaths.SKEL_JSON)
    names = [b['name'] for b in json.load(open(skeleton, encoding='utf-8'))['bones']]
    out = calib(names, A.decode(anim(args.anim)), A.decode(anim(args.ref)), args.joints)
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)
    for j, v in out.items():
        print(j, 'open', np.round(v['open'], 3).tolist(), 'closed', np.round(v['closed'], 3).tolist())
    return out


if __name__ == '__main__':
    main()
