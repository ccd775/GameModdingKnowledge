"""Regenerates a mod's streaming_links.stream from the vanilla link table with every relink so far (v5 hair parts,
v6 body variants -> Porter, v7 cutscene face/inner/second hair set, v9 barefoot parts (shown when the equipped boots
come off; the game hides Porter's own boots then) -> Karin's shoes, v10 equipped boots, v11+ shower hair set).

python make_links.py <version> [--out <streaming_links.stream>] [--print]

A version ending in "f" is for the expression build (build_karin.ps1 -Face): the face skin part 50108:43 keeps its
vanilla mesh (LodMesh 50120:1) and that LodMesh's ZivaRT LOD0/1 point at its LOD2 mesh 186, which holds Karin's face.
Port of the project's make_links.sh (which ran relink.py on the game machine over ssh); the relink list is the same.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def edits(v):
    a = []

    def add(src, field, dst):
        a.extend((src, field, dst))
    face = v.endswith('f')
    faceparts = [51, 27, 45, 46, 36, 40, 29, 38, 30, 42] if face else [51, 27, 45, 43, 46, 36, 40, 29, 38, 30, 42]
    for i in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13):                    # v5: Porter hair parts
        add(f'50121:{i}', 'MeshResource', '50121:82')
    for n in (0, 2, 4, 5, 6, 7):                                          # v6: variants -> Porter
        add('31123:279', f'VariantDefs.Variant#{n}', '50107:0')
    add('50108:595', 'RuntimeMeshes.Mesh#3', '50108:490')                 # v7: inner LOD3/4
    add('50108:595', 'RuntimeMeshes.Mesh#4', '50108:490')
    for p in faceparts:                                                   # v7: Sam face parts
        add(f'50108:{p}', 'MeshResource', '50108:595')
    if face:
        add('50120:1', 'RuntimeMeshes.Mesh#0', '50120:186')
        add('50120:1', 'RuntimeMeshes.Mesh#1', '50120:186')
    for p in range(2, 20):                                                # v7: second hair set
        add(f'50120:{p}', 'MeshResource', '50121:82')
    add('50108:57', 'MeshResource', '50108:153')                         # v9: barefoot R/L -> Karin's shoes
    add('50108:35', 'MeshResource', '50108:282')
    # v10: equipped boots (player group 31123). build_ds2 puts Karin's shoes into boot item 11's uppers (LodMesh
    # 15523 L / 8554 R); every other part of boot items 11-18 (second layers, soles, the other types; 19/20/93/94
    # reuse 11's parts) links to the upper of its side. The uppers' six materials bind the "pizza" variant set
    # 31225:22 (set object and its entry-0 texture 0x1B) instead of 67690:0 / :1, which cutscene Sam doubles share;
    # Karin's shoe page goes into set 22, and the texture swaps of variants 20/93/94 all swap to set 22 too.
    for pl in ('22242:15523 22818:8554 32159:15523 29315:8554 44636:15523 7685:8554 47607:15523 27100:8554 '
               '20919:15523 25841:8554 25573:15523 6384:8554 5936:15523 44815:8554 4499:15523 21519:8554 '
               '29107:15523 17118:8554 47743:15523 10424:8554 26938:15523 37283:8554 44332:15523 33052:8554 '
               '24234:15523 27278:8554 38753:15523 41294:8554 42537:15523 23081:8554 24233:15523 44425:15523 '
               '16406:15523 6182:8554 7752:15523 15866:8554 44402:8554 16639:15523 7287:8554 35761:15523 '
               '46970:8554 10042:15523 34662:8554').split():
        part, mesh = pl.split(':')
        add(f'31123:{part}', 'MeshResource', f'31123:{mesh}')
    # parts 40254 / 37072 (R) and 26207 (L) hold 2-byte records (LodMesh 5893 / 7069 / 6266 < 8192) that can't take
    # 15523 / 8554: their LodMeshes' three LOD meshes point at the shoe meshes instead
    for lm in (5893, 7069):
        for k, m in enumerate((29579, 17027, 37070)):
            add(f'31123:{lm}', f'RuntimeMeshes.Mesh#{k}', f'31123:{m}')
    for k, m in enumerate((33600, 5899, 30270)):
        add('31123:6266', f'RuntimeMeshes.Mesh#{k}', f'31123:{m}')
    for re_ in (44191, 28864, 41445, 47608, 34458, 42947):
        add(f'31123:{re_}', '@67690:0', '31225:22')
        add(f'31123:{re_}', '@67690:1', '31225:27')
    for rt in (105, 157, 85, 37, 158, 59):
        add(f'31225:{rt}', 'TextureSet', '31225:22')
    # v11 (experiment): which shared detail texture carries the long-save dust that greys her (a shower clears it).
    # Only Karin's materials, one group per material, each swapped for the all-zero 4x4 75978:0.
    if v.startswith('v11'):
        for re_ in (489, 235, 66):
            for t in ('74417:0', '74412:0', '74416:1'):
                add(f'50108:{re_}', f'@{t}', '75978:0')
        for re_ in (178, 612):
            for t in ('74410:0', '74416:0', '74413:0', '74418:0'):
                add(f'50108:{re_}', f'@{t}', '75978:0')
        for t in ('74416:0', '74413:0', '74418:0'):
            add('50108:412', f'@{t}', '75978:0')
        for t in ('74406:0', '74411:0', '74419:0', '79289:0'):
            add('50110:166', f'@{t}', '75978:0')
        for t in ('74411:0', '74419:0', '79289:0'):
            add('50110:172', f'@{t}', '75978:0')
    # v11+: the player's hair variation (DSPlayerModelControl HairApv 31123:199) swaps the seven hair parts that now
    # all show Karin's ears / bangs / side locks (LodMesh 50121:82) to Sam's other atlas 31301:0. The swap keeps 67704:0.
    if len(v) > 2 and v[:2] == 'v1' and v[2] in '123456789':
        add('31123:32822', 'TextureSet', '67704:0')
    # v12 only (failed): the four dust detail textures swapped for the all-zero 75978:0 in every material she wears;
    # the dust still covered her, now black (the textures give the look; the wear state lays it on).
    if v.startswith('v12'):
        l0, l1 = ('74406:0', '74411:0', '74419:0', '79289:0'), ('74411:0', '74419:0', '79289:0')
        for re_ in ('50108:489', '50108:178', '50108:191', '50108:609', '50110:166', '31123:44191', '31123:47608'):
            for t in l0:
                add(re_, f'@{t}', '75978:0')
        for re_ in ('50108:235', '50108:612', '50108:329', '50108:303', '50110:172', '50120:176', '50120:89',
                    '50120:91', '31123:28864', '31123:34458'):
            for t in l1:
                add(re_, f'@{t}', '75978:0')
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('version', help='e.g. v13 (no expression) or v13f (expression build)')
    ap.add_argument('--out', help='default DS2_MODDING/work/karin/v1/streaming_links_<version>.stream')
    ap.add_argument('--print', action='store_true', help='print the relink arguments instead of running relink.py')
    a = ap.parse_args()
    args = edits(a.version)
    if a.print:
        print(' '.join(args))
        return
    out = a.out
    if not out:
        if not os.environ.get('DS2_MODDING'):
            raise SystemExit('set DS2_MODDING (the modding workspace) or pass --out')
        out = os.path.join(os.environ['DS2_MODDING'], 'work', 'karin', 'v1', f'streaming_links_{a.version}.stream')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'relink.py'), out, *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    print(r.stdout.strip().splitlines()[-1])


if __name__ == '__main__':
    main()
