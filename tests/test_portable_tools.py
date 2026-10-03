"""Synthetic fixtures only. No game installation or private model is required."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
import ast

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
KITS = ROOT / 'portable-kits'


def module(game, name):
    path = KITS / game / 'scripts' / f'{name}.py'
    if game == 'common' and name == 'modkit':
        path = KITS / game / 'modkit.py'
    if not path.is_file():
        raise unittest.SkipTest(f'{game} is not included in this single-game export')
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def cli(game, name, *args, ok=True):
    path = KITS / game / 'scripts' / f'{name}.py'
    if not path.is_file():
        raise unittest.SkipTest(f'{game} is not included in this single-game export')
    process = subprocess.run([sys.executable, '-B', str(path), *map(str, args)], capture_output=True, text=True)
    if (process.returncode == 0) != ok:
        raise AssertionError(f'{name}: exit {process.returncode}\n{process.stdout}\n{process.stderr}')
    return process


def dds(width=4, height=4, mips=1, dxgi=None, payload=b'\0' * 8):
    header = bytearray(148 if dxgi is not None else 128)
    header[:4] = b'DDS '
    for offset, value in ((4, 124), (12, height), (16, width), (28, mips), (76, 32)):
        struct.pack_into('<I', header, offset, value)
    header[84:88] = b'DX10' if dxgi is not None else b'DXT1'
    if dxgi is not None:
        struct.pack_into('<5I', header, 128, dxgi, 3, 0, 1, 0)
    return bytes(header) + payload


def xbt(texture):
    header = struct.pack('<3I', 0x00584254, 123, 48) + b'\0' * 36
    return header + texture


def glb(points=None):
    binary, accessors, views = bytearray(), [], []
    def add(values, fmt, component, kind):
        while len(binary) % 4: binary.append(0)
        offset = len(binary)
        for row in values: binary.extend(struct.pack('<' + fmt, *row))
        views.append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(binary) - offset})
        accessors.append({'bufferView': len(views) - 1, 'componentType': component, 'count': len(values), 'type': kind})
        return len(accessors) - 1
    attrs = {
        'POSITION': add(points or [(0,0,0),(1,0,0),(0,1,0)], '3f', 5126, 'VEC3'),
        'NORMAL': add([(0,0,1)] * 3, '3f', 5126, 'VEC3'),
        'TEXCOORD_0': add([(0,0),(1,0),(0,1)], '2f', 5126, 'VEC2'),
        'JOINTS_0': add([(0,0,0,0)] * 3, '4B', 5121, 'VEC4'),
        'WEIGHTS_0': add([(1,0,0,0)] * 3, '4f', 5126, 'VEC4'),
        'COLOR_0': add([(1,1,1,1)] * 3, '4f', 5126, 'VEC4')}
    indices = add([(0,),(1,),(2,)], 'H', 5123, 'SCALAR')
    identity = (1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
    ibms = add([identity], '16f', 5126, 'MAT4')
    while len(binary) % 4: binary.append(0)
    document = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}],
                'bufferViews': views, 'accessors': accessors, 'materials': [{'name': 'Synthetic'}],
                'nodes': [{'name':'root'}, {'name':'mesh_0', 'mesh':0, 'skin':0}],
                'skins':[{'joints':[0], 'inverseBindMatrices':ibms}], 'scenes':[{'nodes':[0,1]}], 'scene':0,
                'meshes':[{'name':'mesh_0', 'primitives':[{'attributes':attrs, 'indices':indices, 'material':0}]}]}
    encoded = json.dumps(document).encode()
    encoded += b' ' * (-len(encoded) % 4)
    body = struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + struct.pack('<II', len(binary), 0x004E4942) + binary
    return struct.pack('<4sII', b'glTF', 2, len(body) + 12) + body


class PortableTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding portable ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_project_resume_and_no_overwrite(self):
        m = module('common', 'modkit')
        project = self.root / 'project'
        m.initialize(project, 'left-4-dead-2')
        m.checkpoint(project, 'inspect-1', 'research', 'Need a target rig', ['project.json'])
        self.assertEqual(m.read_json(project/'history/inspect-1.json')['status'], 'research')
        with self.assertRaises(FileExistsError): m.initialize(project, 'left-4-dead-2')
        with self.assertRaises(FileExistsError): m.checkpoint(project, 'inspect-1', 'pass', '', [])

    def test_manifest_drift_and_deterministic_zip(self):
        m = module('common', 'modkit')
        data = self.root/'data'; data.mkdir(); (data/'space name.txt').write_text('synthetic')
        manifest = self.root/'manifest.json'
        m.inventory(data, manifest)
        self.assertEqual(len(m.verify(data, manifest)), 1)
        a = m.package(data, manifest, self.root/'one.zip')
        b = m.package(data, manifest, self.root/'two.zip')
        self.assertEqual(a['sha256'], b['sha256'])
        (data/'extra.txt').write_text('unexpected')
        with self.assertRaises(ValueError): m.verify(data, manifest)

    def test_empty_and_escape_refused(self):
        m = module('common', 'modkit')
        with self.assertRaises(ValueError): m.inventory(self.root, self.root/'manifest.json')
        for path in ('../escape', '/absolute', 'X:/escape', 'x\\escape'):
            with self.assertRaises(ValueError): m.relative_file(self.root, path)

    def test_xbt_payload_roundtrip(self):
        source = self.root/'low.xbt'; source.write_bytes(xbt(dds()))
        extracted = self.root/'texture.dds'; output = self.root/'result.xbt'
        cli('watch-dogs','xbt_tool','extract',source,extracted)
        cli('watch-dogs','xbt_tool','inject',source,extracted,output)
        self.assertEqual(source.read_bytes(), output.read_bytes())
        cli('watch-dogs','xbt_tool','inject',source,extracted,source,ok=False)
        extracted.write_bytes(dds(width=8))
        cli('watch-dogs','xbt_tool','inject',source,extracted,self.root/'bad.xbt',ok=False)

    def test_prim_roundtrip_positive_and_negative(self):
        m = module('hitman-world-of-assassination', 'compare_prim_roundtrip')
        source = self.root/'0000000000000001.PRIM.glb'; source.write_bytes(glb())
        output = self.root/'roundtrip.glb'; output.write_bytes(glb())
        self.assertEqual(m.compare(source, output)['status'], 'pass')
        output.write_bytes(glb([(0,0,0),(1.5,0,0),(0,1,0)]))
        self.assertEqual(m.compare(source, output)['status'], 'fail')

    def test_prim_validator_rejects_truncated_binary(self):
        source = self.root/'0000000000000001.PRIM.glb'; source.write_bytes(b'glTF')
        cli('hitman-world-of-assassination','validate_prim_glb',source,'--skip-meta',ok=False)

    def test_forge_rebuild_and_independent_extract(self):
        import lz4.block
        m = module('assassins-creed-black-flag', 'rebuild_forge_v50_patch')
        resource_type, resource_id = 0x85C817C3, 42
        def resource(payload):
            return struct.pack('<IQBQI', resource_type, len(payload)+12, 0, resource_id, resource_type) + payload
        asset = resource(b'synthetic ' * 80)
        index = m.build_bundle_index([{'object_id':resource_id, 'decoded_size':len(asset), 'reserved':b'\0'*6}], b'')
        first = m.encode_bms(index, 1, 65536, True, lz4.block)[0]
        second = m.encode_bms(asset, 1, 65536, False, lz4.block)[0]
        entry = first + second
        fat = m.FORGE_HEADER.size
        start = fat + m.FAT_HEADER.size
        toc = start + len(entry)
        data = m.FORGE_HEADER.pack(b'scimitar',0,50,fat,1,0) + m.FAT_HEADER.pack(1,toc,0xFFFFFFFFFFFFFFFF)
        data += entry + m.FAT_ROW.pack(start,resource_id,len(entry),resource_type)
        source = self.root/'source.forge'; source.write_bytes(data)
        replacement = self.root/'replacement.bin'; replacement.write_bytes(resource(b'replacement ' * 80))
        for name in ('one','two'):
            cli('assassins-creed-black-flag','rebuild_forge_v50_patch','--input',source,
                '--output',self.root/f'{name}.forge','--report',self.root/f'{name}.json','--replace',f'42={replacement}')
        self.assertEqual((self.root/'one.forge').read_bytes(), (self.root/'two.forge').read_bytes())
        cli('assassins-creed-black-flag','extract_forge_v50_bms',self.root/'one.forge',
            '--output-root',self.root/'decoded','--json-output',self.root/'extract.json','--markdown-output',self.root/'extract.md')
        report = json.loads((self.root/'extract.json').read_text())
        self.assertTrue(report['validation']['all_passed'])
        self.assertEqual(report['oodle']['libraries'], {})
        self.assertEqual(source.read_bytes(), data)
        with self.assertRaises(m.RebuildError): m.parse_outer_forge(data[:20])

    def test_l4d2_vta_custom_contract(self):
        source = self.root/'face.vta'; output = self.root/'scaled.vta'; smd = self.root/'ref.smd'
        source.write_text('version 1\nnodes\n0 "root" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\n'
                          'time 1 # smile\n0 0 0 0 0 0 0\nend\nvertexanimation\ntime 0\n'
                          '0 0 0 0 0 0 1\n1 1 0 0 0 0 1\n2 0 1 0 0 0 1\ntime 1\n0 0 0 1 0 0 1\nend\n')
        smd.write_text('version 1\ntriangles\nmat\n0 0 0 0 0 0 1 0 0 0\n0 2 0 0 0 0 1 0 0 0\n0 0 2 0 0 0 1 0 0 0\nend\n')
        args = ['--input', source, '--output', output, '--reference-smd', smd,
                '--input-units-per-meter','1','--output-units-per-meter','2', '--report',self.root/'vta.json',
                '--expected-nodes','1','--expected-frames','2']
        cli('left-4-dead-2','rescale_vta',*args)
        self.assertIn('0 0.000000 0.000000 2.000000 0 0 1', output.read_text())
        cli('left-4-dead-2','rescale_vta',*args,ok=False)

    def test_vpk_crc_and_path_boundary(self):
        m = module('left-4-dead-2', 'extract_vpk_entries')
        source = self.root/'synthetic.vpk'; payload=b'synthetic payload'
        source.write_bytes(struct.pack('<III',0x55AA1234,1,0)+payload)
        row={'path':'models/test.bin','metadata_size':0,'archive_index':0x7FFF,'offset':0,'size':len(payload),'crc32':zlib.crc32(payload)}
        m.extract_one(source,self.root/'out',row,False)
        self.assertEqual((self.root/'out/models/test.bin').read_bytes(),payload)
        with self.assertRaises(ValueError): m.safe_destination(self.root,'../escape')
        row['crc32'] = 0
        with self.assertRaises(IOError): m.extract_one(source,self.root/'bad',row,False)

    def test_re4_pak_extract_and_corrupt_bounds(self):
        m = module('resident-evil-4-remake','re4_pak_analyze')
        payload = b'MESH' + b'synthetic '*80
        compressor=zlib.compressobj(wbits=-15); encoded=compressor.compress(payload)+compressor.flush()
        lo,hi = m.path_hash('natives/stm/synthetic.mesh.1')
        source=self.root/'test.pak'
        source.write_bytes(struct.pack('<4sIII',b'KPKA',4,1,0)+struct.pack('<6Q',lo|(hi<<32),64,len(encoded),len(payload),1,0)+encoded)
        output=self.root/'mesh.bin'
        cli('resident-evil-4-remake','re4_pak_analyze','extract-index',source,0,output)
        self.assertEqual(output.read_bytes(),payload)
        cli('resident-evil-4-remake','re4_pak_analyze','extract-index',source,-1,self.root/'bad',ok=False)
        source.write_bytes(source.read_bytes()[:64])
        with self.assertRaises(ValueError): m.read_entries(source)

    def test_hd2_triplet_and_lut(self):
        m=module('helldivers-2','stingray_archive')
        patch=self.root/'synthetic.patch_0'
        main=b'synthetic'
        data=bytearray(72); struct.pack_into('<4I',data,0,m.MAGIC,1,1,0)
        data.extend(struct.pack('<QQQII',0,m.UNIT_ID,1,0,0))
        data.extend(struct.pack('<7Q6I',1,m.UNIT_ID,184,0,0,0,0,len(main),0,0,0,0,1));data.extend(main)
        patch.write_bytes(data);Path(str(patch)+'.gpu_resources').write_bytes(b'');Path(str(patch)+'.stream').write_bytes(b'')
        cli('helldivers-2','inspect_patch',patch,'--report',self.root/'triplet.json')
        invalid=bytearray(data);struct.pack_into('<I',invalid,160,999999);patch.write_bytes(invalid)
        cli('helldivers-2','inspect_patch',patch,ok=False)
        payload=bytearray();w,h=23,8
        for mip in range(5):
            for row in range(h): payload.extend(struct.pack('<4e',float(row),0,0,1)*w)
            w,h=max(1,w//2),max(1,h//2)
        source=self.root/'lut.dds';source.write_bytes(dds(23,8,5,10,bytes(payload)))
        out=self.root/'collapsed.dds'
        cli('helldivers-2','collapse_lut_rows','--source-dds',source,'--source-row',3,'--output-dds',out,'--report',self.root/'lut.json')
        self.assertEqual(source.read_bytes()[:148],out.read_bytes()[:148])
        self.assertEqual(struct.unpack_from('<e',out.read_bytes(),148)[0],3.0)
        self.assertEqual(out.read_bytes()[148:148+184],out.read_bytes()[148+184:148+368])

    def test_all_cli_help(self):
        for path in KITS.glob('*/scripts/*.py'):
            if path.stem in ('stingray_archive','audit_blend_source'): continue
            if path.parents[1].name == 'ghost-of-tsushima' and got_missing(): continue
            if path.parents[1].name == 'horizon-forbidden-west' and hfw_missing(): continue
            if path.parents[1].name == 'god-of-war-ragnarok' and gowr_missing(): continue
            if path.parents[1].name == 'watch-dogs' and path.stem not in WD_STDLIB_SCRIPTS and wd_missing(pil=True): continue
            cli(path.parents[1].name,path.stem,'--help')


GOT_DEPENDENCIES = ('numpy', 'scipy', 'etcpak', 'texture2ddecoder', 'PIL')


def got_missing():
    return [m for m in GOT_DEPENDENCIES if importlib.util.find_spec(m) is None]


def got(name):
    """GoT builder module; skipped with the install hint when the kit's extra requirements are absent."""
    if not (KITS / 'ghost-of-tsushima').is_dir():
        raise unittest.SkipTest('ghost-of-tsushima is not included in this single-game export')
    if got_missing():
        raise unittest.SkipTest('pip install -r portable-kits/ghost-of-tsushima/requirements.txt (missing '
                                + ', '.join(got_missing()) + ')')
    return module('ghost-of-tsushima', name)


class GhostOfTsushimaTools(unittest.TestCase):
    """Builder modules on synthetic data. A full build needs the game install and a VRM and is not run here."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding got ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_got_psarc_stores_data_raw_and_aligned(self):
        arc = got('gotarc')
        files = [(f'/bitmaps/hero_kamakura_armor_chest_mtl.msac.{c}.synthetic.sps', bytes([i]) * (40 + i))
                 for i, c in enumerate('dnsg')]
        big = bytes((i * 7) % 251 for i in range(70000))
        files.append(('/meshes/hero_kamakura_armor_all_ranks.xmesh', big))
        out = self.root / 'mod.psarc'
        arc.write_psarc(str(out), files)
        raw = out.read_bytes()
        self.assertEqual(raw[:4], b'PSAR')
        for _, data in files[1:4]:                              # non-zero payloads: padding cannot fake a hit
            self.assertGreater(raw.find(data), 0)               # file data stored as is, not zlib
        self.assertEqual(raw.find(big) % 8192, 0)              # >= 64 KiB starts on an 8192 boundary
        back = arc.Psarc(str(out))
        for name, data in files:
            self.assertEqual(back.extract(name), data)
        back.s.f.close()                                     # Psarc keeps its stream open

    def test_got_weight_and_normal_packing(self):
        fmt = got('gotfmt')
        import numpy as np
        bones = np.array([[5, 7, 9, 0], [3, 0, 0, 0]])
        weights = np.array([[0.5, 0.3, 0.2, 0.0], [1.0, 0.0, 0.0, 0.0]])
        b, packed = fmt.quantize_weights(bones, weights)
        self.assertEqual(b[1].tolist(), [3, -1, -1, -1])
        implicit = 255 - packed[:, :3].astype(int).sum(1)       # bone 0 weight is not stored
        self.assertLessEqual(abs(implicit[0] - 127.5), 1)
        self.assertEqual(implicit[1], 255)
        v = np.random.default_rng(1).normal(size=(50, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        q = fmt.pack_n10(v)
        dec = np.stack([q & 1023, (q >> 10) & 1023, (q >> 20) & 1023], 1) / 1023.0 * 2 - 1
        self.assertLess(np.abs(dec - v).max(), 2.0 / 1023)

    def test_got_decimate_keeps_border_and_faces(self):
        dec = got('decimate')
        import numpy as np
        n = 12
        g = np.stack(np.meshgrid(np.arange(n), np.arange(n), indexing='ij'), -1).reshape(-1, 2).astype(float)
        tris = []
        for i in range(n - 1):
            for j in range(n - 1):
                a, b, c, d = i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1
                tris += [(a, b, c), (a, c, d)]
        mesh = dict(pos=np.c_[g, np.zeros(len(g))], tris=np.array(tris), uv=g / (n - 1),
                    joints=np.zeros((len(g), 4), int), weights=np.tile([1.0, 0, 0, 0], (len(g), 1)))
        target = int(len(g) * 0.8)
        out, stats = dec.decimate(mesh, target)
        self.assertLessEqual(stats['verts'][1], target)
        border = {tuple(p) for p in g if p[0] in (0, n - 1) or p[1] in (0, n - 1)}
        self.assertTrue(border <= {tuple(p[:2]) for p in out['pos']})
        faces = {tuple(sorted(t)) for t in out['tris'].tolist()}
        self.assertEqual(len(faces), len(out['tris']))
        P, T = out['pos'], out['tris']
        normal_z = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])[:, 2]
        self.assertTrue((normal_z > 0).all())

    def test_got_atlas_pixels_follow_uv(self):
        atlas = got('atlas')
        import numpy as np
        from PIL import Image
        items = []
        for key, (cx, cy), blue in (('a', (21, 31), 60), ('b', (40, 12), 200)):
            grid = np.zeros((64, 64, 4), np.uint8)              # per-pixel gradient: any offset changes the colour
            grid[..., 0] = np.arange(64)[None, :] * 4
            grid[..., 1] = np.arange(64)[:, None] * 4
            grid[..., 2] = blue                                 # alpha stays 0: colour must survive resampling
            uv = np.array([[cx + 0.5, cy + 0.5], [cx - 5, cy - 6], [cx + 6, cy - 6], [cx + 6, cy + 6],
                           [cx - 5, cy + 6]]) / 64.0
            items.append(dict(img=Image.fromarray(grid, 'RGBA'), uv=uv, key=key,
                              tris=np.array([[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1]])))
        # scale 1 is checked exactly (any one-pixel shift fails); the downscaled page only catches gross
        # mapping errors (axis swap, wrong scale), its tolerance allows about one page pixel of gradient
        for size, tol in ((64, 0), (24, 6)):
            page, uvs, info = atlas.build_page(items, (size, size))
            if size == 24:
                self.assertLess(info['scale'], 1.0)
            px = np.asarray(page.convert('RGBA')).astype(int)
            self.assertTrue((px[..., 2] > 0).all())             # empty page area is filled from the pieces
            for it, uv in zip(items, uvs):
                src = np.asarray(it['img']).astype(int)
                for k in (0, 1, 2, 3, 4):                       # centre and the four island corners
                    sx, sy = np.clip(np.floor(it['uv'][k] * 64 + (it['uv'][0] * 64 - it['uv'][k] * 64) * 0.2), 0, 63).astype(int)
                    x, y = np.clip(np.floor((uv[k] + (uv[0] - uv[k]) * 0.2) * size), 0, size - 1).astype(int)
                    with self.subTest(size=size, key=it['key'], vertex=k):
                        self.assertLessEqual(np.abs(px[y, x, :3] - src[sy, sx, :3]).max(), tol + 4 / info['scale'] * (tol > 0))

    def test_got_hang_pose_and_rest_solve(self):
        bk = got('build_karin')
        import numpy as np
        nb = bk.NBONES
        parents = [-1] * nb
        for side in (0, 1):
            ua, fa = (499, 505) if side == 0 else (546, 553)
            chain = [ua] + [b for b, _ in bk.LIMBS['leftUpperArm' if side == 0 else 'rightUpperArm'][2]]
            for p, c in zip(chain, chain[1:]):
                parents[c] = p
            parents[fa] = ua
        J = np.zeros((nb, 3))
        J[499], J[546] = (-1.6, 18.2, 147.0), (-1.6, -18.2, 147.0)
        J[505], J[553] = (-4.1, 47.3, 147.0), (-4.1, -47.3, 147.0)
        tgt = {'neck': np.array([0.3, 0, 147.8]), 'leftUpperArm': np.array([-0.5, 9.8, 144.8]),
               'rightUpperArm': np.array([-0.5, -9.8, 144.8]), 'leftLowerArm': J[505], 'rightLowerArm': J[553]}
        kj = {'neck': np.array([0, 0, 100.0]), 'leftUpperArm': np.array([0, 6.8, 98.0]),
              'rightUpperArm': np.array([0, -6.8, 98.0]), 'leftLowerArm': np.array([0, 25.8, 98.0]),
              'rightLowerArm': np.array([0, -25.8, 98.0])}
        maps, S, moving = bk.hang_pose({'kj': kj, 'tgt': tgt}, J, parents, 75.0, 1.45)
        for h, b in (('leftUpperArm', 499), ('rightUpperArm', 546)):
            root = maps[h][1]                                 # turned 75 degrees down, the root reaches her shoulder
            self.assertLess(np.linalg.norm(S[b, :3, :3] @ root + S[b, :3, 3] - tgt[h]), 1e-9)
        P = np.array([[0, 8.0, 140.0], [0, 20.0, 146.0], [0, 12.0, 145.0]])
        Pa = P + np.array([0, 4.0, -6.0])
        N = np.tile([0, 0, 1.0], (3, 1))
        bones = np.array([[10, 0, 0, 0], [500, 0, 0, 0], [10, 500, 0, 0]])
        weights = np.array([[1.0, 0, 0, 0], [1.0, 0, 0, 0], [0.5, 0.5, 0, 0]])
        x, n, moved = bk.rest_from_hang(P, N, bones, weights, S, moving, {500: (Pa, N)})
        self.assertEqual(moved, 2)
        self.assertTrue(np.array_equal(x[0], P[0]))            # torso-only vertices keep the torso fit
        self.assertLess(np.abs(x[1] - Pa[1]).max(), 1e-9)       # arm-only vertices land on the arm map
        R, t = S[500, :3, :3], S[500, :3, 3]
        posed = 0.5 * x[2] + 0.5 * (R @ x[2] + t)               # mixed vertex: exact in the hang pose
        self.assertLess(np.abs(posed - (0.5 * P[2] + 0.5 * (R @ Pa[2] + t))).max(), 1e-9)

    def test_got_builder_refuses_missing_inputs(self):
        got('gotfmt')                                           # same skip rules as the module tests
        out = self.root / 'mod.psarc'
        vrm = self.root / 'model.vrm'
        vrm.write_bytes(b'glTF')
        game = self.root / 'game'
        (game / 'cache_pc' / 'psarc').mkdir(parents=True)
        texconv = self.root / 'texconv.exe'
        texconv.write_bytes(b'not the real tool')
        base = ('--profile', 'picodra', '--out', out)
        cases = [
            ((), 'must name the source VRM file'),
            (('--vrm', vrm, '--game', self.root / 'missing'), 'must be the game folder'),
            (('--vrm', vrm, '--game', game, '--expected-texconv-sha256', '0' * 64), 'needs --texconv'),
            (('--vrm', vrm, '--game', game, '--texconv', self.root / 'missing.exe'), 'is not a file'),
            (('--vrm', vrm, '--game', game, '--texconv', texconv, '--expected-texconv-sha256', '0' * 64),
             'does not match'),
        ]
        for extra, message in cases:
            with self.subTest(message=message):
                process = cli('ghost-of-tsushima', 'build_karin', *base, *extra, ok=False)
                self.assertIn(message, process.stderr)
                self.assertFalse(out.exists())


GOWR_DEPENDENCIES = ('numpy', 'scipy', 'PIL', 'lz4', 'etcpak', 'texture2ddecoder')
GOWR_KIT = KITS / 'god-of-war-ragnarok'


def gowr_missing():
    return [m for m in GOWR_DEPENDENCIES if importlib.util.find_spec(m) is None]


def gowr_names():
    return [p.stem for p in (GOWR_KIT / 'scripts').glob('*.py')]


def gowr(name):
    """GoWR builder module; skipped with the install hint when the kit's extra requirements are absent.
    Modules of the same name loaded from anywhere else are dropped first, so the kit imports its own siblings."""
    if not GOWR_KIT.is_dir():
        raise unittest.SkipTest('god-of-war-ragnarok is not included in this single-game export')
    if gowr_missing():
        raise unittest.SkipTest('pip install -r portable-kits/god-of-war-ragnarok/requirements.txt (missing '
                                + ', '.join(gowr_missing()) + ')')
    scripts = (GOWR_KIT / 'scripts').resolve()
    for stem in gowr_names():
        loaded = sys.modules.get(stem)
        if loaded is not None and Path(getattr(loaded, '__file__', None) or '.').resolve().parent != scripts:
            sys.modules.pop(stem)
    return module('god-of-war-ragnarok', name)


def gowr_mesh_def(comps, vcount, icount, buf_offs, ind_off, ind_stride=2):
    """One synthetic MESH_ entry holding one definition, laid out where mesh.parse_mesh reads it."""
    b = bytearray(0x400)
    struct.pack_into('<II', b, 0xC, 0x14, 1)                  # header offset (table at 0x20) and def count
    o = 0x40
    struct.pack_into('<I', b, 0x20, o - 0x20)                  # self-relative pointer to the def
    struct.pack_into('<I', b, o + 0x30, ind_off)
    struct.pack_into('<I', b, o + 0x3C, buf_offs[0])
    struct.pack_into('<II', b, o + 0x44, vcount, icount // 3)
    struct.pack_into('<I', b, o + 0x5C, icount)
    struct.pack_into('<II', b, o + 0x60, 0x100, 0x180)         # component / buffer-offset tables, def-relative
    struct.pack_into('<Q', b, o + 0x68, 0x1234)
    b[o + 0x80], b[o + 0x81], b[o + 0x84] = len(buf_offs), ind_stride, len(comps)
    for j, c in enumerate(comps):
        struct.pack_into('<5B', b, o + 0x100 + 8 * j, *c)
    for j, off in enumerate(buf_offs):
        struct.pack_into('<I', b, o + 0x180 + 4 * j, off)
    return bytes(b)


def gowr_geo(np, sizes):
    """Synthetic geometry: one triangle strip per part; `sizes` maps part name -> vertex count."""
    P, IDX, part_of_tri, stats, base = [], [], [], {}, 0
    for k, (name, n) in enumerate(sizes.items()):
        P.append(np.c_[np.arange(n) * 0.01 + k, np.zeros(n), np.arange(n) % 2])
        tris = np.array([[i, i + 1, i + 2] for i in range(n - 2)]) + base
        IDX.append(tris)
        part_of_tri.append(np.full(len(tris), k))
        stats[name] = dict(verts=n)
        base += n
    P = np.concatenate(P)
    V = len(P)
    return dict(P=P, N=np.tile([0, 0, 1.0], (V, 1)), T=np.tile([1.0, 0, 0], (V, 1)), UV=np.zeros((V, 2)),
                INF=[[(0, 1.0)]] * V, IDX=np.concatenate(IDX), part_of_tri=np.concatenate(part_of_tri), stats=stats)


def gowr_fbx_nodes(specs, start):
    """Binary FBX 7.4 node records (12-byte headers); spec = (name, encoded props, children, has_null)."""
    out = bytearray()
    for name, props, children, null in specs:
        pb = b''.join(props)
        body_start = start + len(out) + 13 + len(name) + len(pb)
        body = gowr_fbx_nodes(children, body_start) if children else b''
        if null:
            body += bytes(13)
        out += struct.pack('<III', body_start + len(body), len(props), len(pb)) + bytes([len(name)]) + name + pb + body
    return bytes(out)


def gowr_fbx(filler, vertices):
    def s(b):
        return b'S' + struct.pack('<I', len(b)) + b
    def arr(code, fmt, values, enc):
        data = struct.pack('<%d%s' % (len(values), fmt), *values)
        data = zlib.compress(data) if enc else data
        return code + struct.pack('<III', len(values), enc, len(data)) + data
    specs = [
        (b'FBXHeaderExtension', [], [(b'FBXHeaderVersion', [b'I' + struct.pack('<i', 1003)], [], False),
                                     (b'Creator', [s(b'synthetic' + b'x' * filler)], [], False)], True),
        (b'Objects', [], [(b'Geometry', [b'L' + struct.pack('<q', 42), s(b'body_2\x00\x01Geometry'), s(b'Mesh')],
                           [(b'Vertices', [arr(b'd', 'd', vertices, 1)], [], False),
                            (b'PolygonVertexIndex', [arr(b'i', 'i', [0, 1, -3], 0)], [], False),
                            (b'Misc', [b'Y' + struct.pack('<h', 7), b'C\x01', b'F' + struct.pack('<f', 1.5),
                                       b'D' + struct.pack('<d', 2.5), b'R' + struct.pack('<I', 3) + b'raw'], [], False),
                            (b'Properties70', [], [], True)], True)], True),
        (b'Connections', [], [(b'C', [s(b'OO'), b'L' + struct.pack('<q', 42), b'L' + struct.pack('<q', 0)], [], False)], True),
    ]
    body = b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400) + gowr_fbx_nodes(specs, 27) + bytes(13)
    pad = -(len(body) + 20) % 16 or 16                         # footer padding ends on a 16-byte boundary
    magic = bytes.fromhex('f85a8c6adef5d97eece90ce3758f290b')
    return body + bytes(range(16)) + bytes(4) + bytes(pad) + struct.pack('<I', 7400) + bytes(120) + magic


def gowr_glb():
    """VRM-like GLB: mesh 'Body' plus 'body_2' whose two sparse POSITION targets are kisekae_Ankle and kisekae_Knee."""
    binary, views, accessors = bytearray(), [], []
    def view(raw):
        while len(binary) % 4: binary.append(0)
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(raw)})
        binary.extend(raw)
        return len(views) - 1
    def dense(rows):
        a = {'bufferView': view(b''.join(struct.pack('<3f', *r) for r in rows)), 'componentType': 5126,
             'count': len(rows), 'type': 'VEC3', 'min': [min(c) for c in zip(*rows)], 'max': [max(c) for c in zip(*rows)]}
        accessors.append(a)
        return len(accessors) - 1
    def sparse(count, idx, vals):
        accessors.append({'componentType': 5126, 'count': count, 'type': 'VEC3',
                          'min': [min(c) for c in zip(*vals)], 'max': [max(c) for c in zip(*vals)],
                          'sparse': {'count': len(idx),
                                     'indices': {'bufferView': view(struct.pack('<%dI' % len(idx), *idx)), 'componentType': 5125},
                                     'values': {'bufferView': view(b''.join(struct.pack('<3f', *v) for v in vals))}}})
        return len(accessors) - 1
    base = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]
    face = dense([(0, 2, 0), (1, 2, 0), (0, 3, 0)])
    pos = dense(base)
    ankle = sparse(4, [0], [(0.125, 0, 0)])
    knee = sparse(4, [1, 3], [(0, 0, 0.5), (0, -0.25, 2.0)])
    while len(binary) % 4: binary.append(0)
    document = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}], 'bufferViews': views,
                'accessors': accessors,
                'meshes': [{'name': 'Body', 'primitives': [{'attributes': {'POSITION': face}}]},
                           {'name': 'body_2', 'extras': {'targetNames': ['kisekae_Ankle', 'kisekae_Knee']},
                            'primitives': [{'attributes': {'POSITION': pos},
                                            'targets': [{'POSITION': ankle}, {'POSITION': knee}]}]}]}
    encoded = json.dumps(document).encode()
    encoded += b' ' * (-len(encoded) % 4)
    body = struct.pack('<I4s', len(encoded), b'JSON') + encoded + struct.pack('<I4s', len(binary), b'BIN\0') + bytes(binary)
    return struct.pack('<4sII', b'glTF', 2, len(body) + 12) + body, dict(pos=pos, ankle=ankle, knee=knee, face=face)


def gowr_rig(np, positions, parents):
    """Skeleton blob in the layout rig.parse_rig reads: local matrices (row-vector translation) after the bone table."""
    n = len(positions)
    mo = ((0x18 + n * 32 + 15) & ~15) + 0x50
    b = bytearray(mo + 128 * n)
    struct.pack_into('<H', b, 0x10, n)
    for i, (p, par) in enumerate(zip(positions, parents)):
        struct.pack_into('<h', b, 0x1E + 8 * i, par)
        local = np.eye(4)
        local[3, :3] = np.subtract(p, positions[par]) if par >= 0 else p
        struct.pack_into('<16f', b, mo + 64 * i, *local.reshape(-1))
    return bytes(b)


class GodOfWarRagnarokTools(unittest.TestCase):
    """Builder modules on synthetic data. A full build needs the game install, Blender fits and the source model."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding gowr ')
        self.root = Path(self.temp.name)
        for stem in gowr_names() if GOWR_KIT.is_dir() else ():   # fresh modules: charbuild caches part sizes
            sys.modules.pop(stem, None)

    def tearDown(self): self.temp.cleanup()

    @classmethod
    def tearDownClass(cls):
        for stem in gowr_names() if GOWR_KIT.is_dir() else ():
            sys.modules.pop(stem, None)

    def test_gowr_joint_layouts_roundtrip(self):
        mesh, enc, dec = gowr('mesh'), gowr('encode'), gowr('decode')
        import numpy as np
        P = np.array([[0.1, 1.2, -0.3], [0.5, 1.0, 0.25], [-0.4, 0.1, 0.0], [0.2, 1.5, 0.75]])
        N = np.array([[0, 0, 1.0], [0, 1.0, 0], [0.6, 0.8, 0], [0, -0.6, 0.8]])
        geo = dict(P=P, N=N, T=np.tile([1.0, 0, 0], (4, 1)), UV=np.zeros((4, 2)), IDX=np.array([[0, 1, 2], [2, 1, 3]]))
        def ramp(joints, first):                               # descending weights summing to 1
            ws = np.linspace(first, 1.0, len(joints)); ws /= ws.sum()
            return list(zip(joints, ws.tolist()))
        layouts = [  # joints component, weights component, influences carried, per-vertex influences
            ((9, 2, 4), (10, 2, 3), 10, [ramp([1447, 2000, 3, 4, 5, 6, 7, 8, 9, 10], 3.0),
                                         [(163, 0.5), (175, 0.3), (2047, 0.2)], [(318, 1.0)],
                                         ramp(list(range(20, 31)), 4.0)]),
            ((9, 2, 4), (10, 2, 2), 7, [ramp([3000, 2048, 1447, 12, 13, 14, 15], 3.0),
                                        [(65000, 0.75), (1, 0.25)], [(2500, 1.0)], ramp(list(range(40, 49)), 5.0)]),
            ((9, 4, 4), (10, 3, 1), 4, [ramp([1500, 2, 3, 4], 4.0), [(900, 0.6), (901, 0.4)], [(7, 1.0)],
                                        ramp(list(range(60, 66)), 3.0)]),
        ]
        for jc, wc, k, inf in layouts:
            with self.subTest(joints=jc, weights=wc):
                stride1 = mesh.DT_SIZE[jc[1]] * jc[2] + mesh.DT_SIZE[wc[1]] * wc[2]
                comps = [(0, 0, 3, 0, 0), (1, 3, 1, 12, 0), (*jc, 0, 1), (*wc, mesh.DT_SIZE[jc[1]] * jc[2], 1)]
                offs = [0, enc.align(4 * 16)]
                ind_off = enc.align(offs[1] + 4 * stride1)
                m = mesh.parse_mesh(gowr_mesh_def(comps, 4, 6, offs, ind_off))[0]
                self.assertEqual((m.strides, m.buf_offs, m.ind_off), ([16, stride1], offs, ind_off))
                self.assertEqual(enc.max_influences(m), k)
                buf = bytearray(ind_off + 16)
                enc.write_in_place(buf, m, dict(geo, INF=inf), None, None)
                out, idx = dec.decode(m, bytes(buf))
                self.assertEqual(np.array(idx).reshape(-1, 3).tolist(), geo['IDX'].tolist())
                self.assertTrue(np.array_equal(np.array(dec.pos_of(out))[:, :3], P.astype(np.float32)))
                normals = np.array([v[0][:3] for v in out[(1, 3, 1)]])
                self.assertLess(np.abs(normals - N).max(), 2 / 512)
                want = enc.limit_influences(inf, k)             # the 11-influence vertex keeps its 10/7/4 largest
                for vi, (got, exp) in enumerate(zip(dec.skin_of(m, out), want)):
                    gw = {}
                    for j, w in got:
                        gw[j] = gw.get(j, 0.0) + w
                    self.assertEqual({j for j, w in gw.items() if w > 0.002}, {j for j, _ in exp}, (vi, got))
                    self.assertLess(max(abs(gw[j] - w) for j, w in exp), 0.006)
                if wc == (10, 2, 2):                            # eight u16 slots: 7 joints, 8th zero, no 11-bit packing
                    raw = struct.unpack_from('<8H', buf, offs[1])
                    self.assertEqual(raw, (3000, 2048, 1447, 12, 13, 14, 15, 0))
                    raw = struct.unpack_from('<8H', buf, offs[1] + stride1)
                    self.assertEqual(raw, (65000, 1, 65000, 65000, 65000, 65000, 65000, 0))   # padded with joint 1

    def test_gowr_single_group_lodpack_roundtrip(self):
        bm, packs = gowr('build_mesh'), gowr('packs')
        import lz4.frame
        buffers = {0x2a5ef0f242a705b6: bytes(range(256)) * 3 + b'x', 0x167745b9b547165b: b'\x01' * 1000, 0x10: b'abc'}
        path = self.root / 'Mod Pack.lodpack'
        bm.write_lodpack_single_group(str(path), buffers)
        data, toc = path.read_bytes(), Path(str(path) + '.toc').read_bytes()
        head = 16 + 24 + 24 * len(buffers)
        self.assertEqual(struct.unpack_from('<IIQ', data, 0), (1, 3, 1 << 32))
        self.assertEqual((toc, len(data)), (data[:head], head + sum(map(len, buffers.values()))))
        lz = self.root / 'lz4.toc'
        lz.write_bytes(lz4.frame.compress(toc))
        for source in (path, Path(str(path) + '.toc'), lz):
            groups, members, _ = packs.read_lodpack_toc(str(source))
            self.assertEqual(groups, [(head, max(buffers), sum(map(len, buffers.values())))])
            self.assertEqual(set(members), set(buffers))
        offsets = [members[h][1] for h in sorted(buffers)]
        self.assertEqual(offsets, sorted(offsets))                 # members follow each other in hash order
        for h, b in buffers.items():
            gi, mo, size = members[h]
            self.assertEqual((gi, size, data[head + mo:head + mo + size]), (0, len(b), b))

    def test_gowr_slot_planning_and_fallback(self):
        cb = gowr('charbuild')
        import numpy as np
        geos = {'full': gowr_geo(np, {'a': 30, 'b': 20, 'c': 10}), '0.5': gowr_geo(np, {'a': 15, 'b': 10, 'c': 6})}
        levels = ['full', '0.5']
        # best common level first, then the leftover room upgrades parts in list order
        self.assertEqual(cb.fit_parts(['a', 'b'], levels, geos, 45, 1000), [('a', 'full'), ('b', '0.5')])
        self.assertIsNone(cb.fit_parts(['a', 'b'], levels, geos, 20, 1000))
        self.assertEqual(cb.fit_parts(['a'], levels, geos, 100, 50), [('a', '0.5')])    # index room decides
        groups = [dict(lods=[dict(dist=12.34, meshes=[7, 5])]),
                  dict(lods=[dict(dist=1.0, meshes=[9]), dict(dist=50.0, meshes=[])])]
        room = {5: (100, 1000), 7: (4, 1000), 9: (16, 1000)}
        plan, chosen = cb.plan_groups(groups, {0: [['a'], ['c']], 1: [['a', 'c']]}, room.__getitem__, geos)
        # slot 7 cannot hold even the coarsest 'c', so 'c' moves to the main slot 5
        self.assertEqual(plan, {5: ('mixed', [('a', 'full'), ('c', 'full')]), 9: ('mixed', [('a', '0.5')])})
        self.assertEqual(chosen[5], dict(group=0, lod=0, dist=12.3, room=(100, 1000),
                                         levels={'a': 'full', 'c': 'full'}, verts=40))
        self.assertEqual((chosen[9]['dropped'], chosen[9]['verts']), (['c'], 15))   # lowest priority dropped
        with self.assertRaises(SystemExit):
            cb.plan_groups(groups, {1: [['a']]}, {9: (3, 1000)}.__getitem__, geos)

    def test_gowr_fbx_roundtrip_and_edit(self):
        fb = gowr('fbxbin')
        import numpy as np
        pattern = [0.0, 1.0, 0.5] * 20
        for filler in range(16):                                   # covers the "already aligned: pad 16" footer
            with self.subTest(filler=filler):
                src, out = self.root / f'src{filler}.fbx', self.root / f'out{filler}.fbx'
                src.write_bytes(gowr_fbx(filler, pattern))
                fb.FBX(str(src)).save(str(out))
                self.assertEqual(out.read_bytes(), src.read_bytes())
        src = self.root / 'src0.fbx'
        f = fb.FBX(str(src))
        geo = f.objects()[0]
        self.assertEqual(geo.props[1].value(), b'body_2\x00\x01Geometry')
        vp = geo.find(b'Vertices')[0].props[0]
        self.assertEqual(vp.value().tolist(), pattern)
        new = np.random.default_rng(3).normal(size=len(pattern))   # less compressible: the file length changes
        vp.set_array(new)
        out = self.root / 'edited.fbx'
        f.save(str(out))
        self.assertNotEqual(out.stat().st_size, src.stat().st_size)
        g = fb.FBX(str(out))
        gp = g.objects()[0].find(b'Vertices')[0].props[0]
        self.assertTrue(np.array_equal(gp.value(), new))
        self.assertEqual(struct.unpack_from('<III', gp.raw)[1], 1)  # still zlib-compressed
        before = {c.name: [p.raw for p in c.props] for c in f.objects()[0].children if c.name != b'Vertices'}
        after = {c.name: [p.raw for p in c.props] for c in g.objects()[0].children if c.name != b'Vertices'}
        self.assertEqual(after, before)
        pad = len(g.tail) - 16 - 4 - 140
        self.assertTrue(0 <= pad <= 16)
        self.assertEqual((g.body_len + 20 + pad) % 16, 0)          # padding recomputed: ends on a 16-byte boundary
        self.assertEqual((g.tail[:20], g.tail[-140:]), (f.tail[:20], f.tail[-140:]))

    def test_gowr_bake_knee_vrm_sparse_target(self):
        bk, gu = gowr('bake_knee'), gowr('gltf_util')
        import numpy as np
        data, ai = gowr_glb()
        src, dst = self.root / 'model.vrm', self.root / 'baked.vrm'
        src.write_bytes(data)
        report = bk.bake_vrm(str(src), str(dst), ['kisekae_Knee'])
        self.assertEqual(src.read_bytes(), data)
        self.assertEqual(report['kisekae_Knee']['verts'], 2)
        self.assertTrue(report['position_bounds_updated'])
        g, g0 = gu.GLB(str(dst)), gu.GLB(str(src))
        self.assertTrue(np.allclose(g.read(ai['pos']), [[0, 0, 0], [1, 0, 0.5], [0, 1, 0], [1, 0.75, 2.0]]))
        idx, val = g.read_sparse(ai['knee'])
        self.assertEqual((idx.tolist(), np.abs(val).max()), ([1, 3], 0.0))     # indices kept, values zeroed
        acc = g.json['accessors']
        self.assertEqual((acc[ai['knee']]['min'], acc[ai['knee']]['max']), ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))
        self.assertEqual((acc[ai['pos']]['min'], acc[ai['pos']]['max']), ([0.0, 0.0, 0.0], [1.0, 1.0, 2.0]))
        for other in ('ankle', 'face'):                           # other target and other mesh untouched
            self.assertTrue(np.array_equal(g.read(ai[other]), g0.read(ai[other])))
            self.assertEqual(acc[ai[other]], g0.json['accessors'][ai[other]])

    def test_gowr_rigspec_mirror_stacked_joint(self):
        rs = gowr('rigspec')
        import numpy as np
        # GoW: +X is the character's right. Left knee: FK control 4 and deforming child 5 sit on one joint.
        pos = [(0, 1.0, 0), (0.1, 1.0, 0), (-0.1, 1.0, 0), (0.1, 0.5, 0), (-0.1, 0.5, 0), (-0.1, 0.5, 0),
               (0.1, 0.05, 0.02), (-0.1, 0.05, 0.02)]
        par = [-1, 0, 0, 1, 2, 4, 3, 5]
        rig = gowr_rig(np, pos, par)
        n, parents, P = rs.world(rig)
        self.assertEqual((n, parents), (8, par))
        self.assertTrue(np.allclose(P, pos, atol=1e-6))
        self.assertEqual(rs.mirror(P, 3, parents), 4)     # tie broken by the parent that mirrors bone 3's parent
        self.assertEqual(rs.mirror(P, 6, parents), 7)
        core = dict(Hips=0, Spine=0, Chest=0, Neck=0, Head=0)
        right = dict(hip=1, kn=3, an=6, Index=[3, 6])
        spec = rs.make_spec(rig, core, right)
        self.assertEqual(spec['Left'], dict(hip=2, kn=4, an=7, Index=[4, 7]))
        spec = rs.make_spec(rig, core, right, pad_joint=6, left_override=dict(kn=5))
        self.assertEqual(spec['Left'], dict(hip=2, kn=5, an=7, Index=[4, 7]))    # override only replaces its role
        self.assertEqual((spec['core'], spec['Right'], spec['pad_joint']), (core, right, 6))
        self.assertTrue(np.allclose(spec['joints'][6], [-0.1, 0.02, 0.05]))       # Blender (-x, z, y)
        json.dumps(spec)

    def test_gowr_game_folder_and_lazy_dll(self):
        gd = gowr('gamedir')
        from unittest import mock
        with mock.patch.dict(os.environ):
            os.environ.pop('GOWR_GAME', None)
            gd.set_game(None)
            with self.assertRaises(SystemExit) as cm:
                gd.wad_dir()
            self.assertIn('GOWR_GAME', str(cm.exception))
            gd.set_game(self.root / 'nowhere')
            with self.assertRaises(SystemExit) as cm:
                gd.game_root()
            self.assertIn('exec/wad/pc_le', str(cm.exception))
            game = self.root / 'game'
            (game / 'exec' / 'wad' / 'pc_le').mkdir(parents=True)
            os.environ['GOWR_GAME'] = str(game)
            gd.set_game(None)
            self.assertEqual(Path(gd.wad_dir()), game / 'exec' / 'wad' / 'pc_le')
            agc = gowr('agctex')                                   # imports without the game DLL
            self.assertIsNone(agc._api)
            self.assertEqual(agc.parse_tsharp(bytes(32))['width'], 1)
            with self.assertRaises(SystemExit) as cm:              # first real use looks for the DLL
                agc.AgcTexture(bytes(32))
            self.assertIn('libSceAgcTextureTool.dll', str(cm.exception))


HFW_DEPENDENCIES = ('numpy', 'scipy', 'PIL')
HFW_SHARED_NAMES = ('atlas', 'vrm')                       # same module names as the GoT kit


def hfw_missing():
    return [m for m in HFW_DEPENDENCIES if importlib.util.find_spec(m) is None]


def hfw(name):
    """HFW builder module; skipped with the install hint when the kit's extra requirements are absent."""
    if not (KITS / 'horizon-forbidden-west').is_dir():
        raise unittest.SkipTest('horizon-forbidden-west is not included in this single-game export')
    if hfw_missing():
        raise unittest.SkipTest('pip install -r portable-kits/horizon-forbidden-west/requirements.txt (missing '
                                + ', '.join(hfw_missing()) + ')')
    for shared in HFW_SHARED_NAMES:                        # build_hfw must import the HFW atlas / vrm
        sys.modules.pop(shared, None)
    return module('horizon-forbidden-west', name)


class HorizonForbiddenWestTools(unittest.TestCase):
    """Builder modules on synthetic data. A full build needs h2 exports of the game, the h2 tool and a VRM."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding hfw ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    @classmethod
    def tearDownClass(cls):
        for shared in HFW_SHARED_NAMES:
            sys.modules.pop(shared, None)

    @staticmethod
    def submesh(np, name, points, nuv=1, slots=4, bone=0):
        n = len(points)
        return dict(name=name, nuv=nuv, textures=[('tex_a', 0)], pos=np.asarray(points, float),
                    nrm=np.tile([0, 0, 1.0], (n, 1)), col=np.tile([255, 128, 0, 255], (n, 1)),
                    uv=[np.linspace(0, 1, 2 * n).reshape(n, 2) for _ in range(nuv)],
                    bi=[[bone] * slots for _ in range(n)], bw=[[1.0] + [0.0] * (slots - 1) for _ in range(n)],
                    faces=np.array([[0, 1, 2]]))

    def test_hfw_ascii_roundtrip(self):
        H = hfw('hfwascii')
        import numpy as np
        bones = [dict(name='hipsBone', parent=-1, pos=[0, 0, 1.0], quat=[0, 0, 0, 1]),
                 dict(name='C_Spine_sjnt_0', parent=0, pos=[0, 0.01, 1.1], quat=[0, 0, 0.5, 0.866025])]
        upper = self.submesh(np, 'b2c4_215_sm1', [[0.1, 0.2, 0.3], [0.4, -0.5, 0.6], [-0.7, 0.8, 0.9]],
                             nuv=3, slots=8, bone=1)
        upper['bi'] = [[1, 0, 1, 1, 1, 1, 1, 1]] * 3
        upper['bw'] = [[0.5, 0.25, 0.25] + [0.0] * 5] * 3
        meshes = [self.submesh(np, 'b2c4_215_sm0', np.eye(3)), upper]
        path = self.root / 'lod0_215.ascii'
        H.write(path, meshes, bones=bones)
        text = path.read_bytes()
        self.assertNotIn(b'\r', text)                         # the h2 tool reads LF text
        self.assertNotIn(b'nan', text.lower())
        back_bones, back = H.read_meshes(path, has_skeleton=True)
        self.assertEqual([(b['name'], b['parent']) for b in back_bones], [('hipsBone', -1), ('C_Spine_sjnt_0', 0)])
        self.assertEqual([b['name'] for b in H.read_skeleton(path)], ['hipsBone', 'C_Spine_sjnt_0'])
        for m, r in zip(meshes, back):
            self.assertEqual((r['name'], r['nuv'], r['textures']), (m['name'], m['nuv'], m['textures']))
            self.assertLess(np.abs(r['pos'] - m['pos']).max(), 1e-6)
            self.assertTrue(np.array_equal(r['col'], m['col']))
            for u in range(m['nuv']):
                self.assertLess(np.abs(r['uv'][u] - m['uv'][u]).max(), 1e-6)
            self.assertEqual(r['bi'], m['bi'])
            self.assertLess(np.abs(np.array(r['bw']) - np.array(m['bw'])).max(), 1e-6)
            self.assertTrue(np.array_equal(r['faces'], m['faces']))

    def test_hfw_core_patch_and_refusal(self):
        H = hfw('hfwascii')
        import numpy as np
        script = KITS / 'horizon-forbidden-west/scripts/patch_bounds.py'
        consts = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(script.read_text(encoding='utf-8')).body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in ('BOXES', 'CS_NBT')}
        core = bytearray(4096)
        box_at, nbt_at, o = {}, {}, 64
        for name, (mn, _) in consts['BOXES'].items():
            struct.pack_into('<6f', core, o, *mn, *(np.array(mn) + 0.25))
            box_at[name], o = o, o + 64
        for name, (vc, nbt) in consts['CS_NBT'].items():
            struct.pack_into('<I', core, o, 7)                # SkinInfo type 24 bytes before the count pair
            struct.pack_into('<ii', core, o + 24, vc, nbt)
            nbt_at[name], o = o + 24, o + 64
        bones = [dict(name='hipsBone', parent=-1, pos=[0, 0, 0], quat=[0, 0, 0, 1])]
        karin = {('lod0_215.ascii', 1): [[-2.0, 0.1, 1.2], [0.3, 0.2, 1.3], [0.1, -0.3, 2.4]],
                 ('lod0_260.ascii', 0): [[1.5, 0.9, -0.5], [0.1, 0.1, 0.2], [0.0, 0.0, 0.9]],
                 ('lod0_625.ascii', 0): [[0.3, 0.4, 2.5], [-0.1, 0.0, 1.5], [0.0, 0.1, 1.6]]}
        (self.root / 'ascii').mkdir()
        for f in sorted({f for f, _ in karin}):
            subs = [self.submesh(np, f'sm{i}', karin.get((f, i), np.eye(3))) for i in range(2)]
            H.write(self.root / 'ascii' / f, subs, bones=bones)
        path = self.root / '02_19A7C73A.core'
        path.write_bytes(bytes(core))
        cli('horizon-forbidden-west', 'patch_bounds', path, self.root)
        out = path.read_bytes()
        for name, (mn, content) in consts['BOXES'].items():
            pts = np.concatenate([np.array(karin[(f, i)]) for f, i in content])
            want_min = np.minimum(mn, pts.min(0) - 0.02)
            want_max = np.maximum(np.array(mn) + 0.25, pts.max(0) + 0.02)
            got = np.array(struct.unpack_from('<6f', out, box_at[name]))
            with self.subTest(box=name):
                self.assertLess(np.abs(got - np.r_[want_min, want_max]).max(), 1e-5)
        for name, (vc, nbt) in consts['CS_NBT'].items():
            with self.subTest(skininfo=name):
                self.assertEqual(struct.unpack_from('<I', out, nbt_at[name] - 24)[0], 5)
                self.assertEqual(struct.unpack_from('<ii', out, nbt_at[name]), (vc, -1))
        bad = bytearray(core)                                 # one part is not CsNbtGen: refuse, file untouched
        struct.pack_into('<I', bad, next(iter(nbt_at.values())) - 24, 6)
        path.write_bytes(bytes(bad))
        process = cli('horizon-forbidden-west', 'patch_bounds', path, self.root, ok=False)
        self.assertIn('expected 7', process.stdout + process.stderr)
        self.assertEqual(path.read_bytes(), bytes(bad))

    def test_hfw_weight_quantize_and_cover_test(self):
        bh = hfw('build_hfw')
        import numpy as np
        acc = np.array([[0.1, 0.6, 0.0, 0.3, 0.001], [0, 0, 1.0, 0, 0]])
        bi, bw = bh.quantize(acc, 2)
        self.assertEqual(bi[0].tolist(), [1, 3])
        self.assertLess(np.abs(bw[0] - [0.6 / 0.9, 0.3 / 0.9]).max(), 1e-12)
        self.assertEqual((int(bi[1][0]), bw[1].tolist()), (2, [1.0, 0.0]))
        with self.assertRaises(ValueError):
            bh.quantize(np.zeros((1, 3)), 2)
        c = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
        quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        tri = np.array([[c[a], c[b], c[d]] for a, b, _, d in quads] + [[c[b], c[e], c[d]] for _, b, e, d in quads])
        P = np.array([[0, 0, 0.0], [0.2, 0.1, 0.0], [3.0, 0, 0]])
        N = np.array([[1.0, 0, 0], [0, 0, 1.0], [1.0, 0, 0]])
        self.assertEqual(bh.enclosed(P, N, tri, dist=1.5).tolist(), [True, True, False])
        self.assertEqual(bh.enclosed(P[:1], N[:1], tri, dist=0.5).tolist(), [False])   # cover farther than dist

    def test_hfw_atlas_mask_merge_keeps_separate_islands(self):
        atlas = hfw('atlas')
        import numpy as np
        from PIL import Image
        img = Image.new('RGBA', (64, 64), (90, 120, 150, 255))
        # two triangles whose bounding boxes overlap but whose footprints do not touch
        uv = np.array([[0.1, 0.1], [0.6, 0.1], [0.1, 0.6], [0.9, 0.9], [0.4, 0.9], [0.9, 0.4]])
        items = [dict(img=img, uv=uv, tris=np.array([[0, 1, 2], [3, 4, 5]]), key='a')]
        self.assertEqual(atlas.build_page(items, (128, 128))[2]['pieces'], 1)
        page, uvs, info = atlas.build_page(items, (128, 128), mask_merge=True)
        self.assertEqual(info['pieces'], 2)
        self.assertEqual(page.size, (128, 128))
        # a mirrored copy on the same footprint still shares one piece
        twin = [dict(img=img, uv=uv[:3].copy(), tris=np.array([[0, 1, 2]]), key='a'),
                dict(img=img, uv=uv[:3].copy(), tris=np.array([[0, 2, 1]]), key='a')]
        page, uvs, info = atlas.build_page(twin, (128, 128), mask_merge=True)
        self.assertEqual(info['pieces'], 1)
        self.assertLess(np.abs(uvs[0] - uvs[1]).max(), 1e-12)

    def test_hfw_pose_fk_keeps_pivots(self):
        pp = hfw('pose_preview')
        import numpy as np
        sk = [dict(name='root', parent=-1, pos=[0, 0, 0], quat=[0, 0, 0, 1]),
              dict(name='arm', parent=0, pos=[0, 0, 1.0], quat=[0, 0, 0, 1]),
              dict(name='hand', parent=1, pos=[0, 0, 2.0], quat=[0, 0, 0, 1])]
        M = pp.fk(sk, {'arm': pp.rot([1, 0, 0], 90)})
        self.assertTrue(np.allclose(M[0], np.eye(4)))
        self.assertTrue(np.allclose(M[1] @ [0, 0, 1.0, 1], [0, 0, 1.0, 1]))          # rotation about its own pivot
        self.assertTrue(np.allclose(M[2] @ [0, 0, 2.0, 1], [0, -1.0, 1.0, 1]))       # child follows
        m = dict(pos=np.array([[0, 0, 2.0]]), bi=[[2, 0]], bw=[[0.5, 0.5]])
        self.assertTrue(np.allclose(pp.skin(m, M), [[0, -0.5, 1.5]]))


class MK1Tools(unittest.TestCase):
    def test_mk1_synthetic_suite_and_cli(self):
        scripts = ROOT/'games/mortal-kombat-1/scripts'
        if not scripts.is_dir():
            self.skipTest('MK1 is not included in this single-game export')
        process = subprocess.run(
            [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(scripts), '-p', 'test_*.py'],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stdout+'\n'+process.stderr)
        self.assertIn('Ran 18 tests', process.stderr)
        for name in ('mk1_checks.py', 'psk_index_plan.py', 'atlas_quadrants.py'):
            process = subprocess.run([sys.executable, '-B', str(scripts/name), '--help'],
                                     cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stdout+'\n'+process.stderr)


WD_DEPENDENCIES = ('numpy',)
WD_STDLIB_SCRIPTS = ('xbt_tool', 'audit_xbt_templates', 'build_xbt_pair', 'extract_fat8', 'repack_fat8')
# synthetic char01-like skeleton: name, parent index, local translation (identity rotations)
WD_NODES = (('char01', -1, (0, 0, 0)), ('Pelvis', 0, (0, 0, 1.0)), ('Spine', 1, (0, 0, 0.1)), ('Spine1', 2, (0, 0, 0.1)),
            ('Spine2', 3, (0, 0, 0.1)), ('Neck', 4, (0, 0, 0.15)), ('Head', 5, (0, 0.02, 0.1)), ('L_Eye', 6, (-0.03, 0.08, 0.06)),
            ('R_Eye', 6, (0.03, 0.08, 0.06)), ('L Clavicle', 4, (-0.02, 0, 0.12)), ('L UpperArm', 9, (-0.16, 0, 0)),
            ('L Forearm', 10, (-0.28, 0, 0)))
WD_MATERIALS = ('graphics\\_synthetic\\synthetic_head.material.bin', 'graphics\\_synthetic\\synthetic_coat.material.bin')


def wd_missing(pil=False):
    return [m for m in WD_DEPENDENCIES + (('PIL',) if pil else ()) if importlib.util.find_spec(m) is None]


def wd(name, pil=False):
    """Watch Dogs XBG/XBT module; skipped with the install hint when numpy (and Pillow) are absent."""
    if not (KITS / 'watch-dogs' / 'scripts' / 'xbg_codec.py').is_file():
        raise unittest.SkipTest('watch-dogs is not included in this single-game export')
    if wd_missing(pil):
        raise unittest.SkipTest('pip install -r requirements.txt -r portable-kits/watch-dogs/requirements.txt (missing '
                                + ', '.join(wd_missing(pil)) + ')')
    return module('watch-dogs', name)


def wd_entry(text, h=0):
    raw = text.encode() + b'\0'
    return struct.pack('<II', h, len(raw)) + raw + b'\0' * (-len(raw) % 4)


def wd_submesh(np, codec, material, vertex_type, bones, lift=0.0):
    """Triangle fan with max(3, len(bones)) vertices; vertex i is fully weighted to bones[i % len(bones)]."""
    n = max(3, len(bones))
    angle = np.linspace(0, np.pi, n)
    pos = np.c_[0.1 * np.cos(angle), np.full(n, 0.05), 1.2 + lift + 0.1 * np.sin(angle)]
    w = np.zeros((n, 4), np.uint8)
    w[:, 0] = 255
    b = np.full((n, 4), -1, np.int64)
    b[:, 0] = [bones[i % len(bones)] for i in range(n)]
    uv = np.c_[np.linspace(0, 1, n), np.linspace(1, 0, n)]
    return codec.Submesh(material, vertex_type, pos, np.tile([0, 1.0, 0], (n, 1)), uv, np.zeros((n, 2)),
                         np.tile(np.array([254, 254, 254, 255], np.uint8), (n, 1)), w, b,
                         np.array([[0, i + 1, i] for i in range(1, n - 1)]))


def wd_template(path, palette_len=2):
    """Write a synthetic char01-like template XBG: 2 material slots, WD_NODES, inverse binds and a filler block."""
    import numpy as np
    xm, codec = wd('xbg_model'), wd('xbg_codec')
    out = bytearray(0x8C)
    out[:4] = b'MOEG'
    out += struct.pack('<I', len(WD_MATERIALS)) + b''.join(wd_entry(m) for m in WD_MATERIALS)
    out += struct.pack('<I', 2) + wd_entry('head') + struct.pack('<I', 0) + wd_entry('coat') + struct.pack('<I', 1)
    out += struct.pack('<I', 1) + wd_entry('char01', 0xCC97FA4A) + struct.pack('<I', 1)
    palette_offset = len(out)
    palette = list(range(palette_len))
    out += struct.pack('<I', palette_len) + struct.pack(f'<{palette_len}H', *palette) + b'\0' * (2 * palette_len % 4)
    out += struct.pack('<II', 1, len(WD_NODES))
    world, nodes = [], []
    for b, (name, parent, t) in enumerate(WD_NODES):
        out += struct.pack('<I7f2H', 0x64, *t, 0, 0, 0, 1, parent & 0xFFFF, b) + wd_entry(name)
        world.append(np.array(t, float) + (world[parent] if parent >= 0 else 0))
        nodes.append({'name': name, 'parent': parent & 0xFFFF, 'b': b, 'xf': (*t, 0, 0, 0, 1), 'flags': 0x64})
    nodes_end = len(out)
    out += struct.pack('<II', len(WD_NODES), len(WD_NODES))
    out += b'\0' * (-len(out) % 16)
    for p in world:
        inv = np.eye(4)
        inv[:3, 3] = -p
        out += inv.T.astype('<f4').tobytes()  # row-vector layout, as stored by the game
    out += b'SYNTHETIC-PHYSICS-BLOCK.' * 2
    fake = xm.Xbg(bytes(out), palette, palette_offset, nodes, len(out))
    fake.nodes_end = nodes_end
    lod = [wd_submesh(np, codec, 0, 0x17BA, [6]), wd_submesh(np, codec, 1, 0x179A, [1, 2], lift=-0.5)]
    path.write_bytes(codec.encode(fake, [lod, lod]))
    return xm.load(path)


def wd_fbx(path, bone='Head', material='synthetic_coat.material.bin'):
    """Minimal binary FBX 7400: two skinned LOD quads (Body_LOD0/1) with one material and one bone."""
    def prop(v):
        if isinstance(v, str):
            raw = v.encode()
            return b'S' + struct.pack('<I', len(raw)) + raw
        if isinstance(v, int):
            return b'L' + struct.pack('<q', v)
        kind, values = v
        data = struct.pack(f'<{len(values)}{kind}', *values)
        return kind.encode() + struct.pack('<III', len(values), 0, len(data)) + data

    def node(offset, name, props=(), children=()):
        body = b''.join(prop(p) for p in props)
        start = offset + 13 + len(name) + len(body)
        kids = b''
        for child in children:
            kids += node(start + len(kids), *child)
        if children:
            kids += b'\0' * 13
        return struct.pack('<III', start + len(kids), len(props), len(body)) + bytes([len(name)]) + name.encode() + body + kids

    mat, limb = 900, 901
    objects = [('Material', (mat, material + '\x00\x01Material', '')), ('Model', (limb, bone + '\x00\x01Model', 'LimbNode'))]
    conns = []
    for k, model in enumerate((100, 200)):
        geom, skin, cluster = model + 1, model + 2, model + 3
        objects += [
            ('Geometry', (geom, f'Body_LOD{k}\x00\x01Geometry', 'Mesh'), [
                ('Vertices', (('d', [0, 0, 1, 0.1, 0, 1, 0.1, 0, 1.2, 0, 0, 1.2]),)),
                ('PolygonVertexIndex', (('i', [0, 1, 2, -4]),)),
                ('LayerElementNormal', (0,), [('MappingInformationType', ('ByPolygonVertex',)),
                                              ('ReferenceInformationType', ('Direct',)), ('Normals', (('d', [0, -1, 0] * 4),))]),
                ('LayerElementUV', (0,), [('Name', ('UVMap',)), ('MappingInformationType', ('ByPolygonVertex',)),
                                          ('ReferenceInformationType', ('Direct',)), ('UV', (('d', [0, 0, 1, 0, 1, 1, 0, 1]),))]),
                ('LayerElementMaterial', (0,), [('MappingInformationType', ('AllSame',)),
                                                ('ReferenceInformationType', ('IndexToDirect',)), ('Materials', (('i', [0]),))])]),
            ('Model', (model, f'Body_LOD{k}\x00\x01Model', 'Mesh')),
            ('Deformer', (skin, 'Skin\x00\x01Deformer', 'Skin')),
            ('Deformer', (cluster, 'Cluster\x00\x01SubDeformer', 'Cluster'),
             [('Indexes', (('i', [0, 1, 2, 3]),)), ('Weights', (('d', [1.0] * 4),))])]
        conns += [('C', ('OO', geom, model)), ('C', ('OO', mat, model)), ('C', ('OO', skin, geom)),
                  ('C', ('OO', cluster, skin)), ('C', ('OO', limb, cluster))]
    data = b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400)
    for top in (('Objects', (), objects), ('Connections', (), conns)):
        data += node(len(data), *top)
    path.write_bytes(data + b'\0' * 13)


def wd_fat(folder, blobs):
    """Uncompressed FAT v8 / DAT pair with entries sorted by hash, each file 16-byte aligned."""
    dat, entries = bytearray(), bytearray()
    for h in sorted(blobs):
        dat += b'\0' * (-len(dat) % 16)
        entries += struct.pack('<4I', h, 0, len(blobs[h]), len(dat) >> 3)
        dat += blobs[h]
    fat = folder / 'pack.fat'
    fat.write_bytes(b'3TAF' + struct.pack('<3I', 8, 0, len(blobs)) + bytes(entries) + b'\0' * 8)
    fat.with_suffix('.dat').write_bytes(bytes(dat))
    return fat


class WatchDogsXbgTools(unittest.TestCase):
    """ZModeler-free XBG writer, skeleton patch, FAT v8 and texconv-free XBT on synthetic data."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding wd ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_wd_xbg_palette_growth_keeps_matrix_table_aligned(self):
        import numpy as np
        xm, codec, skel = wd('xbg_model'), wd('xbg_codec'), wd('xbg_skeleton')
        template = wd_template(self.root / 'template.xbg')
        tpl_table = (template.nodes_end + 8 + 15) & ~15
        self.assertEqual(tpl_table % 16, 0)
        block = template.data[tpl_table:template.lod_offset]
        self.assertEqual(len(template.palette), 3)
        # palettes of 1, 3, 7 and 10 bones move the node table end by -4, 0, +8 and +12 bytes against the template's 3;
        # +8 is the in-game crash case (66 -> 70 bones) when the template padding was copied verbatim
        for bones in ([6], [1, 2, 6], list(range(1, 8)), list(range(1, 11))):
            with self.subTest(palette=len(bones)):
                lods = [[wd_submesh(np, codec, 1, 0x179A, bones)]] * 2
                path = self.root / f'palette_{len(bones)}.xbg'
                path.write_bytes(codec.encode(template, lods))
                x = xm.load(path)
                table = (x.nodes_end + 8 + 15) & ~15
                self.assertEqual(sorted(x.palette), sorted(bones))
                self.assertFalse(any(x.data[x.nodes_end + 8:table]))
                self.assertEqual(x.data[table:x.lod_offset], block)  # the inverse binds start on the 16-byte boundary
                sk = skel.Skeleton(path)
                worst = max(np.abs(sk.bind[n] @ sk.inv_bind[b] - np.eye(4)).max() for b, n in sk.node_of_b.items())
                self.assertLess(worst, 1e-6)
                scale, back = codec.decode(x)
                for want, got in zip(lods, back):
                    self.assertTrue(np.array_equal(want[0].triangles, got[0].triangles))
                    self.assertTrue(np.array_equal(want[0].weights, got[0].weights))
                    self.assertTrue(np.array_equal(np.where(want[0].weights > 0, want[0].bones, -1), got[0].bones))
                    # ZModeler quantization (int)(x / scale + 0.5) truncates toward zero, so negatives err by up to 1.5 steps
                    self.assertLessEqual(np.abs(want[0].positions - got[0].positions).max(), 1.5 * scale)

    def test_wd_fbx_to_xbg_cli_readback_and_conventions(self):
        import numpy as np
        xm, codec = wd('xbg_model'), wd('xbg_codec')
        template, fbx, out = self.root / 'template.xbg', self.root / 'karin.fbx', self.root / 'out' / 'char01.xbg'
        wd_template(template)
        wd_fbx(fbx)
        result = cli('watch-dogs', 'build_xbg_from_fbx', '--fbx', fbx, '--template-xbg', template, '--output', out,
                     '--report', self.root / 'report.json')
        self.assertIn('READBACK PASS', result.stdout)
        cli('watch-dogs', 'build_xbg_from_fbx', '--fbx', fbx, '--template-xbg', template, '--output', out, ok=False)
        cli('watch-dogs', 'build_xbg_from_fbx', '--fbx', fbx, '--template-xbg', template, '--output', template, '--force', ok=False)
        x = xm.load(out)
        _, lods = codec.decode(x)
        self.assertEqual(len(lods), 2)
        sub = lods[0][0]
        self.assertEqual((sub.material, sub.vertex_type), (1, 0x179A))  # FBX material name -> template slot
        expected = {(0.0, 0.0, 1.0), (-0.1, 0.0, 1.0), (-0.1, 0.0, 1.2), (0.0, 0.0, 1.2)}  # (-x, -y, z)
        self.assertEqual({tuple(np.round(p, 4) + 0.0) for p in sub.positions}, expected)
        self.assertEqual(len(sub.triangles), 2)
        head_b = next(n['b'] for n in x.nodes if n['name'] == 'Head')
        self.assertTrue(np.all(sub.bones[:, 0] == head_b) and np.all(sub.weights[:, 0] == 255))
        # the CCW FBX fan is stored CW: the geometric normal points against the stored normal
        tri = sub.positions[sub.triangles[0]]
        self.assertLess(np.cross(tri[1] - tri[0], tri[2] - tri[0]) @ sub.normals[sub.triangles[0][0]], 0)
        self.assertTrue(np.allclose(sorted(sub.uv0[:, 1]), [0, 0, 1, 1], atol=1e-4))

    def test_wd_skeleton_patch_moves_joint_and_children(self):
        import numpy as np
        skel = wd('xbg_skeleton')
        src, targets, out = self.root / 'template.xbg', self.root / 'targets.json', self.root / 'narrow.xbg'
        wd_template(src)
        before = skel.Skeleton(src)
        new = before.head('L UpperArm') + np.array([0.04, 0, 0])  # 4 cm shorter clavicle
        targets.write_text(json.dumps({'L UpperArm': new.tolist()}))
        report = json.loads(cli('watch-dogs', 'xbg_skeleton_patch', src, targets, out).stdout)
        self.assertEqual(report['moved_nodes'], 2)  # L UpperArm and its child L Forearm
        after = skel.Skeleton(out)
        self.assertTrue(np.allclose(after.head('L UpperArm'), new, atol=1e-6))
        self.assertTrue(np.allclose(after.head('L Forearm') - before.head('L Forearm'), [0.04, 0, 0], atol=1e-6))
        self.assertTrue(np.allclose(after.head('Head'), before.head('Head')))
        worst = max(np.abs(after.bind[n] @ after.inv_bind[b] - np.eye(4)).max() for b, n in after.node_of_b.items())
        self.assertLess(worst, 1e-6)
        cli('watch-dogs', 'xbg_skeleton_patch', src, targets, out, ok=False)
        targets.write_text(json.dumps({'No Such Bone': [0, 0, 0]}))
        cli('watch-dogs', 'xbg_skeleton_patch', src, targets, self.root / 'bad.xbg', ok=False)

    def test_wd_fat8_repack_replace_and_extract(self):
        if not (KITS / 'watch-dogs' / 'scripts' / 'repack_fat8.py').is_file():
            raise unittest.SkipTest('watch-dogs is not included in this single-game export')
        repack = module('watch-dogs', 'repack_fat8')
        self.assertEqual(repack.path_hash('graphics/characters/char/char01/char01.xbg'), 0xE886A8DB)
        coat = repack.path_hash('graphics/_synthetic/coat.xbt')
        blobs = {0x10: b'MOEG' + b'\1' * 21, coat: b'TBX\0' + b'\2' * 40, 0xFFFFFFF0: b'other' * 3}
        src = wd_fat(self.root, blobs)
        replacement, texture = self.root / 'new.xbg', self.root / 'new.xbt'
        replacement.write_bytes(b'MOEG' + b'\3' * 50)
        texture.write_bytes(b'TBX\0' + b'\4' * 9)
        out = self.root / 'out' / 'pack.fat'
        cli('watch-dogs', 'repack_fat8', src, out, f'00000010={replacement}', f'graphics/_synthetic/coat.xbt={texture}')
        cli('watch-dogs', 'repack_fat8', src, out, ok=False)
        cli('watch-dogs', 'repack_fat8', src, self.root / 'x.fat', f'00000099={replacement}', ok=False)
        cli('watch-dogs', 'extract_fat8', out, self.root / 'ex')
        self.assertEqual((self.root / 'ex' / '00000010.xbg').read_bytes(), replacement.read_bytes())
        self.assertEqual((self.root / 'ex' / f'{coat:08X}.xbt').read_bytes(), texture.read_bytes())
        self.assertEqual((self.root / 'ex' / 'FFFFFFF0.bin').read_bytes(), blobs[0xFFFFFFF0])
        cli('watch-dogs', 'extract_fat8', out, self.root / 'ex', ok=False)
        fat = out.read_bytes()
        offsets = [struct.unpack_from('<I', fat, 16 + 16 * i + 12)[0] << 3 for i in range(3)]
        self.assertEqual([o % 16 for o in offsets], [0, 0, 0])
        self.assertEqual(fat[16 + 48:], src.read_bytes()[16 + 48:])  # trailer kept

    def test_wd_xbt_encode_keeps_donor_layout(self):
        wd('xbt_encode', pil=True)
        from PIL import Image
        donor = bytearray(xbt(dds(8, 8, mips=4, payload=bytes(56))))  # DXT1 8x8: 32 + 8 + 8 + 8 bytes
        struct.pack_into('<I', donor, 48 + 80, 4)  # DDPF_FOURCC
        donor_path, png, out = self.root / 'donor.xbt', self.root / 'source.png', self.root / 'out.xbt'
        donor_path.write_bytes(bytes(donor))
        Image.new('RGB', (16, 16), (200, 40, 90)).save(png)
        result = cli('watch-dogs', 'xbt_encode', png, donor_path, out)
        self.assertIn("'mips': 4", result.stdout)
        data = out.read_bytes()
        self.assertEqual(len(data), len(donor))
        self.assertEqual(data[:48 + 128], bytes(donor[:48 + 128]))
        self.assertNotEqual(data[48 + 128:], bytes(56))
        cli('watch-dogs', 'xbt_encode', png, donor_path, out, ok=False)

if __name__ == '__main__': unittest.main(verbosity=2)
