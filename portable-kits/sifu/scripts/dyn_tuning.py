# Tuning of the bone-chain dynamics (PA_Karin_Dynamics + the RigidBody node of ABP_Karin_PostProcess).
# Pure python (no bpy): dyn_stage.run() calls apply() on fresh geometry, and an existing cloth.json can be re-tuned
# without a Blender rebuild:   python dyn_tuning.py <cloth.json>
#
# Target behaviour = the source model's VRChat PhysBones (exported as VRM springs): gravity 0, pull 0.17-0.27,
# drag 0.27-0.63 per frame. The hair keeps its modelled shape and only sways with motion, heavily damped.
# Reference in-game: the game's own PA_M_MainChar_Dynamics (cape) uses cone 30/20, twist locked/10, no drives,
# AngularDamping 15-20 on boxy 0.65-1 kg bodies.
#
# Physics notes (UE 4.26 RBAN over PhysX immediate mode):
# - PhysX body damping is v *= max(0, 1 - c*dt) per step on the body's own velocities. For a slender body swinging
#   about its joint, angular damping only acts on I_com (~1/4 of I about the joint, far less for a chain), so it
#   barely damps pendulum motion; linear damping (COM velocity) and joint drive damping do the work.
# - Constraint drives are acceleration springs (UE sets PxD6JointDriveFlag::eACCELERATION): the torque is
#   I_row * (S * angle + D * rel_ang_vel) with I_row the child's I_com for an angular row. To give a sub-chain of
#   inertia I_sub (about the joint) the mode w, S = w^2 * I_sub / I_com and D = 2 * zeta * w * I_sub / I_com.
import argparse
import json
import math

DRIVE_ACCELERATION = True

# chain name -> per-bone masses (kg), mode frequency (Hz), joint damping ratio, body damping (1/s),
# swing limits per joint (deg), twist limit (deg), kinematic colliders this chain may touch
CHAINS = {
    "Hair_tail_L": dict(masses=[0.25, 0.2, 0.15], freq=1.3, zeta=0.45, lin_damp=8.0, ang_damp=4.0,
                        swing=[40, 30, 30], twist=6,
                        collide=["head", "neck_01", "spine_02", "spine_03", "upperarm_l", "upperarm_r"]),
    "Hair_tail_R": dict(masses=[0.25, 0.2, 0.15], freq=1.3, zeta=0.45, lin_damp=8.0, ang_damp=4.0,
                        swing=[40, 30, 30], twist=6,
                        collide=["head", "neck_01", "spine_02", "spine_03", "upperarm_l", "upperarm_r"]),
    "Tail": dict(masses=[0.4, 0.3, 0.25, 0.2, 0.1], freq=1.5, zeta=0.45, lin_damp=8.0, ang_damp=4.0,
                 swing=[30, 25, 25, 25, 25], twist=5, collide=["pelvis", "spine_01"]),
    "Hair_side_L": dict(masses=[0.1], freq=2.0, zeta=0.5, lin_damp=8.0, ang_damp=4.0,
                        swing=[25], twist=5, collide=["head", "spine_03"]),
    "Hair_side_R": dict(masses=[0.1], freq=2.0, zeta=0.5, lin_damp=8.0, ang_damp=4.0,
                        swing=[25], twist=5, collide=["head", "spine_03"]),
}

# FAnimNode_RigidBody settings. Gravity is reduced (the source springs had none) so the drives hold the modelled
# shape; component velocity/acceleration feed the motion in, clamped against Sifu's abrupt starts and stops.
NODE = {
    "SimulationSpace": "BaseBoneSpace", "BaseBoneRef": {"BoneName": "root"},
    "bOverrideWorldGravity": True, "OverrideWorldGravity": {"X": 0.0, "Y": 0.0, "Z": -300.0},
    "ComponentLinearAccScale": {"X": 0.35, "Y": 0.35, "Z": 0.35},
    "ComponentLinearVelScale": {"X": 0.3, "Y": 0.3, "Z": 0.3},
    "ComponentAppliedLinearAccClamp": {"X": 2500.0, "Y": 2500.0, "Z": 2500.0},
    "CachedBoundsScale": 1.2, "bEnableWorldGeometry": False,
    "bForceDisableCollisionBetweenConstraintBodies": True,
}


def _capsule_icom(m, r, h):
    """Inertia about the COM, perpendicular to the axis, of a capsule (radius r, cylinder length h) of mass m."""
    L = h + 2 * r
    return m * (L * L / 12.0 + r * r / 4.0)


def apply(dyn, node=None):
    """Fill masses, damping, limits, drives and collision filtering into the dynamics json (geometry from dyn_stage)."""
    bodies = {b["bone"]: b for b in dyn["bodies"]}
    joints = {j["child"]: j for j in dyn["joints"]}
    kinematic = [b["bone"] for b in dyn["bodies"] if b.get("kinematic")]
    disable = set()
    report = {}
    for ch in dyn["chains"]:
        t = ch.get("tune") or CHAINS[ch["name"]]
        bones = ch["bones"]
        n = len(bones)
        seg = [2.0 * bodies[b]["center"][0] for b in bones]          # body centre sits at half the segment
        icom = []
        for k, b in enumerate(bones):
            bd = bodies[b]
            bd["mass"] = t["masses"][k]
            bd["lin_damp"] = t["lin_damp"]
            bd["ang_damp"] = t["ang_damp"]
            icom.append(_capsule_icom(bd["mass"], bd["radius"], bd["length"]))
        w = 2 * math.pi * t["freq"]
        rep = []
        for k, b in enumerate(bones):
            isub = 0.0
            for j in range(k, n):
                d = sum(seg[k:j]) + seg[j] / 2.0                       # straight-chain distance joint k -> COM j
                isub += icom[j] + t["masses"][j] * d * d
            scale = isub / icom[k] if DRIVE_ACCELERATION else isub
            jt = joints[b]
            jt["swing1"] = jt["swing2"] = float(t["swing"][k])
            jt["twist"] = float(t["twist"])
            jt["drive_stiffness"] = round(w * w * scale, 1)
            jt["drive_damping"] = round(2 * t["zeta"] * w * scale, 2)
            rep.append({"bone": b, "I_sub/I_com": round(isub / icom[k], 1), "S": jt["drive_stiffness"], "D": jt["drive_damping"]})
        report[ch["name"]] = rep
        for b in bones:
            for c in kinematic:
                if c not in t["collide"]:
                    disable.add((b, c))
    # chains never collide with each other
    for a in dyn["chains"]:
        for b in dyn["chains"]:
            if a["name"] < b["name"]:
                for x in a["bones"]:
                    for y in b["bones"]:
                        disable.add((x, y))
    rest = {tuple(p) for p in dyn.get("rest_overlap_pairs", [])}
    dyn["disable_pairs"] = sorted([list(p) for p in disable | rest])
    if node is not None:
        node.clear()
        node.update(json.loads(json.dumps(NODE)))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-tune the bone-chain dynamics of an existing cloth.json in place "
                                             "(masses, damping, limits, drives, collision filter, RigidBody node).")
    ap.add_argument("cloth_json", help="cloth.json written by build_karin.py; rewritten in place, report on stdout")
    path = ap.parse_args().cloth_json
    data = json.load(open(path, encoding="utf-8"))
    rep = apply(data["dynamics"], data.setdefault("rigidbody", {}))
    json.dump(data, open(path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rep, indent=1))
