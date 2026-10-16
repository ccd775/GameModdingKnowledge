"""Set the cooked rest pose of Karin's eyelid amplifier bones (Scripts/blink_rig.py) so that an AnimBP CopyBone node
(BCS_ParentBoneSpace, translation) on each lid bone turns Deacon's lid joint motion into the VRM blink.

Chain: Head -> KB_Amp_<side>_<axis> -> KB_Blink_<side>_<axis>. CopyBone writes the source joint's local translation
(Head space: Karin rest p + Deacon delta d, the face joints are AnimationRelative) into the lid bone's local translation,
i.e. into the amplifier's space. With the amplifier's local rotation R and scale S, the lid bone's Head-space position is
R S (p + d) + t, and its skinned vertices move R S (d - d_open) from the rest pose when the lid bone's rest translation is
p + d_open. R maps Head X onto minus the lid bone's half axis e, S = (M / travel, eps, eps): the lid joint's drop along
Head X (travel = open X - closed X of Deacon's neutral blink) gives s = 1 and moves the lid bone by M along e (blink_rig's
magnitude), Y/Z joint motion is damped to eps. t puts the lid bone's rest where the import had it. UE rebuilds the
inverse bind matrices from the ref pose at load (USkeletalMesh::CalculateInvRefMatrices, not serialized), so only the
local ref transforms change; every serialized copy of the ref pose array is patched.

usage: blink_amp.py <cooked mesh> <out mesh> <blink_rig.json> <lid_calib.json> [report.json]
"""
import argparse, json, struct, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import refskel
from abp_springs import quat_from_matrix

SOURCE = {"L": "face_1544", "R": "face_1911"}
EPS = 0.02


def basis_from_x(x):
    x = np.asarray(x, float); x /= np.linalg.norm(x)
    a = np.array([0, 0, 1.0]) if abs(x[2]) < 0.9 else np.array([0, 1.0, 0])
    y = np.cross(a, x); y /= np.linalg.norm(y); z = np.cross(x, y)
    return np.c_[x, y, z]


def main(src, dst, rig_json, calib_json, rep_json=None):
    data = bytearray(open(src, "rb").read())
    rs = refskel.read(src)
    N, P, L, C = rs["names"], rs["parents"], rs["local"], rs["component"]
    ix = {n: i for i, n in enumerate(N)}
    rig = json.load(open(rig_json)); cal = json.load(open(calib_json))
    po = rs["pose_offset"]
    arr = bytes(data[po:po + 40 * len(N)])
    copies = []
    o = data.find(arr)
    while o >= 0:
        copies.append(o); o = data.find(arr, o + 1)
    assert po in copies, "ref pose array not found as a whole"
    report = {"pose_copies": copies, "bones": {}}
    newT = {}
    for name, b in rig["bones"].items():
        side, e = b["side"], np.array(b["axis_head_local"], float)
        amp = name.replace("KB_Blink_", "KB_Amp_")
        ia, ib, isrc = ix[amp], ix[name], ix[SOURCE[side]]
        assert N[P[ia]] == "Head" and P[ib] == ia and N[P[isrc]] == "Head", (amp, name)
        d_open, d_closed = np.array(cal[SOURCE[side]]["open"]), np.array(cal[SOURCE[side]]["closed"])
        travel = d_open[0] - d_closed[0]
        R = basis_from_x(-e)
        S = np.array([b["magnitude"] / travel, EPS, EPS])
        p = L[isrc][:3, 3]
        lid_t = p + d_open
        rest = C[ib][:3, 3]                                   # lid bone rest in component space (import)
        Hc = C[ix["Head"]]
        rest_head = np.linalg.solve(Hc[:3, :3], rest - Hc[:3, 3])   # in Head local coordinates
        t = rest_head - R @ (S * lid_t)
        q = quat_from_matrix(R)
        assert np.allclose(refskel.quat_mat(*q), R, atol=1e-6)
        newT[ia] = (q, t, S)
        newT[ib] = ([0, 0, 0, 1.0], lid_t, np.ones(3))
        # check: Head-space displacement of the lid bone at the neutral blink
        disp = R @ (S * (p + d_closed)) + t - rest_head
        report["bones"][name] = {"amp_scale": np.round(S, 4).tolist(), "amp_axis_x": np.round(R[:, 0], 4).tolist(),
                                 "closed_disp_head": np.round(disp, 3).tolist(),
                                 "expected": np.round(b["magnitude"] * e, 3).tolist()}
        assert np.allclose(disp, b["magnitude"] * e + R @ (S * np.r_[0, d_closed[1:] - d_open[1:]]), atol=1e-4)
    for base in copies:
        for i, (q, t, s) in newT.items():
            struct.pack_into("<10f", data, base + 40 * i, *q, *t, *s)
    open(dst, "wb").write(bytes(data))
    # verify the written mesh
    r2 = refskel.read(dst)
    for name in rig["bones"]:
        i = ix[name]
        assert np.allclose(r2["component"][i][:3, 3], C[i][:3, 3], atol=1e-3), name
    report["verified_rest_positions"] = True
    if rep_json:
        json.dump(report, open(rep_json, "w"), indent=1)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", help="cooked Karin mesh (from the editor cook)")
    ap.add_argument("out", help="output mesh .uasset")
    ap.add_argument("rig", help="blink_rig.json written by scripts/blender/blink_rig.py")
    ap.add_argument("calib", help="lid calibration JSON (scripts/lid_calib.py, configs/lid_calib_t28.json)")
    ap.add_argument("report", nargs="?", help="optional report JSON")
    args = ap.parse_args()
    r = main(args.mesh, args.out, args.rig, args.calib, args.report)
    print("pose copies", r["pose_copies"])
    for n, b in r["bones"].items():
        print("%-16s scale %s  closed disp %s  expected %s" % (n, b["amp_scale"], b["closed_disp_head"], b["expected"]))
