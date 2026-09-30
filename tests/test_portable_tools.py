"""Synthetic fixtures only. No game installation or private model is required."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

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


if __name__ == '__main__': unittest.main(verbosity=2)
