"""Collect the Sam reference data the Karin builder needs into one JSON.

python prep_ref.py <out.json>
  skeleton 50118:0 names/parents and bind world matrices (from the inverse bind matrices of every Porter mesh),
  JointIndexList of every slot mesh, and which primitive of each slot mesh uses which material (by colour texture).
  The coat meshes of group 50110 (Cloth_PBD joints) are slots too: their joint lists go to coat_joint_lists.
"""
import argparse
import json
import sys

import numpy as np

from graph import Graph, game_root
from group import read_group
from patch_core import mat44

GID = 50108
SKEL = (50118, 0)
SLOT_MESHES = [144, 73, 392, 218, 364, 90, 453, 614, 194]
COAT_GID, COAT_MESHES = 50110, [234, 124, 73]
HAIR_GID, HAIR_SKEL, HAIR_MESHES = 50121, (67700, 0), [85, 38, 27, 56]   # LodMesh 50121:82 LOD0..3 (Hair_PBD)
FACE_GID, FACE_SKEL, FACE_MESHES = 50120, (67711, 0), [186, 229, 45]  # Sam's face skin LodMesh 50120:1 LOD2..4
# colour textures and texture sets of the Porter materials (object index in 50108); effects bind either
ALBEDO = {16: 'body', 384: 'gloves', 8: 'boots', 2: 'body', 3: 'gloves', 1: 'boots'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', help='ref.json')
    out_path = ap.parse_args().out
    g = Graph(game_root())
    objs = read_group(g, GID)
    sk = read_group(g, SKEL[0])[SKEL[1]]
    names = [j['Name'] for j in sk['Joints']]
    parents = [j['ParentIndex'] for j in sk['Joints']]
    world = body_world = {}
    spread = {}

    def bind(group, i):
        jb = group[group[i]['SkinnedMeshJointBindings'][2]]
        for j, x in zip(jb['JointIndexList'], jb['InverseBindMatrices']):
            w = np.linalg.inv(mat44(x))
            if j in world:
                spread[j] = max(spread.get(j, 0.0), float(np.abs(world[j] - w).max()))
            else:
                world[j] = w
        return list(jb['JointIndexList'])
    joint_lists = {i: bind(objs, i) for i, o in enumerate(objs)
                   if o['__type__'] == 'RegularSkinnedMeshResource' and tuple(o['Skeleton'][1:]) == SKEL}
    coat = read_group(g, COAT_GID)
    coat_lists = {i: bind(coat, i) for i in COAT_MESHES}
    # hair slot: skeleton 67700 (Head + root-level Hair_PBD particles), binds from every 50121 mesh on it
    hsk = read_group(g, HAIR_SKEL[0])[HAIR_SKEL[1]]
    hair = read_group(g, HAIR_GID)
    world, spread_body = {}, spread
    spread = {}
    hair_lists = {i: bind(hair, i) for i, o in enumerate(hair)
                  if o['__type__'] == 'RegularSkinnedMeshResource' and tuple(o['Skeleton'][1:]) == HAIR_SKEL}
    hair_out = dict(names=[j['Name'] for j in hsk['Joints']], parents=[j['ParentIndex'] for j in hsk['Joints']],
                    world={str(j): w.tolist() for j, w in world.items()},
                    joint_lists={str(k): hair_lists[k] for k in HAIR_MESHES})
    # face slot: facial skeleton 67711, binds from every 50120 mesh on it (face skin LOD0..4)
    fsk = read_group(g, FACE_SKEL[0])[FACE_SKEL[1]]
    face = read_group(g, FACE_GID)
    world, spread = {}, {}
    face_lists = {i: bind(face, i) for i, o in enumerate(face)
                  if o['__type__'] == 'RegularSkinnedMeshResource' and tuple(o['Skeleton'][1:]) == FACE_SKEL}
    face_out = dict(names=[j['Name'] for j in fsk['Joints']], parents=[j['ParentIndex'] for j in fsk['Joints']],
                    world={str(j): w.tolist() for j, w in world.items()},
                    joint_lists={str(k): face_lists[k] for k in FACE_MESHES})
    world, spread = body_world, spread_body
    materials = {}
    for mi in SLOT_MESHES:
        m = objs[mi]
        mats = []
        for sg_ref in m['ShadingGroups']:
            re = objs[objs[sg_ref[2]]['RenderEffect'][2]]
            tex = set()
            for ts in re['TechniqueSets']:
                for t in ts['RenderTechniques']:
                    for tb in t['TextureBindings']:
                        r = tb.get('TextureResource')
                        if r and r[1] == GID:
                            tex.add(r[2])
            kind = sorted({ALBEDO[t] for t in tex if t in ALBEDO})
            mats.append(kind[0] if len(kind) == 1 else None)
        materials[mi] = mats
    out = dict(names=names, parents=parents, world={str(j): w.tolist() for j, w in world.items()},
               joint_lists={str(k): v for k, v in joint_lists.items()}, materials={str(k): v for k, v in materials.items()},
               coat_joint_lists={str(k): v for k, v in coat_lists.items()}, hair=hair_out, face=face_out)
    json.dump(out, open(out_path, 'w'))
    print('joints', len(names), 'bind known', len(world), 'max IBM disagreement', max(spread.values()) if spread else 0)
    for mi in SLOT_MESHES:
        print('mesh', mi, 'joints', len(joint_lists.get(mi, [])), 'materials', materials[mi])
    for mi in COAT_MESHES:
        print('coat mesh', mi, 'joints', len(coat_lists[mi]))
    print('hair skeleton', len(hair_out['names']), 'bind known', len(hair_out['world']),
          {k: len(v) for k, v in hair_out['joint_lists'].items()})
    print('face skeleton', len(face_out['names']), 'bind known', len(face_out['world']),
          {k: len(v) for k, v in face_out['joint_lists'].items()})
    for n in ('JNT_C_B_001_Hips', 'JNT_C_B_008_Head', 'JNT_L_B_000_Shoulder', 'JNT_L_B_001_Arm', 'JNT_L_B_003_Hand',
              'JNT_L_B_100_Leg', 'JNT_L_B_102_Foot', 'JNT_L_B_103_Toe'):
        j = names.index(n)
        print('  %-22s %s' % (n, np.round(world[j][:3, 3], 3).tolist() if j in world else 'no bind'))


if __name__ == '__main__':
    main()
