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
            if path.parents[1].name == 'rise-of-the-ronin' and path.stem in RONIN_NUMPY_SCRIPTS and ronin_missing(): continue
            if path.parents[1].name == 'dragons-dogma-2' and path.stem in DD2_NUMPY_SCRIPTS and dd2_missing(): continue
            if path.parents[1].name == 'sifu' and sifu_missing(path.stem): continue
            if path.parents[1].name == 'marvels-spider-man-2' and sm2_missing(path.stem): continue
            if path.parents[1].name == 'days-gone' and dg_missing(path.stem): continue
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
WD_STDLIB_SCRIPTS = ('xbt_tool', 'audit_xbt_templates', 'build_xbt_pair', 'extract_fat8', 'repack_fat8',
                     'char01_paths', 'package_mod')
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


def wd_template(path, palette_len=2, nodes_spec=WD_NODES, materials=WD_MATERIALS, slots=((0, 0x17BA, 6), (1, 0x179A, (1, 2))),
                physics=None):
    """Write a synthetic char01-like template XBG: material slots, nodes (name, parent, local t), inverse binds,
    a physics block (physics(file offset) -> bytes, or a filler) and one LOD submesh per (slot, vertex type, bones)."""
    import numpy as np
    xm, codec = wd('xbg_model'), wd('xbg_codec')
    out = bytearray(0x8C)
    out[:4] = b'MOEG'
    out += struct.pack('<I', len(materials)) + b''.join(wd_entry(m) for m in materials)
    out += struct.pack('<I', len(materials)) + b''.join(
        wd_entry(m.split('\\')[-1].split('.')[0]) + struct.pack('<I', i) for i, m in enumerate(materials))
    out += struct.pack('<I', 1) + wd_entry('char01', 0xCC97FA4A) + struct.pack('<I', 1)
    palette_offset = len(out)
    palette = list(range(palette_len))
    out += struct.pack('<I', palette_len) + struct.pack(f'<{palette_len}H', *palette) + b'\0' * (2 * palette_len % 4)
    out += struct.pack('<II', 1, len(nodes_spec))
    world, nodes = [], []
    for b, (name, parent, t) in enumerate(nodes_spec):
        out += struct.pack('<I7f2H', 0x64, *t, 0, 0, 0, 1, parent & 0xFFFF, b) + wd_entry(name)
        world.append(np.array(t, float) + (world[parent] if parent >= 0 else 0))
        nodes.append({'name': name, 'parent': parent & 0xFFFF, 'b': b, 'xf': (*t, 0, 0, 0, 1), 'flags': 0x64})
    nodes_end = len(out)
    out += struct.pack('<II', len(nodes_spec), len(nodes_spec))
    out += b'\0' * (-len(out) % 16)
    for p in world:
        inv = np.eye(4)
        inv[:3, 3] = -p
        out += inv.T.astype('<f4').tobytes()  # row-vector layout, as stored by the game
    out += physics(len(out)) if physics else b'SYNTHETIC-PHYSICS-BLOCK.' * 2
    fake = xm.Xbg(bytes(out), palette, palette_offset, nodes, len(out))
    fake.nodes_end = nodes_end
    lod = [wd_submesh(np, codec, slot, vtype, list(bones) if isinstance(bones, tuple) else [bones], lift=-0.5 * (i > 0))
           for i, (slot, vtype, bones) in enumerate(slots)]
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

# synthetic char01 template for the VRM builder: (name, parent, world position), identity rotations, arms in an A-pose
WD_HUMAN_WORLD = (
    ('char01', -1, (0, 0, 0)), ('Pelvis', 0, (0, 0, 1.0)), ('Spine', 1, (0, 0, 1.1)), ('Spine1', 2, (0, 0, 1.2)),
    ('Spine2', 3, (0, 0, 1.3)), ('Neck', 4, (0, 0, 1.5)), ('Head', 5, (0, 0.02, 1.6)),
    ('L_Eye', 6, (-0.03, 0.08, 1.68)), ('R_Eye', 6, (0.03, 0.08, 1.68)),
    ('L Clavicle', 4, (-0.02, 0, 1.42)), ('L UpperArm', 9, (-0.18, 0, 1.42)), ('L Forearm', 10, (-0.36, 0, 1.24)),
    ('L Hand', 11, (-0.53, 0, 1.07)),
    ('R Clavicle', 4, (0.02, 0, 1.42)), ('R UpperArm', 13, (0.18, 0, 1.42)), ('R Forearm', 14, (0.36, 0, 1.24)),
    ('R Hand', 15, (0.53, 0, 1.07)),
    ('L Thigh', 1, (-0.1, 0, 0.95)), ('L Calf', 17, (-0.1, 0, 0.5)), ('L Foot', 18, (-0.1, 0, 0.08)),
    ('L Toe', 19, (-0.1, 0.12, 0.02)),
    ('R Thigh', 1, (0.1, 0, 0.95)), ('R Calf', 21, (0.1, 0, 0.5)), ('R Foot', 22, (0.1, 0, 0.08)),
    ('R Toe', 23, (0.1, 0.12, 0.02)))
WD_HUMAN_MATERIALS = tuple(f'graphics\\_synthetic\\{s}.material.bin' for s in ('head', 'coat', 'hair', 'lashes'))
# synthetic VRM 1.0 (glTF: left = +X, up = +Y, forward = +Z): name, parent, world position, humanoid bone, material
WD_VRM_NODES = (
    ('Armature', -1, (0, 0, 0), None, None), ('Hips', 0, (0, 0.60, 0), 'hips', 'Cloth'),
    ('Spine', 1, (0, 0.70, 0), 'spine', 'Body'), ('Chest', 2, (0, 0.80, 0), 'chest', 'Cloth'),
    ('Neck', 3, (0, 0.95, 0), 'neck', 'Body'), ('Head', 4, (0, 1.00, 0), 'head', 'Face'),
    ('EyeL', 5, (0.03, 1.08, 0.05), 'leftEye', 'Lashes'), ('EyeR', 5, (-0.03, 1.08, 0.05), 'rightEye', 'Face'),
    ('ShoulderL', 3, (0.03, 0.92, 0), 'leftShoulder', 'Body'), ('UpperArmL', 8, (0.10, 0.92, 0), 'leftUpperArm', 'Body'),
    ('LowerArmL', 9, (0.30, 0.92, 0), 'leftLowerArm', 'Body'), ('HandL', 10, (0.50, 0.92, 0), 'leftHand', 'Body'),
    ('ThumbL1', 11, (0.52, 0.91, 0.02), 'leftThumbMetacarpal', 'Body'),
    ('ThumbL2', 12, (0.54, 0.90, 0.03), 'leftThumbProximal', 'Body'),
    ('ShoulderR', 3, (-0.03, 0.92, 0), 'rightShoulder', 'Body'), ('UpperArmR', 14, (-0.10, 0.92, 0), 'rightUpperArm', 'Body'),
    ('LowerArmR', 15, (-0.30, 0.92, 0), 'rightLowerArm', 'Body'), ('HandR', 16, (-0.50, 0.92, 0), 'rightHand', 'Body'),
    ('UpperLegL', 1, (0.08, 0.58, 0), 'leftUpperLeg', 'Body'), ('LowerLegL', 18, (0.08, 0.32, 0), 'leftLowerLeg', 'Body'),
    ('FootL', 19, (0.08, 0.05, 0), 'leftFoot', 'Body'), ('ToesL', 20, (0.08, 0.0, 0.08), 'leftToes', 'Body'),
    ('UpperLegR', 1, (-0.08, 0.58, 0), 'rightUpperLeg', 'Body'), ('LowerLegR', 22, (-0.08, 0.32, 0), 'rightLowerLeg', 'Body'),
    ('FootR', 23, (-0.08, 0.05, 0), 'rightFoot', 'Body'), ('ToesR', 24, (-0.08, 0.0, 0.08), 'rightToes', 'Body'),
    ('Hair_tail_L', 5, (0.06, 1.05, -0.06), None, 'Hair'), ('Hair_tail_L.001', 26, (0.07, 0.90, -0.07), None, 'Hair'),
    ('Skirt_root', 1, (0, 0.55, 0), None, None), ('Skirt_F', 28, (0, 0.50, 0.08), None, 'Cloth'),
    ('Skirt_B', 28, (0, 0.50, -0.08), None, 'Cloth'), ('Skirt_F.001', 29, (0, 0.42, 0.09), None, 'Cloth'))
WD_VRM_COLORS = {'Face': (230, 200, 190, 255), 'Body': (240, 210, 200, 255), 'Cloth': (40, 60, 120, 255),
                 'Hair': (250, 240, 200, 255), 'Lashes': (20, 10, 10, 200)}
WD_VRM_PROFILE = {
    'materials': {'Face': {'slot': 'head'}, 'Lashes': {'slot': 'lashes'}, 'Cloth': {'slot': 'coat', 'spec': 'cloth'},
                  'Body': {'slot': 'coat', 'spec': 'skin'}, 'Hair': {'slot': 'hair'}},
    'chains': [{'match': 'Hair_tail_', 'under': 'head', 'to': 'Spine2', 'shares': [0.0, 0.5]},
               {'match': 'Skirt_', 'under': 'hips', 'to_side': ['L Thigh', 'R Thigh'], 'shares': [0.3]}]}


def wd_human_template(path):
    nodes = []
    for name, parent, p in WD_HUMAN_WORLD:
        base = WD_HUMAN_WORLD[parent][2] if parent >= 0 else (0, 0, 0)
        nodes.append((name, parent, tuple(a - b for a, b in zip(p, base))))
    return wd_template(path, palette_len=4, nodes_spec=tuple(nodes), materials=WD_HUMAN_MATERIALS,
                       slots=((0, 0x17BA, 6), (1, 0x179A, (1, 2)), (2, 0x179A, 6), (3, 0x11BA, 6)))


def wd_vrm(path, vrm0=False):
    """Synthetic humanoid VRM: one skinned triangle per bone, each fully weighted to its bone.

    vrm0=True writes the VRM 0.x form: VRM extension, humanBones list, VRM 0.x thumb names, facing -Z."""
    import io
    from PIL import Image
    binary, views, accessors = bytearray(), [], []

    def view(data):
        while len(binary) % 4:
            binary.append(0)
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)})
        binary.extend(data)
        return len(views) - 1

    def acc(rows, fmt, component, kind):
        accessors.append({'bufferView': view(b''.join(struct.pack('<' + fmt, *r) for r in rows)),
                          'componentType': component, 'count': len(rows), 'type': kind})
        return len(accessors) - 1

    flip = (-1, 1, -1) if vrm0 else (1, 1, 1)
    world = [tuple(c * f for c, f in zip(p, flip)) for _, _, p, _, _ in WD_VRM_NODES]
    gl_nodes = [{'name': name} for name, *_ in WD_VRM_NODES]
    for i, (name, parent, _, _, _) in enumerate(WD_VRM_NODES):
        base = world[parent] if parent >= 0 else (0, 0, 0)
        gl_nodes[i]['translation'] = [a - b for a, b in zip(world[i], base)]
        if parent >= 0:
            gl_nodes[parent].setdefault('children', []).append(i)
    joints = list(range(1, len(WD_VRM_NODES)))
    ibm = acc([(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -world[j][0], -world[j][1], -world[j][2], 1) for j in joints],
              '16f', 5126, 'MAT4')
    names = list(WD_VRM_COLORS)
    images, materials = [], []
    for k, name in enumerate(names):
        img = Image.new('RGBA', (8, 8), WD_VRM_COLORS[name])
        img.putpixel((k, k), (255, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        images.append({'name': name, 'mimeType': 'image/png', 'bufferView': view(buf.getvalue())})
        materials.append({'name': name, 'pbrMetallicRoughness': {'baseColorTexture': {'index': k}}})
    primitives = []
    for mat_index, name in enumerate(names):
        pos, nrm, uv, jt, wt = [], [], [], [], []
        for i, (_, _, _, _, mat) in enumerate(WD_VRM_NODES):
            if mat != name:
                continue
            x, y, z = world[i]
            pos += [(x, y, z), (x + 0.01 * flip[0], y, z), (x, y - 0.01, z + 0.005 * flip[2])]  # mirrored for vrm0
            nrm += [(0, 0, 1)] * 3
            uv += [(0.3, 0.3), (0.5, 0.3), (0.3, 0.5)] if name == 'Lashes' else [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9)]
            jt += [(joints.index(i), 0, 0, 0)] * 3
            wt += [(1.0, 0, 0, 0)] * 3
        attrs = {'POSITION': acc(pos, '3f', 5126, 'VEC3'), 'NORMAL': acc(nrm, '3f', 5126, 'VEC3'),
                 'TEXCOORD_0': acc(uv, '2f', 5126, 'VEC2'), 'JOINTS_0': acc(jt, '4H', 5123, 'VEC4'),
                 'WEIGHTS_0': acc(wt, '4f', 5126, 'VEC4')}
        primitives.append({'attributes': attrs, 'indices': acc([(i,) for i in range(len(pos))], 'H', 5123, 'SCALAR'),
                           'material': mat_index})
    gl_nodes.append({'name': 'Body', 'mesh': 0, 'skin': 0})
    human = {h: i for i, (_, _, _, h, _) in enumerate(WD_VRM_NODES) if h}
    if vrm0:
        rename = {'leftThumbMetacarpal': 'leftThumbProximal', 'leftThumbProximal': 'leftThumbIntermediate'}
        ext = {'VRM': {'humanoid': {'humanBones': [{'bone': rename.get(h, h), 'node': i} for h, i in human.items()]}}}
    else:
        ext = {'VRMC_vrm': {'specVersion': '1.0', 'humanoid': {'humanBones': {h: {'node': i} for h, i in human.items()}}}}
    while len(binary) % 4:
        binary.append(0)
    document = {'asset': {'version': '2.0'}, 'extensionsUsed': list(ext), 'extensions': ext,
                'buffers': [{'byteLength': len(binary)}], 'bufferViews': views, 'accessors': accessors,
                'images': images, 'textures': [{'source': k} for k in range(len(images))], 'materials': materials,
                'nodes': gl_nodes, 'skins': [{'joints': joints, 'inverseBindMatrices': ibm}],
                'meshes': [{'name': 'Body', 'primitives': primitives}], 'scenes': [{'nodes': [0, len(gl_nodes) - 1]}], 'scene': 0}
    encoded = json.dumps(document).encode()
    encoded += b' ' * (-len(encoded) % 4)
    body = struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + struct.pack('<II', len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, len(body) + 12) + body)


def wd_donor(width, height, fourcc=b'DXT1'):
    """Donor XBT: DDS with a full mip chain of zero blocks and the FOURCC flag set."""
    mips, payload, w, h = 0, 0, width, height
    while True:
        mips += 1
        payload += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if fourcc == b'DXT1' else 16)
        if w == 1 and h == 1:
            break
        w, h = max(1, w // 2), max(1, h // 2)
    data = bytearray(xbt(dds(width, height, mips=mips, payload=bytes(payload))))
    struct.pack_into('<I', data, 48 + 80, 4)
    data[48 + 84:48 + 88] = fourcc
    return bytes(data)


def wd_base_pack(folder, template_path):
    """Base char01 replacer pack: template XBG, donor XBTs for every char01 stream, one private entry, modconfig."""
    paths, repack = module('watch-dogs', 'char01_paths'), module('watch-dogs', 'repack_fat8')
    blobs = {repack.path_hash(paths.XBG): template_path.read_bytes(),
             repack.path_hash('graphics/_synthetic/private_hair.material.bin'): b'PRIVATE-MATERIAL'}
    for key in paths.TEXTURES:
        for p in paths.texture_paths(key):
            blobs[repack.path_hash(p)] = wd_donor(8, 4, b'DXT5') if key == paths.LASHES_KEY else wd_donor(8, 8)
    fat = wd_fat(folder, blobs)
    (folder / 'modconfig.json').write_text(json.dumps({'friendlyId': 'base_mod', 'name': 'Base', 'author': 'synthetic',
                                                       'packs': ['pack'], 'version': '1.0.0', 'configVersion': 1,
                                                       'modsRecommendedBelowPriority': ['living_city']}))
    return fat, blobs


class WatchDogsVrmBuilder(unittest.TestCase):
    """Generic VRM -> char01 builder on a synthetic humanoid; the real check is the Karin_Original
    reproduction recorded in VALIDATION.md."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding wd vrm ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_wd_vrm_build_end_to_end(self):
        import numpy as np
        wd('build_from_vrm', pil=True)
        xm, codec, skel, paths, repack = (wd(n) for n in ('xbg_model', 'xbg_codec', 'xbg_skeleton', 'char01_paths', 'repack_fat8'))
        template = self.root / 'template.xbg'
        wd_human_template(template)
        base = self.root / 'base'
        base.mkdir()
        fat, blobs = wd_base_pack(base, template)
        vrm, profile, out = self.root / 'model.vrm', self.root / 'profile.json', self.root / 'out'
        wd_vrm(vrm)
        profile.write_text(json.dumps(WD_VRM_PROFILE))
        args = ('--vrm', vrm, '--profile', profile, '--base-fat', fat, '--out-dir', out, '--package', '--pack', 'synthetic',
                '--friendly-id', 'synthetic_replacer', '--name', 'Synthetic', '--version', '0.1.0')
        self.assertIn('READBACK PASS', cli('watch-dogs', 'build_from_vrm', *args).stdout)
        cli('watch-dogs', 'build_from_vrm', *args, ok=False)  # non-empty output directory
        report = json.loads((out / 'build_report.json').read_text())
        self.assertEqual(report['facing'], '+Z (VRM 1.0)')
        scale = report['scale']
        self.assertAlmostEqual(scale, 0.87 / 0.53, places=6)  # template thigh-to-foot over the model's
        # joints: torso pivots stay, limbs move to the model's scaled joints
        before, after = skel.Skeleton(template), skel.Skeleton(out / 'char01.xbg')
        self.assertTrue(np.allclose(after.head('Pelvis'), before.head('Pelvis'), atol=1e-6))
        self.assertTrue(np.allclose(after.head('L Thigh'), scale * np.array([-0.08, 0, 0.58]), atol=1e-5))
        self.assertTrue(np.allclose(after.head('L UpperArm')[0], -scale * 0.10, atol=1e-5))
        # repose: the forearm points the template's way, and its vertices lie along the new forearm
        f, h = after.head('L Forearm'), after.head('L Hand')
        tmpl = before.head('L Hand') - before.head('L Forearm')
        self.assertGreater((h - f) @ tmpl / np.linalg.norm(h - f) / np.linalg.norm(tmpl), 0.9999)
        x = xm.load(out / 'char01.xbg')
        _, lods = codec.decode(x)
        b = {n['name']: n['b'] for n in x.nodes}

        def vertices_on(sub, bone):
            return [dict(zip(r_b[r_w > 0].tolist(), r_w[r_w > 0].tolist())) for r_b, r_w in zip(sub.bones, sub.weights)
                    if bone in r_b[r_w > 0]]

        coat = next(s for s in lods[0] if s.material == 1)
        fore = coat.positions[coat.bones[:, 0] == b['L Forearm']] - f
        along = fore[np.argmin(np.abs(np.linalg.norm(fore, axis=1) - 0.01 * scale))]  # the vertex 1 cm down the T-pose arm
        self.assertGreater(along @ (h - f) / np.linalg.norm(along) / np.linalg.norm(h - f), 0.99)
        # weights: eye -> Head, hair chain level 1 -> half to Spine2, skirt level 0 -> 30 % split over both thighs
        lashes = next(s for s in lods[0] if s.material == 3)
        self.assertTrue(all(v == {b['Head']: 255} for v in vertices_on(lashes, b['Head'])))
        hair = next(s for s in lods[0] if s.material == 2)
        self.assertIn({b['Head']: 128, b['Spine2']: 127}, vertices_on(hair, b['Spine2']))
        self.assertIn({b['Head']: 255}, vertices_on(hair, b['Head']))
        # skirt vertices on the centre line (x = 0): 0.7 Pelvis, 0.15 per thigh
        self.assertIn({b['Pelvis']: 179, b['L Thigh']: 38, b['R Thigh']: 38}, vertices_on(coat, b['Pelvis']))
        # textures: two coat textures stacked, lashes cropped; package keeps untouched entries
        layout = json.loads((out / 'textures' / 'layout.json').read_text())
        self.assertEqual(layout['materials']['Cloth']['rect'], [0.0, 0.0, 1.0, 0.5])
        self.assertEqual(layout['materials']['Body']['rect'], [0.0, 0.5, 1.0, 1.0])
        self.assertGreater(layout['materials']['Lashes']['rect'][2], 1.0)
        new_fat = out / 'package' / 'synthetic.fat'
        new_dat = new_fat.with_suffix('.dat').read_bytes()
        entries = {h_: new_dat[o:o + s] for h_, o, s in module('watch-dogs', 'extract_fat8').read_entries(new_fat.read_bytes())}
        self.assertEqual(entries.keys(), blobs.keys())
        changed = {h_ for h_ in entries if entries[h_] != blobs[h_]}
        expect = {repack.path_hash(paths.XBG)} | {repack.path_hash(p) for k, (slot, kind) in paths.TEXTURES.items()
                                                  if slot != 'head' or kind == 'd' for p in paths.texture_paths(k)}
        self.assertEqual(changed, expect)  # head normal/specular and the private material stay
        cfg = json.loads((out / 'package' / 'modconfig.json').read_text())
        self.assertEqual((cfg['friendlyId'], cfg['packs'], cfg['author']), ('synthetic_replacer', ['synthetic'], 'synthetic'))
        self.assertTrue((out / 'synthetic_replacer_v0_1_0.zip').is_file())

    def test_wd_vrm0_facing_and_thumb_names(self):
        import numpy as np
        wd('vrm_fit', pil=True)
        fit_mod, model, skel = wd('vrm_fit'), wd('vrm_model'), wd('xbg_skeleton')
        template = self.root / 'template.xbg'
        wd_human_template(template)
        sk = skel.Skeleton(template)
        v1, v0 = self.root / 'v1.vrm', self.root / 'v0.vrm'
        wd_vrm(v1)
        wd_vrm(v0, vrm0=True)
        m0 = model.load(v0)
        self.assertEqual(m0.humanoid['leftThumbMetacarpal'], 12)  # VRM 0.x leftThumbProximal
        self.assertEqual(m0.humanoid['leftThumbProximal'], 13)  # VRM 0.x leftThumbIntermediate
        a, b = fit_mod.build_fit(v1, sk), fit_mod.build_fit(v0, sk)
        self.assertFalse(np.array_equal(a.axes, b.axes))
        for name in sk.names:
            self.assertTrue(np.allclose(a.aiden_world[name], b.aiden_world[name], atol=1e-9), name)
        for pa, pb in zip(a.parts, b.parts):
            self.assertTrue(np.allclose(pa.positions, pb.positions, atol=1e-9))

    def test_wd_vrm_profile_errors_and_grid(self):
        wd('vrm_textures', pil=True)
        tex, model = wd('vrm_textures'), wd('vrm_model')
        self.assertEqual(tex.cells(2, 16), [(0, 0, 16, 8), (0, 8, 16, 8)])
        self.assertEqual(tex.cells(3, 16), [(0, 0, 8, 8), (8, 0, 8, 8), (0, 8, 8, 8)])
        vrm = self.root / 'model.vrm'
        wd_vrm(vrm)
        m = model.load(vrm)
        partial = {'materials': {k: v for k, v in WD_VRM_PROFILE['materials'].items() if k != 'Hair'}}
        with self.assertRaises(ValueError):
            tex.compose(m, partial, self.root / 'a')
        grid = {'materials': {**WD_VRM_PROFILE['materials'], 'Hair': {'slot': 'coat'}}}
        layout = tex.compose(m, grid, self.root / 'b', {'coat': (8, 8)})
        self.assertEqual(layout['materials']['Hair']['rect'], [0.0, 0.5, 0.5, 1.0])  # third cell of a 2x2 grid
        self.assertNotIn('char01_hair_v2_d', layout['textures'])


# ---------------------------------------------------------------- Watch Dogs physics (xbg_physics, vrm_physics)
WD_COAT_ANCHORS = ('L Thigh', 'R Thigh', 'Pelvis', 'Spine', 'Spine1', 'Spine2')


def wd_jiggle(smu, node, anchor='Spine2'):
    return smu.Obj(offset=0, params=(0.0, -9.8, 0.9, 0.9, 0.7, 0.1, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0), type=4, sub=2, flag=0,
                   nodes=[(node, 0.01, 0, 0.0, 0.0)], anchors=[anchor])


def wd_physics_block(pos, particles=(), collar=(), coat=True):
    """Synthetic physics block at file offset pos: FCB part, a jiggle, [a coat cloth (header 2,0,1, two thigh capsules,
    particle records), a collar chain], and a table (one kind-2 entry inside the kept objects, one pointing at the
    collar, one kind-6 entry)."""
    import numpy as np
    smu = wd('smu_format')
    out = bytearray(struct.pack('<II', 1, 8) + b'nbCF' + b'\0' * 4)
    out += struct.pack('<I', 3 if coat else 1)
    out += smu.write_object(wd_jiggle(smu, 'Ph_Jig_Synthetic_SMUJiggle'), pos + len(out))
    if not coat:
        return bytes(out + struct.pack('<I', 0))
    cloth = bytearray(struct.pack('<I12f3I', 0, 0.0, -12.5, 1.75, 1.5, 1.0, 1.0, 0.15, 0.015, 0.1, 0.01, 0.0, 0.0, 2, 0, 1))
    cloth += struct.pack('<III', 0, 0, 2)  # lists A, B empty; C: two thigh capsules pointing down the legs
    for bone in ('L Thigh', 'R Thigh'):
        cloth += smu._name_bytes(bone)
        cloth += b'\0' * (-(pos + len(out) + len(cloth)) % 16)
        cloth += np.diag([1.0, -1.0, -1.0, 1.0]).astype('<f4').tobytes() + struct.pack('<7f', 0.06, 0, 0, 0.06, 0, 0, 0.4)
    cloth += struct.pack('<II', 0, len(particles))  # list D empty, particle records
    for name, flags in particles:
        cloth += smu._name_bytes(name) + struct.pack('<fIff', 0.0255, flags, 0.5, 0.5)
    cloth += struct.pack('<I', len(WD_COAT_ANCHORS)) + b''.join(smu._name_bytes(a) for a in WD_COAT_ANCHORS)
    out += cloth
    chain = smu.Obj(offset=0, params=(0.0, -9.8, 1.0, 1.0, 1.0, 0.1, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0), type=4, sub=1, flag=0,
                    nodes=[(n, 0.01, 1 if i == 0 else 0x10000, 0.0, 0.0) for i, n in enumerate(collar)],
                    anchors=['Spine2'], links=[(i, i + 1, 1) for i in range(len(collar) - 1)])
    out += smu.write_object(chain, pos + len(out))
    cut = 1 + len(particles)
    out += struct.pack('<I', 3) + struct.pack('<HHHHf', 2, 2, 1, 0, 0.5) + struct.pack('<HHHHf', cut, 2, 1, 0, 1.0)
    out += struct.pack('<HH', 0, 6) + b'\0' * 20
    return bytes(out)


WD_PHYS_COLLAR = tuple(f'Ph_Pl_Sweater_Colar_SMUNode_{i}' for i in range(1, 5))


def wd_physics_template(path):
    """The synthetic human template plus physics nodes: a jiggle node, a ring of 12 coat particles on the Pelvis
    (two pinned), two particles on a thigh helper, one pinned on the Spine, and four spare collar nodes."""
    import numpy as np
    world = list(WD_HUMAN_WORLD)
    idx = {n: i for i, (n, _, _) in enumerate(world)}
    world.append(('Ph_Jig_Synthetic_SMUJiggle', idx['Spine2'], (0, -0.1, 1.3)))
    particles = []
    for k in range(12):
        a = np.radians(30 * k + 15)
        z = 0.85 if k < 6 else 0.78
        world.append((f'PL_Coat_SMUNode_{k + 1}', idx['Pelvis'], (0.12 * np.sin(a), -0.12 * np.cos(a), z)))
        particles.append((f'PL_Coat_SMUNode_{k + 1}', (2 << 16) | (1 if k in (0, 6) else 0)))
    world.append(('Rfx_LThigh_Back', idx['L Thigh'], (-0.1, -0.05, 0.85)))
    helper = len(world) - 1
    for k, p in ((13, (-0.14, -0.1, 0.8)), (14, (-0.16, 0.0, 0.72))):
        world.append((f'PL_Coat_SMUNode_{k}', helper, p))
        particles.append((f'PL_Coat_SMUNode_{k}', 0))
    world.append(('PL_Coat_SMUNode_15', idx['Spine'], (0, -0.13, 1.05)))
    particles.append(('PL_Coat_SMUNode_15', (3 << 16) | 1))
    for i, n in enumerate(WD_PHYS_COLLAR):
        world.append((n, idx['Spine2'], (0.02 * i, -0.08, 1.42)))
    nodes = []
    for name, parent, p in world:
        base = world[parent][2] if parent >= 0 else (0, 0, 0)
        nodes.append((name, parent, tuple(float(a - b) for a, b in zip(p, base))))
    return wd_template(path, palette_len=4, nodes_spec=tuple(nodes), materials=WD_HUMAN_MATERIALS,
                       slots=((0, 0x17BA, 6), (1, 0x179A, (1, 2)), (2, 0x179A, 6), (3, 0x11BA, 6)),
                       physics=lambda pos: wd_physics_block(pos, particles, WD_PHYS_COLLAR))


class WatchDogsPhysics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding wd physics ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_wd_smu_object_round_trip(self):
        import numpy as np
        smu = wd('smu_format')
        m = tuple(np.eye(4).reshape(-1))
        o = smu.Obj(offset=0, params=tuple(float(i) for i in range(12)), type=4, sub=1, flag=1,
                    spheres=[('_Jaw', m, 0.04)], capsules=[('Head', m, (0.08, 0, 0, 0.08, 0, 0, 0.15))],
                    nodes=[('Ph_A', 0.01, 1, 0.0, 0.0), ('Ph_B', 0.02, 0x10000, 0.0, 0.0)], anchors=['Facial_Hook', 'Head'],
                    links=[(0, 1, 1)])
        for pos in (0, 4, 12):
            raw = b'\xAA' * pos + smu.write_object(o, pos)
            r = smu.Reader(raw, pos)
            back = smu.parse_object(r)
            self.assertEqual(r.p, len(raw))
            self.assertEqual((back.params, back.type, back.sub, back.flag), (o.params, 4, 1, 1))
            self.assertEqual([n for n, *_ in back.nodes], ['Ph_A', 'Ph_B'])
            self.assertEqual([f for _, _, f, _, _ in back.nodes], [1, 0x10000])
            self.assertEqual((back.anchors, back.links), (['Facial_Hook', 'Head'], [(0, 1, 1)]))
            self.assertEqual(back.spheres[0][0], '_Jaw')
            self.assertAlmostEqual(back.capsules[0][2][6], 0.15, places=6)
            m_at = raw.index(struct.pack('<16f', *m))
            self.assertEqual(m_at % 16, 0)  # matrices are aligned to the file offset
        bad = bytearray(smu.write_object(o, 0))
        name_at = bytes(bad).index(b'_Jaw') - 8  # a wrong name hash is rejected
        bad[name_at:name_at + 4] = b'\0\0\0\0'
        with self.assertRaises(ValueError):
            smu.parse_object(smu.Reader(bytes(bad), 0))

    def test_wd_physics_chain_rig_move_and_colliders(self):
        import numpy as np
        phys, smu, skel, xm, codec = (wd(n) for n in ('xbg_physics', 'smu_format', 'xbg_skeleton', 'xbg_model', 'xbg_codec'))
        nodes = WD_NODES + tuple((n, 4, (0.02 * i, -0.08, 0.12)) for i, n in enumerate(WD_PHYS_COLLAR[:3]))
        path = self.root / 'template.xbg'
        wd_template(path, palette_len=2, nodes_spec=nodes, physics=lambda pos: wd_physics_block(pos, coat=False))
        before = skel.Skeleton(path)
        x = xm.load(path)
        b0, b1 = phys.block_range(x)
        starts = phys.object_starts(x.data, b0, b1)
        self.assertEqual(len(starts), 1)
        keep_end = smu.parse_object(smu.Reader(x.data, starts[0])).end
        head = before.head('Head')
        points = [head + (0, -0.1, 0), head + (0, -0.15, -0.1), head + (0, -0.18, -0.2)]
        o = smu.Obj(offset=0, params=(0.0, -4.0, 0.15, 0.15, 0.15, 0.1, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0), type=4, sub=1,
                    flag=1, anchors=['Head'])
        chain = {'nodes': list(WD_PHYS_COLLAR[:3]), 'parent': 'Head', 'points': points, 'object': o,
                 'radius': [0.01, 0.02, 0.01], 'link_kinds': [1, 1]}
        rigged, report = phys.edit(path.read_bytes(), [chain], keep_objects=(1, keep_end), phys_table=struct.pack('<I', 0),
                                   fix_anchor=True)
        self.assertEqual((report['edited_nodes'], report['objects']), (3, 2))
        out = self.root / 'rigged.xbg'
        out.write_bytes(rigged)
        after, y = skel.Skeleton(out), xm.load(out)
        for n, p in zip(chain['nodes'], points):
            i = after.index[n]
            self.assertTrue(np.allclose(after.head(n), p, atol=1e-5))
            self.assertEqual(after.names[after.parent[i]], 'Head')
            self.assertTrue(np.allclose(after.bind[i] @ after.inv_bind[after.b[i]], np.eye(4), atol=1e-4))
            k = chain['nodes'].index(n)
            d = points[k + 1] - points[k] if k < 2 else points[k] - points[k - 1]  # local +Y runs down the chain
            self.assertGreater(after.bind[i][:3, 1] @ d / np.linalg.norm(d), 0.999)
        c0, c1 = phys.block_range(y)
        self.assertEqual(y.data[c0 + 20:c0 + 20 + keep_end - (b0 + 20)], x.data[b0 + 20:keep_end])  # jiggle kept verbatim
        r = smu.Reader(y.data, c0 + 20 + keep_end - (b0 + 20))
        rigged_chain = smu.parse_object(r)
        self.assertEqual([f for _, _, f, _, _ in rigged_chain.nodes], [1, 0, 0])  # one anchor -> free nodes use index 0
        self.assertEqual(struct.unpack_from('<I', y.data, r.p)[0], 0)
        self.assertEqual(r.p + 4, c1)
        _, lods_before = codec.decode(x)
        _, lods_after = codec.decode(y)
        self.assertTrue(np.array_equal(lods_before[0][0].positions, lods_after[0][0].positions))
        # move: push a node out, hang another from the Pelvis; world binds and inverse binds stay consistent
        moved, rep = phys.move(path.read_bytes(), {'L_Eye': before.head('L_Eye') + (0, 0.05, 0)},
                               {WD_PHYS_COLLAR[2]: 'Pelvis'})
        self.assertEqual((rep['moved_nodes'], rep['reparented_nodes']), (1, 1))
        out2 = self.root / 'moved.xbg'
        out2.write_bytes(moved)
        m2 = skel.Skeleton(out2)
        i = m2.index[WD_PHYS_COLLAR[2]]
        self.assertEqual(m2.names[m2.parent[i]], 'Pelvis')
        self.assertTrue(np.allclose(m2.bind[i], before.bind[i], atol=1e-5))
        self.assertTrue(np.allclose(m2.head('L_Eye'), before.head('L_Eye') + (0, 0.05, 0), atol=1e-5))
        for k in range(len(m2.names)):
            self.assertTrue(np.allclose(m2.bind[k] @ m2.inv_bind[m2.b[k]], np.eye(4), atol=1e-4))
        # export-colliders reads the objects of an XBG (here the rigged one) into JSON
        cols = self.root / 'colliders.json'
        cli('watch-dogs', 'xbg_physics', 'export-colliders', '--xbg', out, '--out', cols)
        data = json.loads(cols.read_text())
        self.assertEqual(sorted(data['objects']), ['Ph_Jig_Synthetic_SMUJiggle', WD_PHYS_COLLAR[0]])
        cli('watch-dogs', 'xbg_physics', 'export-colliders', '--xbg', out, '--out', cols, ok=False)  # no overwrite

    def test_wd_vrm_physics_end_to_end(self):
        import numpy as np
        wd('build_from_vrm', pil=True)
        phys, smu, skel, xm, codec = (wd(n) for n in ('xbg_physics', 'smu_format', 'xbg_skeleton', 'xbg_model', 'xbg_codec'))
        template = self.root / 'template.xbg'
        wd_physics_template(template)
        base = self.root / 'base'
        base.mkdir()
        fat, _ = wd_base_pack(base, template)
        vrm = self.root / 'model.vrm'
        wd_vrm(vrm)
        cloth_part = 'Body/' + str(list(WD_VRM_COLORS).index('Cloth'))
        physics = {'colliders': {'hair': [{'from': 'Ph_Synthetic_SMUNode_1', 'fallback': 'body'}, {'legs': True}]},
                   'chains': [{'start': 'Hair_tail_L', 'attach': 'Head', 'colliders': 'hair', 'gravity': -4.0,
                               'damping': 0.15, 'pull': 0.1, 'radius': [0.01, 0.02, 0.01], 'pool': 'collar'}],
                   'cloth': {'joints': 'Skirt_', 'skip': ['Skirt_root'], 'gravity': -2.0, 'damping_scale': 0.12, 'k': 4,
                             'sigma': 0.08, 'thigh_radius': 0.07, 'hang_from_pelvis': True},
                   'double_sided': [cloth_part]}
        profile = self.root / 'profile.json'
        profile.write_text(json.dumps({**WD_VRM_PROFILE, 'chains': [], 'physics': physics}))
        cols = self.root / 'colliders.json'
        m = tuple(np.eye(4).reshape(-1).tolist())
        cols.write_text(json.dumps({'schema': 'watchdogs.physics_colliders.v1', 'objects': {
            'Ph_Synthetic_SMUNode_1': {'spheres': [], 'capsules': [['Spine2', m, [0.09, 0, 0, 0.09, 0, 0, 0.2]]]}}}))
        runs = {}
        for tag, extra in (('file', ('--colliders', cols)), ('derived', ())):
            out = self.root / tag
            result = cli('watch-dogs', 'build_from_vrm', '--vrm', vrm, '--profile', profile, '--base-fat', fat,
                         '--out-dir', out, *extra)
            self.assertIn('READBACK PASS', result.stdout)
            runs[tag] = out
        out = runs['file']
        report = json.loads((out / 'build_report.json').read_text())['physics']
        self.assertEqual((report['objects_kept'], report['objects_dropped']), (2, 1))
        self.assertEqual((report['table_entries'], report['table_dropped'], report['global_cut']), (3, 1, 16))
        self.assertEqual(report['anchors_switched'], 3)  # two thigh-hung particles, one spine-pinned one
        self.assertEqual(report['double_sided'], [cloth_part])
        x, sk = xm.load(out / 'char01.xbg'), skel.Skeleton(out / 'char01.xbg')
        b0, b1 = phys.block_range(x)
        coat = phys.coat_object_offset(x.data, b0, b1)
        prm = struct.unpack_from('<12f', x.data, coat + 4)
        self.assertAlmostEqual(prm[1], -2.0, places=6)
        self.assertAlmostEqual(prm[2], 1.75 * 0.12, places=6)
        caps = phys.coat_capsules(x.data, coat)
        self.assertAlmostEqual(struct.unpack_from('<f', x.data, caps['L Thigh'])[0], 0.07, places=6)
        names = [n for n in sk.names if n.startswith('PL_Coat_SMUNode_')]
        flags = {n: struct.unpack_from('<I', x.data, o)[0] for n, o in phys.coat_particle_flags(x.data, coat, names).items()}
        for n in ('PL_Coat_SMUNode_13', 'PL_Coat_SMUNode_14', 'PL_Coat_SMUNode_15'):
            self.assertEqual(sk.names[sk.parent[sk.index[n]]], 'Pelvis')
            self.assertEqual(flags[n] >> 16, 2)
        self.assertEqual(flags['PL_Coat_SMUNode_15'] & 1, 1)  # still pinned, now to the Pelvis
        # block: jiggle and coat kept, the collar chain replaced by the hair chain, the collar table entry dropped
        fcb = struct.unpack_from('<I', x.data, b0 + 4)[0]
        self.assertEqual(struct.unpack_from('<I', x.data, b0 + 8 + fcb)[0], 3)
        starts = phys.object_starts(x.data, b0, b1)
        hair = smu.parse_object(smu.Reader(x.data, starts[-1]))
        self.assertEqual(hair.anchors, ['Facial_Hook', 'Head'])
        self.assertEqual([f for _, _, f, _, _ in hair.nodes], [1, 0x10000])
        # colliders: the file's Spine2 capsule, then the template's thigh capsules as they were (0.06, not 0.07)
        self.assertEqual([c[0] for c in hair.capsules], ['Spine2', 'L Thigh', 'R Thigh'])
        self.assertAlmostEqual(hair.capsules[0][2][0], 0.09, places=6)
        self.assertAlmostEqual(hair.capsules[1][2][0], 0.06, places=6)
        for n, *_ in hair.nodes:
            self.assertIn(n, WD_PHYS_COLLAR)
            self.assertEqual(sk.names[sk.parent[sk.index[n]]], 'Head')
        xd = xm.load(runs['derived'] / 'char01.xbg')
        d0, d1 = phys.block_range(xd)
        derived = smu.parse_object(smu.Reader(xd.data, phys.object_starts(xd.data, d0, d1)[-1]))
        # without --colliders the "from" item falls back to capsules built from the skeleton (chest, neck, head)
        self.assertEqual([c[0] for c in derived.capsules], ['Spine2', 'Neck', 'Head', 'L Thigh', 'R Thigh'])
        self.assertAlmostEqual(derived.capsules[0][2][0], 0.12, places=6)
        # weights: skirt level-1 vertices on coat particles, the hair tail on the chain nodes; the skirt has back faces
        _, lods = codec.decode(x)
        b_of = {n['name']: n['b'] for n in x.nodes}
        used = {int(bb) for sub in lods[0] for row_b, row_w in zip(sub.bones, sub.weights) for bb in row_b[row_w > 0]}
        self.assertTrue(used & {b_of[n] for n in names})
        self.assertTrue(used & {b_of[n] for n, *_ in hair.nodes})
        parts = json.loads((out / 'build_report.json').read_text())['parts']
        self.assertIn(cloth_part + '/back', [p['part'] for p in parts])

RONIN_KIT = KITS / 'rise-of-the-ronin'
RONIN_NUMPY_SCRIPTS = ('leg_weights',)
RONIN_DEPENDENCIES = ('numpy', 'scipy')


def ronin_missing():
    return [m for m in RONIN_DEPENDENCIES if importlib.util.find_spec(m) is None]


def ronin(name, numpy=False):
    """Rise of the Ronin module; the leg tool is skipped with the install hint when numpy / scipy are absent."""
    if not RONIN_KIT.is_dir():
        raise unittest.SkipTest('rise-of-the-ronin is not included in this single-game export')
    if numpy and ronin_missing():
        raise unittest.SkipTest('pip install -r portable-kits/rise-of-the-ronin/requirements.txt (missing '
                                + ', '.join(ronin_missing()) + ')')
    return module('rise-of-the-ronin', name)


def ronin_chunk(magic, body, version=b'0000'):
    return magic + version + struct.pack('<I', 12 + len(body)) + body


def ronin_g1m(joints, binds, materials, vertices, palettes, submeshes, indices, mm_extra=0):
    """Minimal little-endian G1M: FM1G (MM1G count at +24), SM1G, MM1G, GM1G with the nine gust sections.
    joints: (bone id, parent storage index, local position); storage order = list order, bone ids may be sparse.
    vertices: list of (position, weights[8], palette slots[8]); one vertex buffer of stride 36."""
    ids = [0xFFFF] * (max(b for b, _, _ in joints) + 1)
    for j, (b, _, _) in enumerate(joints):
        ids[b] = j
    head = struct.pack('<2I4H', 0, 0, len(joints), len(ids), 1, 0) + struct.pack(f'<{len(ids)}H', *ids)
    head += b'\0' * (-(12 + len(head)) % 16)
    joint_offset = 12 + len(head)
    sm = head[:0] + struct.pack('<I', joint_offset) + head[4:]
    for _b, parent, pos in joints:
        sm += struct.pack('<3fi4f4f', 1, 1, 1, parent, 0, 0, 0, 1, *pos, 1)
    mm = struct.pack('<I', len(binds)) + b''.join(struct.pack('<16f', *[v for r in m for v in r]) for m in binds)
    fm = struct.pack('<4I', 0, 0, 0, len(binds) + mm_extra)
    secs = []
    mat = b''.join(struct.pack('<4I', 0, len(s), 0, 0) + b''.join(struct.pack('<6H', i, 0, t, 0, 1, 1) for i, t in s)
                   for s in materials)
    secs.append((0x00010002, len(materials), mat))
    vb = struct.pack('<4I', 0, 36, len(vertices), 0) + b''.join(
        struct.pack('<3f4e4e8B', *p, *w[:4], *w[4:], *s) for p, w, s in vertices)
    secs.append((0x00010004, 1, vb))
    attrs = [(0, 0x02, 0, 0), (12, 0x0B, 1, 0), (20, 0x0B, 1, 1), (28, 0x05, 2, 0), (32, 0x05, 2, 1)]
    secs.append((0x00010005, 1, struct.pack('<2I', 1, 0) + struct.pack('<I', len(attrs)) +
                 b''.join(struct.pack('<2H4B', 0, off, typ, 0, sem, layer) for off, typ, sem, layer in attrs)))
    secs.append((0x00010006, len(palettes), b''.join(
        struct.pack('<I', len(p)) + b''.join(struct.pack('<3I', g, 0, b) for g, b in p) for p in palettes)))
    ib = struct.pack('<3I', len(indices), 16, 0) + struct.pack(f'<{len(indices)}H', *indices)
    ib += b'\0' * (-len(ib) % 4)
    secs.append((0x00010007, 1, ib))
    secs.append((0x00010008, len(submeshes), b''.join(
        struct.pack('<14I', 0, 0, pal, 0, 0, 0, mat_i, 0, 0, 3, voff, vcnt, ioff, icnt)
        for pal, mat_i, voff, vcnt, ioff, icnt in submeshes)))
    body = b'DX1\0' + struct.pack('<I6f', 0, *([0.0] * 6)) + struct.pack('<I', len(secs))
    for magic, count, payload in secs:
        body += struct.pack('<3I', magic, 12 + len(payload), count) + payload
    chunks = [ronin_chunk(b'FM1G', fm), ronin_chunk(b'SM1G', sm), ronin_chunk(b'MM1G', mm),
              ronin_chunk(b'GM1G', body, b'0440')]
    data = b''.join(chunks)
    return b'_M1G0037' + struct.pack('<4I', 24 + len(data), 24, 0, len(chunks)) + data


def ronin_g1t(fmt, log_w, log_h, mips, payload, storage=0):
    # 8-byte texture header, then a 12-byte extra header: size, 4 unknown bytes, u16 layers, storage flag, pad
    tex = bytes([mips << 4 | 1, fmt, log_h << 4 | log_w, 0, 0, 0, 0, 1]) + struct.pack('<I', 12) + bytes(4) + \
        bytes([0, 0, storage, 0])
    body = struct.pack('<I', 4) + tex + payload
    return b'GT1G0600' + struct.pack('<4I', 24 + len(body), 24, 1, 0) + body


class RiseOfTheRoninTools(unittest.TestCase):
    """KT engine formats on synthetic data. Real work needs the game's fdata_package_dx12."""

    # storage order: root, left thigh / knee / foot, right thigh / knee / foot; bone ids are sparse on purpose
    JOINTS = ((0, -1, (0, 0, 0)), (11, 0, (10, 90, 0)), (12, 1, (0, -40, 0)), (13, 2, (0, -40, 0)),
              (21, 0, (-10, 90, 0)), (22, 4, (0, -40, 0)), (23, 5, (0, -40, 0)))
    CHAINS = ((11, 12, 13), (21, 22, 23))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding ronin ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def native(self, g, bone_world_pos):
        return g.native_bind([[1, 0, 0, bone_world_pos[0]], [0, 1, 0, bone_world_pos[1]], [0, 0, 1, bone_world_pos[2]],
                              [0, 0, 0, 1]])

    def legs(self, g, segmented, bones=(11, 12, 13, 21, 22, 23)):
        """Two legs of vertices from y 90 down to 2 plus a separate 3-vertex placeholder submesh. segmented: like the
        game (knee / foot split); otherwise everything below the knee on the knee bone (the defect)."""
        world = {11: (10, 90, 0), 12: (10, 50, 0), 13: (10, 10, 0), 21: (-10, 90, 0), 22: (-10, 50, 0), 23: (-10, 10, 0)}
        palette = [(0, 0)] + [(k + 1, b) for k, b in enumerate(bones)]
        binds = [self.native(g, (0, 0, 0))] + [self.native(g, world[b]) for _, b in palette[1:]]
        slot = {b: 3 * i for i, (_, b) in enumerate(palette)}
        verts = []
        for x, chain in ((10, self.CHAINS[0]), (-10, self.CHAINS[1])):
            for y in range(90, 0, -8):
                for dz in (-2.0, 2.0):
                    if y > 50:
                        w = {chain[0]: (y - 50) / 40, chain[1]: (90 - y) / 40}
                    elif segmented:
                        w = {chain[1]: y / 50, chain[2]: 1 - y / 50}
                    else:
                        w = {chain[1]: 1.0}
                    items = [(b, v) for b, v in w.items() if v > 0][:8]
                    ws = [v for _, v in items] + [0] * (8 - len(items))
                    ss = [slot[b] for b, _ in items] + [slot[items[0][0]]] * (8 - len(items))
                    verts.append(((x + dz / 4, y, dz), ws, ss))
        n = len(verts)
        tris = [i for k in range(0, n - 3, 2) for i in (k, k + 1, k + 2)]
        return ronin_g1m(self.JOINTS, binds, [[(0, 1)]], verts + verts[:3], [palette],
                         [(0, 0, 0, n, 0, len(tris)), (0, 0, n, 3, len(tris), 3)], tris + [n, n + 1, n + 2])

    def test_ronin_g1m_parse_hide_and_binds(self):
        g = ronin('g1m_tool')
        data = self.legs(g, True)
        m = g.parse(data)
        joints, by_id = g.skeleton(m)
        self.assertEqual(by_id[13], 3)
        self.assertEqual([round(v, 4) for v in joints[3]['world_p']], [10.0, 10.0, 0.0])
        self.assertTrue(all(abs(r['error']) < 1e-5 for r in g.bind_errors(m)))
        src = self.root / 'legs.g1m'; src.write_bytes(data)
        out = self.root / 'hidden.g1m'
        cli('rise-of-the-ronin', 'g1m_tool', 'hide', src, '--submeshes', '0', '--output', out)
        hidden = out.read_bytes()
        self.assertEqual(len(hidden), len(data))
        self.assertTrue(g.is_hidden(g.parse(hidden), g.parse(hidden).submeshes[0]))
        cli('rise-of-the-ronin', 'g1m_tool', 'hide', src, '--all', '--output', out, ok=False)      # never overwrites
        # a G1H is a header plus embedded G1Ms; hiding works through the container and keeps its length
        g1h = b'_H1G0000' + struct.pack('<2I', 0, 0) + data + b'\0' * 8 + data
        models = g.embedded_models(g1h)
        self.assertEqual([x.base for x in models], [16, 16 + len(data) + 8])
        both, edits = g.collapse(g1h, models[1], models[1].submeshes[:1])
        self.assertEqual(len(both), len(g1h)); self.assertEqual(both[:16 + len(data)], g1h[:16 + len(data)])
        self.assertTrue(edits)
        # appended binds raise MM1G and FM1G counts together
        grown, before = g.append_binds(data, [self.native(g, (1, 2, 3))])
        gm = g.parse(grown)
        self.assertEqual(len(g.binds(gm)), before + 1)
        self.assertEqual(struct.unpack_from('<I', grown, gm.chunks['FM1G'].offset + 24)[0], before + 1)
        self.assertEqual(struct.unpack_from('<I', grown, 8)[0], len(grown))

    def test_ronin_g1t_storage_constant_and_compare(self):
        t = ronin('g1t_tool')
        linear = bytes(range(256)) * (524288 // 256) + bytes(131072)          # BC1 1024x1024, 2 mips
        g1t = ronin_g1t(0x59, 10, 10, 2, linear)
        info = t.describe(g1t)[0]
        self.assertEqual((info['name'], info['width'], info['mips'], info['storage']), ('BC1', 1024, 2, 0))
        tiled = t.rewrite_storage(g1t, True)
        self.assertNotEqual(tiled, g1t)
        self.assertEqual(t.rewrite_storage(tiled, False), g1t)
        self.assertEqual(t.to_dds(tiled, t.describe(tiled)[0])[148:], linear[:524288])   # dds undoes the tiles
        for fmt, rgba, want in ((0x59, [8, 150, 232, 255], [8, 150, 231]), (0x5D, [32, 129, 0, 255], [32, 129]),
                                (0x5F, [12, 12, 12, 200], [12, 12, 12, 200]), (0x5C, [77, 0, 0, 255], [77])):
            unit = t.BLOCKS[fmt][0]
            src = ronin_g1t(fmt, 3, 3, 2, bytes(range(unit)) * 4 + bytes(range(unit)))
            out = t.constant(src, rgba)
            self.assertEqual(len(out), len(src))
            self.assertEqual(t.summary(out)['textures'][0]['uniform'], want)
        one = ronin_g1t(0x02, 0, 0, 1, struct.pack('<f', 1.0), storage=1)
        zero = t.constant(one, [0, 0, 0, 0], 0.0)
        self.assertEqual([i for i, (a, b) in enumerate(zip(one, zero)) if a != b], [len(one) - 2, len(one) - 1])
        a, b = self.root / 'a.g1t', self.root / 'b.g1t'
        a.write_bytes(one); b.write_bytes(zero)
        report = json.loads(cli('rise-of-the-ronin', 'g1t_tool', 'compare', a, b).stdout)
        self.assertEqual((report['identical'], report['same_layout']), (False, True))
        self.assertEqual(report['a']['textures'][0]['uniform'], [1.0])
        out = self.root / 'c.g1t'
        cli('rise-of-the-ronin', 'g1t_tool', 'constant', a, '--float', '1.0', '--output', out)
        self.assertEqual(out.read_bytes(), one)
        mips = json.loads(cli('rise-of-the-ronin', 'g1t_tool', 'mips', a, '--reference', b).stdout)
        self.assertTrue(mips['matches_reference'])

    def ronin_game(self, g, k):
        """root.rdb / root.rdx / two fdata packages: a kidsobjdb, two KTIDs, two models, two textures."""
        def kids_entry(name, first, refs=()):
            props = [(5, 1, 0xA0, struct.pack('<I', first))] + [(5, 1, 0xB0 + i, struct.pack('<I', r)) for i, r in enumerate(refs)]
            body = struct.pack('<4I', 0, name, 0x77, len(props)) + b''.join(struct.pack('<3I', t, n, p) for t, n, p, _ in props)
            body += b''.join(v for *_, v in props)
            body += b'\0' * (-len(body) % 4)
            return b'IDOK0000' + body
        m1, m2, k1, k2, t1, t2 = 0x11110001, 0x11110002, 0x22220001, 0x22220002, 0x33330001, 0x33330002
        kids = b'_DOK0000' + bytes(20) + b''.join([
            kids_entry(0x1000, m1, (0x2000,)), kids_entry(0x2000, k1), kids_entry(0x1001, m2, (0x2001,)),
            kids_entry(0x2001, k2), kids_entry(0x3001, t1), kids_entry(0x3002, t2)])
        model1 = ronin_g1m(self.JOINTS[:1], [self.native(g, (0, 0, 0))], [[(0, 1), (1, 2)]],
                           [((0, 0, 0), [1] + [0] * 7, [0] * 8)] * 4, [[(0, 0)]], [(0, 0, 0, 4, 0, 6)], [0, 1, 2, 1, 2, 3])
        model2 = ronin_g1m(self.JOINTS[:1], [self.native(g, (0, 0, 0))], [[(0, 5)]],
                           [((0, 0, 0), [1] + [0] * 7, [0] * 8)] * 4, [[(0, 0)]], [(0, 0, 0, 4, 0, 6)], [0, 1, 2, 1, 2, 3])
        tex1, tex2 = ronin_g1t(0x02, 0, 0, 1, struct.pack('<f', 1.0)), ronin_g1t(0x59, 2, 2, 1, bytes(8))
        resources = [(k.CHARACTER_EDITOR_DB, k.KIDSOBJDB_TYPE, kids), (k1, 0x8E39AA37, struct.pack('<4I', 0, 0x3001, 1, 0x3002)),
                     (k2, 0xBE144B78, struct.pack('<2I', 0, 0x3001)), (m1, k.G1M_TYPE, model1), (m2, k.G1M_TYPE, model2),
                     (t1, 0xAFBEC60C, tex1), (t2, 0xAFBEC60C, tex2)]
        packages = {0: bytearray(b'PDRK0000' + bytes(8)), 1: bytearray(b'PDRK0000' + bytes(8))}
        rdb = bytearray(b'_DRK0000' + struct.pack('<2I', 16, 0))
        for n, (h, typ, payload) in enumerate(resources):
            pkg, mode = n % 2, n % 3          # stored, zlib with u32 chunk sizes, zlib with u16 sizes + 8 bytes
            if mode == 0:
                stored, flags = payload, 0
            elif mode == 1:
                half = len(payload) // 2
                stored = b''.join(struct.pack('<I', len(z)) + z for z in (zlib.compress(payload[:half]), zlib.compress(payload[half:])))
                flags = 0x100000
            else:
                z = zlib.compress(payload)
                stored, flags = struct.pack('<H', len(z)) + bytes(8) + z, 0
            if len(stored) == len(payload):     # equal sizes mean "stored" to the reader, as in the game
                stored, flags = payload, 0
            offset = len(packages[pkg])
            entry = b'IDRK0000' + struct.pack('<3Q4I', 48 + len(stored), len(stored), len(payload), 0, h, typ, flags) + stored
            packages[pkg] += entry + b'\0' * (-len(entry) % 16)
            trailer = (struct.pack('<HII', 0x401, offset, len(entry)) + struct.pack('<H', 100 + pkg) + b'\0') if n % 2 == 0 else \
                (struct.pack('<HB3sII', 0x401, 0, b'\0\0\0', offset, len(entry)) + struct.pack('<H', 100 + pkg) + b'\0')
            rec = b'IDRK0000' + struct.pack('<QI4sQ4s3I', 0x30 + len(trailer), len(trailer), b'\0' * 4, len(payload),
                                            b'\0' * 4, h, typ, 0) + trailer
            rdb += rec + b'\0' * (-len(rec) % 4)
        game = self.root / 'game'; game.mkdir()
        (game / 'root.rdb').write_bytes(bytes(rdb))
        (game / 'root.rdx').write_bytes(struct.pack('<HhI', 100, -1, 0xF0000000) + struct.pack('<HhI', 101, -1, 0xF0000001))
        (game / '0xf0000000.fdata').write_bytes(bytes(packages[0])); (game / '0xf0000001.fdata').write_bytes(bytes(packages[1]))
        mod = self.root / 'mod'; mod.mkdir()
        (mod / '0x33330001.g1t').write_bytes(ronin_g1t(0x02, 0, 0, 1, struct.pack('<f', 0.0)))   # the 1.0 -> 0 defect
        (mod / '0x33330002.g1t').write_bytes(tex2)
        return game, mod, (m1, m2, t1, t2), (model1, tex1)

    def test_ronin_game_data_slots_and_shared_texture_audit(self):
        g, k = ronin('g1m_tool'), ronin('ktdata')
        game, mod, (m1, m2, t1, t2), (model1, tex1) = self.ronin_game(g, k)
        data = k.GameData(game)
        self.assertEqual(data.read(m1), model1)
        self.assertEqual(data.read(t1), tex1)
        self.assertEqual(k.ktid_candidates(m1, data.kids, data.records), [0x22220001])
        out = self.root / 'out'
        rows = json.loads(cli('rise-of-the-ronin', 'ktdata', 'extract', '--game-data', game, '--hash', hex(m1),
                              '--hash', hex(t1), '--output', out).stdout)
        self.assertEqual([r['file'] for r in rows], ['0x11110001.g1m', '0x33330001.g1t'])
        cli('rise-of-the-ronin', 'ktdata', 'extract', '--game-data', game, '--hash', hex(m1), '--output', out, ok=False)
        slots = json.loads(cli('rise-of-the-ronin', 'ktdata', 'slots', '--game-data', game, '--model', hex(m1),
                               '--mod-root', mod).stdout)
        rows = slots['tables'][0]['slots']
        self.assertEqual([(r['g1t'], r['mod']) for r in rows], [('0x33330001', 'changed'), ('0x33330002', 'same as game')])
        self.assertEqual(rows[0]['uses'][0]['type'], 'COLOR')
        audit = json.loads(cli('rise-of-the-ronin', 'ktdata', 'usage', '--game-data', game, '--mod-root', mod,
                               '--own-models', hex(m1)).stdout)
        self.assertEqual(audit['changed_and_shared'], ['0x33330001'])          # the other model draws it as DIRT
        self.assertEqual(audit['textures'][0]['examples'], ['0x11110002'])

    def test_ronin_shader_blobs(self):
        s = ronin('shader_dump')
        def blob(stage, extra=b''):
            dxil = b'DXIL' + struct.pack('<2I', 12, stage << 16) + extra
            body = struct.pack('<I', 36) + dxil
            return b'DXBC' + bytes(16) + struct.pack('<3I', 1, 32 + len(body), 1) + body
        payload = b'pad' + blob(0) + blob(1) + blob(1, b'BLENDWEIGHT')
        z = zlib.compress(payload)
        entry = b'IDRK0000' + struct.pack('<3Q4I', 48 + 4 + len(z), 4 + len(z), len(payload), 0, 1, 2, 0x100000) + \
            struct.pack('<I', len(z)) + z
        self.assertEqual(s.unpack(entry), payload)
        found = s.blobs(payload)
        self.assertEqual([(b['stage'], b['blend_weights']) for b in found], [(0, False), (1, False), (1, True)])
        src = self.root / 'shader.file'; src.write_bytes(entry)
        cli('rise-of-the-ronin', 'shader_dump', src, '--output', self.root / 'dump')
        self.assertTrue((self.root / 'dump' / 'vertex-skin.dxil').is_file())

    def test_ronin_leg_reskin_follows_the_ankle(self):
        g, L = ronin('g1m_tool'), ronin('leg_weights', numpy=True)
        import numpy as np
        game_legs, broken = self.legs(g, True), self.legs(g, False)
        ref_path, tpl, out = self.root / 'ref.g1m', self.root / 'tpl.g1m', self.root / 'new.g1m'
        ref_path.write_bytes(game_legs); tpl.write_bytes(broken)
        chains = ['--left', '11,12,13', '--right', '21,22,23']
        cli('rise-of-the-ronin', 'leg_weights', 'reference', '--body', ref_path, '--wear', ref_path, '--skeleton', tpl,
            *chains, '--output', self.root / 'ref.npz')
        report = json.loads(cli('rise-of-the-ronin', 'leg_weights', 'apply', tpl, '--submesh', '0', '--reference',
                                self.root / 'ref.npz', '--foot-blend', '30', '25', '--output', out).stdout)
        self.assertEqual(report['palette_added'], [])            # every bone was already in the palette
        check = json.loads(cli('rise-of-the-ronin', 'leg_weights', 'check', tpl, out, '--submesh', '0').stdout)
        self.assertEqual(check['errors'], [])
        self.assertEqual(check['stored_weight_sum'], [1.0, 1.0])
        m0, m1 = g.parse(broken), g.parse(out.read_bytes())
        j0, b0 = g.skeleton(m0); j1, b1 = g.skeleton(m1)
        pose = {13: ('x', 35)}                                     # bend the left foot bone
        P, rest0 = L.skin(m0, m0.submeshes[0], L.worlds(m0)[0])
        _, q0 = L.skin(m0, m0.submeshes[0], L.posed_worlds(j0, b0, pose))
        _, rest1 = L.skin(m1, m1.submeshes[0], L.worlds(m1)[0])
        _, q1 = L.skin(m1, m1.submeshes[0], L.posed_worlds(j1, b1, pose))
        feet = (P[:, 1] < 20) & (P[:, 0] > 0)
        self.assertLess(float(np.abs(q0[feet] - rest0[feet]).max()), 1e-6)    # before: the foot ignores the ankle
        self.assertGreater(float(np.linalg.norm(q1[feet] - rest1[feet], axis=1).mean()), 0.5)
        # a bone the palette lacks (the foot) is appended with a native bind
        short = self.legs(g, False, bones=(11, 12, 21, 22, 23))
        grown, rep = L.reskin(short, 0, dict(np.load(self.root / 'ref.npz')), None,
                              ((11, 12, 13), (21, 22, 23)), (30.0, 25.0))
        self.assertEqual(rep['palette_added'], [13])
        gm = g.parse(grown)
        self.assertTrue(all(r['error'] < 1e-4 for r in g.bind_errors(gm) if r['joint'] == 13))
        self.assertQuantised(L)

    def assertQuantised(self, L):
        q = L.quantise({1: 0.333333, 2: 0.333333, 3: 0.333334, 4: 1e-5})
        self.assertEqual(sum(x for _, x in q), 1.0)
        self.assertTrue(all((x * 2048).is_integer() for _, x in q))
        self.assertEqual(len(q), 3)


DD2_NUMPY_SCRIPTS = ('build_karin_textures',)


def dd2_missing():
    return [m for m in ('numpy', 'PIL') if importlib.util.find_spec(m) is None]


def quat_rotate(q, v):
    """Rotate v by the unit quaternion q = (x, y, z, w)."""
    x, y, z, w = q
    t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])]
    return [v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2],
            v[2] + w * t[2] + x * t[1] - y * t[0]]


def unit(v):
    n = sum(c * c for c in v) ** 0.5
    return [c / n for c in v]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def rot_rows(axis, deg):
    """Rotation by deg about axis, as rows = the rotated X, Y, Z axes (the RE row-major matrix convention)."""
    import math
    x, y, z = unit(axis)
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
         [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
         [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]
    return [[m[j][i] for j in range(3)] for i in range(3)]


def dd2_bone(name, parent, rows, pos, local_x):
    """meshinfo-style bone: global = 16 floats (rows 0..2 axes in model space, row 3 position), local row 0 = X."""
    glob = [c for r in rows for c in (*r, 0.0)] + [*pos, 1.0]
    return {'name': name, 'parent': parent, 'global': glob, 'local': [*unit(local_x), 0.0] + [0.0] * 12}


class DragonsDogma2Tools(unittest.TestCase):
    """Chain spec math, mesh header patch, CLSP reader and the dev console client, on synthetic data. DD2Tool (C#),
    the REFramework Lua scripts and the Blender scripts need .NET, the game or Blender and are not run here."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding dd2 ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_dd2_chain_spec_swing_and_tilt(self):
        import math
        m = module('dragons-dogma-2', 'make_chain_spec')
        for d in ([1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, 0, -1], [0.3, -0.8, 0.5], [-0.99, 0.01, 0.1], [2, 2, -1]):
            q = m.swing_from_x(d)
            self.assertAlmostEqual(dot(q, q), 1.0, places=12)
            self.assertEqual(q[0], 0.0)                        # a swing: no twist about X
            for a, b in zip(quat_rotate(q, [1.0, 0.0, 0.0]), unit(d)):
                self.assertAlmostEqual(a, b, places=12)
        # skirt-like rig: four roots around a vertical axis off the origin, under a tilted hip; two-node chains whose
        # rest directions point mostly down, in rotated parent frames
        centre = (0.05, 0.9, -0.02)
        bones = [dd2_bone('Hip', None, rot_rows([0.3, 1.0, 0.2], 25), (0.0, 1.0, 0.0), [1, 0, 0])]
        groups = []
        for k in range(4):
            t = math.radians(90 * k + 10)
            pos = (centre[0] + 0.15 * math.cos(t), centre[1], centre[2] + 0.12 * math.sin(t))
            root, tip = f'K_Skirt_{k}', f'K_Skirt_{k}_1'
            bones.append(dd2_bone(root, 'Hip', rot_rows([math.cos(t), 0.4, math.sin(t)], 40 + 7 * k), pos,
                                  [0.2 * math.cos(t), -1.0, 0.25 * math.sin(t) + 0.1]))
            bones.append(dd2_bone(tip, root, rot_rows([0, 0, 1], 0), (pos[0], pos[1] - 0.1, pos[2]), [0.05, -1.0, 0.3]))
            groups.append({'joints': [root, tip], 'setting': 'skirt'})
        groups.append({'joints': ['K_Skirt_0'], 'setting': 'hair'})      # other settings are left alone
        angle = 0.25
        m.tilt_outward({'bones': bones}, groups, 'skirt', angle)
        self.assertNotIn('aldir', groups[-1])
        by = {b['name']: b for b in bones}
        cx = sum(by[g['joints'][0]]['global'][12] for g in groups[:4]) / 4
        cz = sum(by[g['joints'][0]]['global'][14] for g in groups[:4]) / 4
        for g in groups[:4]:
            r = by[g['joints'][0]]['global']
            u = [r[12] - cx, 0.0, r[14] - cz]                    # outward, horizontal, from the roots' centre axis
            self.assertEqual(len(g['aldir']), len(g['joints']))
            for j, q in zip(g['joints'], g['aldir']):
                pm = by[by[j]['parent']]['global']
                axes = [pm[4 * i:4 * i + 3] for i in range(3)]    # parent axes in model space
                d = by[j]['local'][0:3]                          # rest direction, parent frame
                v = quat_rotate(q, [1.0, 0.0, 0.0])               # cone axis, parent frame
                self.assertAlmostEqual(math.acos(max(-1.0, min(1.0, dot(v, d)))), angle, places=9)

                def to_model(c):
                    return [sum(c[i] * axes[i][k] for i in range(3)) for k in range(3)]
                self.assertGreater(dot(to_model(v), u), dot(to_model(d), u) + 1e-3)   # turned away from the axis
                up = [dot(axes[i], u) for i in range(3)]
                normal = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]]
                self.assertAlmostEqual(dot(v, normal), 0.0, places=9)   # turned in the plane of d and u

    def test_dd2_patch_mesh_header(self):
        body = (struct.pack('<II', 0x4853454D, 251205828) + bytes(range(14)) + struct.pack('<H', 33411)
                + bytes(range(200, 240)))
        mesh = self.root / 'karin body.mesh.260421070'
        mesh.write_bytes(body)
        out = cli('dragons-dogma-2', 'patch_mesh_header', mesh).stdout
        self.assertIn('flags 33411 -> 4099', out)
        patched = mesh.read_bytes()
        self.assertEqual(struct.unpack_from('<H', patched, 22)[0], 4099)
        self.assertEqual(patched[:22] + patched[24:], body[:22] + body[24:])
        cli('dragons-dogma-2', 'patch_mesh_header', mesh, '--flags', 3)
        self.assertEqual(struct.unpack_from('<H', mesh.read_bytes(), 22)[0], 3)
        old = self.root / 'old.mesh.240423143'
        old_bytes = struct.pack('<II', 0x4853454D, 240423143) + bytes(32)
        old.write_bytes(old_bytes)
        cli('dragons-dogma-2', 'patch_mesh_header', old, ok=False)      # only the DD2 V3 (.260421070) layout
        self.assertEqual(old.read_bytes(), old_bytes)

    def test_dd2_clsp_dump_reads_presets(self):
        m = module('dragons-dogma-2', 'clsp_dump')
        self.assertEqual(m.murmur3(b'', 1), 0x514E28B7)              # MurmurHash3 x86_32 reference vectors
        self.assertEqual(m.murmur3(b'Hello, world!', 1234), 0xFAF6CDB3)
        self.assertEqual(m.name_hash('L_Breast'), 1164880656)          # the value DD2Tool (REE-Lib) prints for it
        capsule = bytearray(112)
        struct.pack_into('<IIIIii', capsule, 0, 1, m.name_hash('L_Leg_Upper'), m.name_hash(''), 0, 1 << 14, 0)
        struct.pack_into('<3f', capsule, 32, 0.1, 0.2, 0.3)
        struct.pack_into('<3f', capsule, 48, 0.4, 0.5, 0.6)
        struct.pack_into('<f', capsule, 64, 0.05)
        sphere = bytearray(112)
        struct.pack_into('<IIIIii', sphere, 0, 0, 0x1234, m.name_hash(''), 0, 0, 7)
        struct.pack_into('<4f', sphere, 32, 1.0, 2.0, 3.0, 0.25)
        clsp = self.root / 'synthetic.clsp.3'
        clsp.write_bytes(struct.pack('<IiQ', 0x50534C43, 2, 32) + bytes(16) + capsule + sphere)
        rows = m.parse(clsp, {m.name_hash('L_Leg_Upper'): 'L_Leg_Upper', m.name_hash(''): '<none>'})
        self.assertEqual([r['shape'] for r in rows], ['Capsule', 'Sphere'])
        self.assertEqual((rows[0]['joint'], rows[0]['pair'], rows[0]['flags1']), ('L_Leg_Upper', '<none>', 16384))
        self.assertEqual((rows[0]['p0'], rows[0]['p1'], rows[0]['r']), ([0.1, 0.2, 0.3], [0.4, 0.5, 0.6], 0.05))
        self.assertEqual((rows[1]['joint'], rows[1]['flags2'], rows[1]['pos'], rows[1]['r']),
                         ('0x1234', 7, [1.0, 2.0, 3.0], 0.25))
        meshinfo = self.root / 'meshinfo.json'
        meshinfo.write_text(json.dumps({'bones': [{'name': 'L_Leg_Upper'}]}))
        out = self.root / 'rows.json'
        cli('dragons-dogma-2', 'clsp_dump', clsp, meshinfo, '--json', out)
        self.assertEqual(json.loads(out.read_text())[0]['joint'], 'L_Leg_Upper')

    def test_dd2_devcmd_round_trip_and_missing_game(self):
        import time
        script = KITS / 'dragons-dogma-2' / 'scripts' / 'devcmd.py'
        if not script.is_file():
            self.skipTest('dragons-dogma-2 is not included in this single-game export')
        env = {k: v for k, v in os.environ.items() if k != 'DD2_GAME_DIR'}

        def run(*args):
            return subprocess.run([sys.executable, '-B', str(script), *map(str, args)], capture_output=True, text=True,
                                  env=env, timeout=30)
        missing = run('-e', 'return 1')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('DD2_GAME_DIR', missing.stderr)
        game = self.root / 'Dragons Dogma 2'
        self.assertNotEqual(run('-e', 'return 1', '--game-dir', game).returncode, 0)
        self.assertFalse(game.exists())                                  # nothing is created for a wrong folder
        (game / 'reframework').mkdir(parents=True)
        data = game / 'reframework' / 'data' / 'karin_dev'
        process = subprocess.Popen([sys.executable, '-B', str(script), '-e', 'return K.player() ~= nil', '--timeout', '20',
                                    '--game-dir', str(game)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   env=env)
        try:
            cmd, deadline = None, time.time() + 15
            while cmd is None and time.time() < deadline:            # stand in for karin_dev.lua: answer the command
                try:
                    cmd = json.loads((data / 'cmd.json').read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    time.sleep(0.05)
            self.assertIsNotNone(cmd)
            self.assertEqual(cmd['lua'], 'return K.player() ~= nil')
            (data / 'result.json').write_text(json.dumps({'id': cmd['id'], 'result': True}), encoding='utf-8')
            stdout, stderr = process.communicate(timeout=20)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.assertEqual(process.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout), {'id': cmd['id'], 'result': True})


SIFU_KIT = KITS / 'sifu'
SIFU_DEPENDENCIES = {'make_textures': ('numpy', 'PIL'), 'frames_to_gif': ('PIL',)}


def sifu_missing(script):
    """Modules a Sifu plain-Python script needs that are not installed (the other scripts use the standard library)."""
    return [m for m in SIFU_DEPENDENCIES.get(script, ()) if importlib.util.find_spec(m) is None]


def sifu_run(name, *args, env=None, ok=True):
    """Run a Sifu kit script with its own SIFU_* environment (profiles.py reads SIFU_MODELS_DIR at import time)."""
    path = SIFU_KIT / 'scripts' / f'{name}.py'
    if not path.is_file():
        raise unittest.SkipTest('sifu is not included in this single-game export')
    if sifu_missing(name):
        raise unittest.SkipTest('pip install -r requirements.txt -r portable-kits/sifu/requirements.txt (missing '
                                + ', '.join(sifu_missing(name)) + ')')
    full = {k: v for k, v in os.environ.items() if not k.startswith('SIFU_')}
    full.update(env or {}, PYTHONIOENCODING='utf-8')
    process = subprocess.run([sys.executable, '-B', str(path), *map(str, args)], capture_output=True, text=True,
                             encoding='utf-8', env=full, timeout=300)
    if (process.returncode == 0) != ok:
        raise AssertionError(f'{name}: exit {process.returncode}\n{process.stdout}\n{process.stderr}')
    return process


def png(path, mode, size, colour):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size, colour).save(path)


class SifuTools(unittest.TestCase):
    """Bone-chain tuning, textures, release packaging and burst GIFs on synthetic data. The Blender build, the UE
    Python, the PowerShell tools, the editor plugin (C++) and SifuExport (C#) need Blender, UE 4.26 or the game."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding sifu ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    @staticmethod
    def dynamics():
        """Two simulated chains on spare bones plus two kinematic colliders, in the layout dyn_stage.py writes."""
        def body(bone, length, radius, kinematic=False):
            return {'bone': bone, 'type': 'capsule', 'center': [length / 2, 0.0, 0.0], 'radius': radius,
                    'length': length, 'kinematic': kinematic}
        bodies = [body('pelvis', 20.0, 9.0, True), body('head', 18.0, 8.0, True),
                  body('cloth_a_01', 12.0, 2.0), body('cloth_a_02', 10.0, 1.5), body('acc_side_l', 8.0, 1.0)]
        joints = [{'child': b, 'parent': p} for b, p in (('cloth_a_01', 'pelvis'), ('cloth_a_02', 'cloth_a_01'),
                                                         ('acc_side_l', 'head'))]
        tune = dict(masses=[0.3, 0.2], freq=1.5, zeta=0.5, lin_damp=8.0, ang_damp=4.0, swing=[40, 30], twist=6,
                    collide=['pelvis'])
        chains = [{'name': 'A', 'bones': ['cloth_a_01', 'cloth_a_02'], 'tune': tune},
                  {'name': 'Hair_side_L', 'bones': ['acc_side_l']}]           # no tune: the module's CHAINS entry
        return {'bodies': bodies, 'joints': joints, 'chains': chains, 'rest_overlap_pairs': [['cloth_a_01', 'pelvis']]}

    def test_sifu_dyn_tuning_drives_and_collision_filter(self):
        import math
        m = module('sifu', 'dyn_tuning')
        dyn = self.dynamics()
        node = {'stale': True}
        report = m.apply(dyn, node)
        self.assertEqual(node, m.NODE)                                       # node replaced, not merged
        bodies = {b['bone']: b for b in dyn['bodies']}
        joints = {j['child']: j for j in dyn['joints']}

        def icom(b):                                                         # capsule inertia about its COM
            length = b['length'] + 2 * b['radius']
            return b['mass'] * (length * length / 12 + b['radius'] ** 2 / 4)
        # chain A: sub-chain inertia about each joint by the parallel-axis theorem along the straight chain
        a1, a2 = bodies['cloth_a_01'], bodies['cloth_a_02']
        self.assertEqual((a1['mass'], a2['mass'], a1['lin_damp'], a2['ang_damp']), (0.3, 0.2, 8.0, 4.0))
        s1, s2 = 12.0, 10.0
        isub = [icom(a1) + 0.3 * (s1 / 2) ** 2 + icom(a2) + 0.2 * (s1 + s2 / 2) ** 2, icom(a2) + 0.2 * (s2 / 2) ** 2]
        w = 2 * math.pi * 1.5
        for k, (bone, body) in enumerate((('cloth_a_01', a1), ('cloth_a_02', a2))):
            jt = joints[bone]
            self.assertEqual(jt['drive_stiffness'], round(w * w * isub[k] / icom(body), 1))
            self.assertEqual(jt['drive_damping'], round(2 * 0.5 * w * isub[k] / icom(body), 2))
            self.assertEqual((jt['swing1'], jt['swing2'], jt['twist']), ([40.0, 30.0][k],) * 2 + (6.0,))
            # acceleration drive on I_com gives the sub-chain its mode frequency about the joint
            self.assertAlmostEqual(jt['drive_stiffness'] * icom(body) / isub[k] / (w * w), 1.0, places=3)
            self.assertEqual(report['A'][k]['bone'], bone)
        side = m.CHAINS['Hair_side_L']
        self.assertEqual(bodies['acc_side_l']['mass'], side['masses'][0])
        self.assertEqual(joints['acc_side_l']['swing1'], float(side['swing'][0]))
        # collisions: only the chain's own colliders, plus pairs overlapping at rest; chains never touch each other
        expected = {('cloth_a_01', 'head'), ('cloth_a_02', 'head'), ('cloth_a_01', 'pelvis'), ('acc_side_l', 'pelvis'),
                    ('cloth_a_01', 'acc_side_l'), ('cloth_a_02', 'acc_side_l')}
        self.assertEqual(dyn['disable_pairs'], sorted([list(p) for p in expected]))
        self.assertNotIn(['cloth_a_02', 'pelvis'], dyn['disable_pairs'])
        self.assertNotIn(['acc_side_l', 'head'], dyn['disable_pairs'])
        # command line: re-tunes cloth.json in place, keeps the other sections, prints the per-joint report
        cloth = self.root / 'cloth.json'
        cloth.write_text(json.dumps({'cloth': [{'name': 'Cloth_Skirt'}], 'dynamics': self.dynamics(),
                                     'rigidbody': {'stale': True}}), encoding='utf-8')
        printed = json.loads(sifu_run('dyn_tuning', cloth).stdout)
        data = json.loads(cloth.read_text(encoding='utf-8'))
        self.assertEqual(data['dynamics'], json.loads(json.dumps(dyn)))
        self.assertEqual(data['rigidbody'], m.NODE)
        self.assertEqual(data['cloth'], [{'name': 'Cloth_Skirt'}])
        self.assertEqual(printed, json.loads(json.dumps(report)))

    def test_sifu_make_textures_channels_and_ue_build(self):
        if sifu_missing('make_textures'):
            self.skipTest('pip install -r portable-kits/sifu/requirements.txt (missing '
                          + ', '.join(sifu_missing('make_textures')) + ')')
        import numpy as np
        from PIL import Image
        models, work, remote = self.root / 'models', self.root / 'work y', 'Remote/work/y'
        colours = {'SkinFace': (200, 150, 120), 'HairCostume': (240, 240, 250), 'ClothUV123': (20, 30, 90),
                   'ClothUV4567': (180, 20, 40), 'AccentsProps': (90, 90, 90)}
        for page, colour in colours.items():                       # profile "y": Atlas_<page>_BaseColor.png pages
            png(models / 'Karin_Y_BlenderSafe' / 'textures' / f'Atlas_{page}_BaseColor.png', 'RGBA', (8, 8), colour + (37,))
            ao = Image.fromarray(np.array([[0, 128], [255, 64]], np.uint8), 'L')
            (work / 'ao').mkdir(parents=True, exist_ok=True)
            ao.save(work / 'ao' / f'AO_{page}.png')
        env = {'SIFU_MODELS_DIR': str(models)}
        out = sifu_run('make_textures', 'y', work, remote, env=env).stdout
        self.assertIn('TEXTURES_DONE 13 textures, 6 materials', out)
        tex = work / 'tex'
        flat, black = Image.open(tex / 'T_Karin_Flat_N.png'), Image.open(tex / 'T_Karin_Black.png')
        self.assertEqual((flat.mode, flat.size, black.mode, black.size), ('RGB', (64, 64), 'RGB', (16, 16)))
        self.assertTrue((np.asarray(flat) == [128, 128, 255]).all() and not np.asarray(black).any())
        for name, page, alpha in (('T_Y_SkinFace_CS', 'SkinFace', 255), ('T_Y_ClothUV123_C', 'ClothUV123', 0)):
            a = np.asarray(Image.open(tex / f'{name}.png'))
            self.assertEqual(a.shape, (2048, 2048, 4))                 # skin keeps alpha 255, cloth and hair 0 (W-like)
            self.assertTrue((a[..., 3] == alpha).all())
            src = Image.open(models / 'Karin_Y_BlenderSafe' / 'textures' / f'Atlas_{page}_BaseColor.png')
            self.assertTrue((a[..., :3] == np.asarray(src.convert('RGBA').resize((2048, 2048), Image.LANCZOS))[..., :3]).all())
        ao = np.array([[0, 128], [255, 64]]) / 255.0
        for name, rough, calpha, strength in (('T_Y_SkinFace_S_face', 140, 230, 0.6), ('T_Y_SkinFace_S_skin', 150, 230, 0.8),
                                              ('T_Y_HairCostume_S_hair', 115, 255, 0.9), ('T_Y_ClothUV123_S_cloth', 205, 255, 1.0)):
            s = np.asarray(Image.open(tex / f'{name}.png')).astype(int)
            self.assertEqual(s.shape, (2, 2, 4))                       # ComboMap: R rough, G metal 0, B AO, A mask
            self.assertTrue((s[..., 0] == rough).all() and not s[..., 1].any() and (s[..., 3] == calpha).all())
            want = np.round(np.clip(1.0 - strength * (1.0 - ao), 0, 1) ** 0.8 * 255)
            self.assertLessEqual(np.abs(s[..., 2] - want).max(), 1)
        cfg = json.loads((work / 'ue_build.json').read_text(encoding='utf-8'))
        self.assertEqual((cfg['fbx'], cfg['cloth_json'], cfg['out_json'], cfg['asset_dir']),
                         (remote + '/SK_W_MainChar_01.fbx', remote + '/cloth.json', remote + '/ue_build_out.json', 'Karin_Y'))
        self.assertEqual(sorted(cfg['textures']), sorted(p.stem for p in tex.glob('*.png')))
        self.assertTrue(all(path == f'{remote}/tex/{name}.png' for name, (path, _) in cfg['textures'].items()))
        self.assertEqual(cfg['textures']['T_Karin_Flat_N'][1], 'normal')
        face, body, cloth = cfg['materials']['Karin_Face'], cfg['materials']['Karin_Body'], cfg['materials']['Karin_Cloth123']
        self.assertEqual((face['parent'], face['BaseColor'], face['ComboMap'], face['textures']['Color_Old']),
                         ('w_head', 'T_Y_SkinFace_CS', 'T_Y_SkinFace_S_face', 'T_Y_SkinFace_CS'))
        self.assertEqual((body['parent'], body['ComboMap']), ('w_body', 'T_Y_SkinFace_S_skin'))
        self.assertEqual((cloth['parent'], cloth['Normal'], cloth['ComboMap']), ('w_cloth', 'T_Karin_Flat_N', 'T_Y_ClothUV123_S_cloth'))
        # --flat-dir copies existing files instead of generating them
        given, work2 = self.root / 'flat', self.root / 'work2'
        png(given / 'T_Karin_Flat_N.png', 'RGB', (2, 2), (1, 2, 3))
        png(given / 'T_Karin_Black.png', 'RGB', (2, 2), (4, 5, 6))
        (work2 / 'ao').mkdir(parents=True)
        for page in colours:
            (work2 / 'ao' / f'AO_{page}.png').write_bytes((work / 'ao' / f'AO_{page}.png').read_bytes())
        sifu_run('make_textures', 'y', work2, remote, '--flat-dir', given, env=env)
        self.assertEqual(Image.open(work2 / 'tex' / 'T_Karin_Flat_N.png').getpixel((1, 1)), (1, 2, 3))
        # without SIFU_MODELS_DIR the atlas pages are not found
        sifu_run('make_textures', 'y', self.root / 'work3', remote, ok=False)

    def test_sifu_package_release_folder_and_zip(self):
        import hashlib
        import zipfile
        pak = 'pakchunk99-KarinY_P'
        out, release = self.root / 'out', self.root / 'release'
        (out / 'y').mkdir(parents=True)
        (out / 'y' / f'{pak}.pak').write_bytes(b'synthetic pak ' * 100)
        (out / 'y' / f'{pak}.sig').write_bytes(b'synthetic sig')
        game = 'Games\\Steam\\steamapps\\common\\Sifu'
        sifu_run('package_release', 'y', 3, '2026-10-13', '--out-root', out, '--release-dir', release, '--game-dir', game + '\\')
        folder = release / pak
        self.assertEqual(sorted(p.name for p in folder.iterdir()), sorted([f'{pak}.pak', f'{pak}.sig', '安装说明.txt']))
        for ext in ('.pak', '.sig'):
            self.assertEqual((folder / f'{pak}{ext}').read_bytes(), (out / 'y' / f'{pak}{ext}').read_bytes())
        raw = (folder / '安装说明.txt').read_bytes()
        self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'))            # CRLF text for Windows users
        text = raw.decode('utf-8')
        self.assertIn('版本 v3（2026-10-13）', text)
        self.assertIn(f'   {game}\\Sifu\\Content\\Paks\\\r\n', text)          # trailing separator of --game-dir dropped
        for ext in ('.pak', '.sig'):
            self.assertIn(f'{pak}{ext}  {hashlib.md5((out / "y" / f"{pak}{ext}").read_bytes()).hexdigest()}', text)
        self.assertIn('苦无', text)                                         # the profile's own note
        with zipfile.ZipFile(release / f'{pak}_v3.zip') as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(z.namelist(), [f'{pak}/{pak}.pak', f'{pak}/{pak}.sig', f'{pak}/安装说明.txt'])
            for name in z.namelist():
                self.assertEqual(z.read(name), (folder / name.split('/', 1)[1]).read_bytes())
        # the example path falls back to SIFU_GAME_DIR, then to a placeholder
        for env, want in (({'SIFU_GAME_DIR': 'Games\\Sifu'}, 'Games\\Sifu\\Sifu'), ({}, '<Steam 库>\\steamapps\\common\\Sifu\\Sifu')):
            target = self.root / f'release {len(env)}'
            sifu_run('package_release', 'y', 3, '2026-10-13', '--out-root', out, '--release-dir', target, env=env)
            self.assertIn(want, (target / pak / '安装说明.txt').read_text(encoding='utf-8'))
        # profiles without release text, and a missing release folder argument, are refused before anything is written
        bad = self.root / 'bad'
        sifu_run('package_release', 'karin_original', 1, '2026-10-13', '--out-root', out, '--release-dir', bad, ok=False)
        sifu_run('package_release', 'y', 1, '2026-10-13', '--out-root', out, ok=False)
        self.assertFalse(bad.exists())

    def test_sifu_frames_to_gif_timings_and_sheet(self):
        if sifu_missing('frames_to_gif'):
            self.skipTest('pip install -r requirements.txt (missing Pillow)')
        from PIL import Image
        cap = self.root / 'cap'
        cap.mkdir()
        for i, colour in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))):
            Image.new('RGB', (20, 10), colour).save(cap / f'run_{i:03d}.jpg', quality=95)
        (cap / 'run.txt').write_text('0.0\n66.4\n133.0\n200.2', encoding='utf-8')
        out = sifu_run('frames_to_gif', cap, 'run', self.root / 'run').stdout
        self.assertIn('4 frames', out)
        with Image.open(self.root / 'run.gif') as gif:
            self.assertEqual((gif.n_frames, gif.size), (4, (20, 10)))
            durations = []
            for i in range(gif.n_frames):
                gif.seek(i)
                durations.append(gif.info['duration'])
        for got, want in zip(durations, (66, 67, 67, 100)):                 # GIF stores 10 ms units
            self.assertLess(abs(got - want), 10)
        sifu_run('frames_to_gif', cap, 'run', self.root / 'crop', 0, 0, 10, 5, 2)
        for name, size in (('run_sheet.jpg', (6 * 20, 10)), ('crop.gif', (10, 5)), ('crop_sheet.jpg', (2 * 10, 2 * 5))):
            with Image.open(self.root / name) as im:                          # sheet: 6 columns by default
                self.assertEqual(im.size, size)


PAL_KIT = KITS / 'palworld'
PAL_GROUPS = {'skirt', 'tail', 'twintails', 'sidehair', 'fronthair', 'ears', 'ribbons'}
PAL_SETTINGS = ('damping', 'stiffness', 'world_loc', 'world_rot', 'radius', 'limit_angle')


def pal_kit():
    if not PAL_KIT.is_dir():
        raise unittest.SkipTest('palworld is not included in this single-game export')
    return PAL_KIT


def pal_source(rel):
    return (pal_kit() / rel).read_text(encoding='utf-8')


def pal_functions(rel, names, **namespace):
    """Top-level functions of a Blender script compiled on their own (the script itself needs bpy at import time)."""
    tree = ast.parse(pal_source(rel))
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if sorted(n.name for n in body) != sorted(names):
        raise AssertionError(f'{rel}: expected functions {names}, found {[n.name for n in body]}')
    exec(compile(ast.Module(body=body, type_ignores=[]), str(pal_kit() / rel), 'exec'), namespace)
    return namespace


def pal_strings(rel, function=None):
    """String constants of a script, or of one of its top-level functions."""
    tree = ast.parse(pal_source(rel))
    if function:
        tree = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


class PalworldTools(unittest.TestCase):
    """Kawaii tune merge and curves, the tuning file, gen_ue_config.py and the PowerShell tools on synthetic data. The
    Blender build and simulator, the UE Python, the PalModTools plugin (C++) and PalExport (C#) need Blender, UE 5.1 or
    the game."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding palworld ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_pal_kawaii_merge_and_curve(self):
        tune = {'skirt': {'damping': 0.15, 'limit_angle': 65, 'gravity': [0, 0, -80], 'stiffness_curve': [[0, 1], [1, 0.7]],
                          'capsule_radius': {'thigh_l': 7.5}, 'extra_capsules': [{'bone': 'pelvis', 'a': [0, 0, 80],
                                                                                  'b': [1, 0, 80], 'radius': 9.0}],
                          'note': 'ignored'},
                'tail': {'capsules': [{'bone': 'pelvis', 'a': [-4, 0, 82], 'b': [4, 0, 82], 'radius': 9.75},
                                      {'bone': 'thigh_r', 'a': [-9, 0, 82], 'b': [-9, 1, 76], 'radius': 9.5}],
                         'capsule_radius': {'pelvis': 3.0}, 'dummy': 2.0, 'ring_levels': [1, 2], 'compliance': 'Rubber'}}
        ns = pal_functions('scripts/blender/kawaii_sim.py', ['merged', 'curve'], json=json, TUNE=tune)
        merged, curve = ns['merged'], ns['curve']
        # curves: linear multipliers over the length rate from the root, clamped to the end keys, 1.0 when absent
        keys = [[0, 1], [0.5, 0.8], [1, 0.5]]
        self.assertEqual(curve(None, 0.3), 1.0)
        self.assertEqual(curve([], 0.3), 1.0)
        for x, want in ((-1, 1.0), (0, 1.0), (0.25, 0.9), (0.5, 0.8), (0.75, 0.65), (1, 0.5), (2, 0.5)):
            self.assertAlmostEqual(curve(keys, x), want)
        # physics.json group (geometry and default dynamics) + physics_tune.json dynamics
        settings = dict(damping=0.25, stiffness=0.12, world_loc=0.8, world_rot=0.8, radius=2.5, limit_angle=40)
        derived = [{'bone': 'thigh_l', 'a': [9, 0, 80], 'b': [9, 1, 70], 'radius': 9.0, 'vrm_radius': 10.0},
                   {'bone': 'thigh_r', 'a': [-9, 0, 80], 'b': [-9, 1, 70], 'radius': 9.0, 'vrm_radius': 10.0}]
        skirt = {'name': 'skirt', 'roots': ['skirtA_02', 'skirtB_02'], 'settings': dict(settings), 'capsules': derived,
                 'gravity': [0, 0, -60]}
        before = json.dumps(skirt)
        m = merged(skirt)
        self.assertEqual(json.dumps(skirt), before)                          # the input group is not modified
        self.assertEqual(m['settings'], dict(settings, damping=0.15, limit_angle=65))
        self.assertEqual((m['gravity'], m['stiffness_curve'], m['roots']), ([0, 0, -80], [[0, 1], [1, 0.7]], skirt['roots']))
        self.assertNotIn('note', m)
        self.assertEqual([(c['bone'], c['radius']) for c in m['capsules']], [('thigh_l', 7.5), ('thigh_r', 9.0), ('pelvis', 9.0)])
        # explicit capsules replace the derived ones (radius overrides still apply) and are copied, not shared
        tail = merged({'name': 'tail', 'roots': ['cloth_A_01'], 'settings': dict(settings), 'capsules': derived})
        self.assertEqual([(c['bone'], c['radius']) for c in tail['capsules']], [('pelvis', 3.0), ('thigh_r', 9.5)])
        self.assertEqual((tail['dummy'], tail['ring_levels'], tail['compliance'], tail['settings']), (2.0, [1, 2], 'Rubber', settings))
        self.assertNotIn('gravity', tail)
        tail['capsules'][0]['radius'] = 99
        self.assertEqual(tune['tail']['capsules'][0]['radius'], 9.75)
        # every physics.json group needs a physics_tune.json entry
        with self.assertRaises(KeyError):
            merged({'name': 'ears', 'roots': ['ear_01'], 'settings': dict(settings)})

    def test_pal_physics_tune_covers_build_groups(self):
        tune = json.loads(pal_source('scripts/physics_tune.json'))['groups']
        # the groups build_pal.py writes to physics.json (group("<name>", ...) calls) all have tuning entries
        tree = ast.parse(pal_source('scripts/blender/build_pal.py'))
        built = {n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'group'
                 and n.args and isinstance(n.args[0], ast.Constant)}
        self.assertEqual(built, PAL_GROUPS)
        self.assertEqual(set(tune), PAL_GROUPS)
        known = pal_strings('scripts/blender/kawaii_sim.py', 'merged')       # keys merged() reads; others are ignored
        number = (int, float)
        for name, t in tune.items():
            with self.subTest(group=name):
                self.assertFalse(set(t) - known, 'keys the simulator and ue_build_abp.py would ignore')
                for k in ('damping', 'stiffness', 'world_loc', 'world_rot'):
                    if k in t: self.assertTrue(0 <= t[k] <= 1, k)
                if 'radius' in t: self.assertGreater(t['radius'], 0)
                if 'limit_angle' in t: self.assertTrue(0 <= t['limit_angle'] <= 180)
                if 'gravity' in t: self.assertTrue(len(t['gravity']) == 3 and all(isinstance(v, number) for v in t['gravity']))
                for k in ('stiffness_curve', 'damping_curve', 'limit_angle_curve'):
                    if k in t:
                        xs = [p[0] for p in t[k]]
                        self.assertTrue(all(len(p) == 2 and p[1] >= 0 for p in t[k]) and xs == sorted(set(xs)))
                        self.assertTrue(0 <= xs[0] and xs[-1] <= 1)
                for c in t.get('capsules', []) + t.get('extra_capsules', []):
                    self.assertTrue(isinstance(c['bone'], str) and c['radius'] > 0 and len(c['a']) == len(c['b']) == 3)
        # merged against a synthetic physics.json: every node gets numeric settings, ue_build_abp.py reads all of them
        ns = pal_functions('scripts/blender/kawaii_sim.py', ['merged'], json=json, TUNE=tune)
        defaults = dict(damping=0.3, stiffness=0.15, world_loc=0.8, world_rot=0.8, radius=1.5, limit_angle=35)
        for name in sorted(PAL_GROUPS):
            g = ns['merged']({'name': name, 'roots': [f'{name}_01'], 'settings': dict(defaults), 'capsules': []})
            self.assertTrue(all(isinstance(g['settings'][k], number) for k in PAL_SETTINGS))
        abp = pal_strings('scripts/ue/ue_build_abp.py')
        self.assertTrue(set(PAL_SETTINGS) | {'gravity', 'dummy', 'capsules', 'stiffness_curve', 'damping_curve',
                                             'limit_angle_curve'} <= abp)

    def test_pal_gen_ue_config_paths_and_helpers(self):
        missing = [m for m in ('numpy', 'PIL') if importlib.util.find_spec(m) is None]
        if missing:
            self.skipTest('pip install -r requirements.txt -r portable-kits/palworld/requirements.txt (missing '
                          + ', '.join(missing) + ')')
        from PIL import Image
        script = pal_kit() / 'scripts' / 'gen_ue_config.py'
        player = 'Pal/Content/Pal/Model/Character/Player'
        listing = self.root / 'player list.txt'
        listing.write_text('\n'.join([
            'mounted 1 containers, 9 files',                                   # PalExport's stderr line (2>&1)
            f'{player}/Head/Head010/SK_Player_Female_Head010.uasset', f'{player}/Head/Head010/SK_Player_Female_Head010.uexp',
            f'{player}/Head/Head002/SK_Player_Female_Head002.uasset', f'{player}/Head/Head002/SK_Player_Male_Head002.uasset',
            f'{player}/Head/Head002/MI_Player_Female_Head002.uasset', f'{player}/Hair/Hair003/SK_Player_Hair003.uasset',
            f'{player}/Hair/Hair001/SK_Player_Hair001.uasset ', f'{player}/Hair/Hair001/SK_Player_Hair001_Physics.uasset']),
            encoding='utf-8')
        run = self.root / 'run 1'
        process = subprocess.run([sys.executable, '-B', str(script), str(run), str(listing)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('heads 2 hairs 2', process.stdout)
        cfg = json.loads((run / 'ue_config.json').read_text(encoding='utf-8'))
        game = '/Game/Pal/Model/Character/Player'
        self.assertEqual(cfg['head_paths'], [f'{game}/Head/Head002/SK_Player_Female_Head002', f'{game}/Head/Head010/SK_Player_Female_Head010'])
        self.assertEqual(cfg['hair_paths'], [f'{game}/Hair/Hair001/SK_Player_Hair001', f'{game}/Hair/Hair003/SK_Player_Hair003'])
        self.assertEqual(cfg['hidden_material'], 'MI_Karin_Skin')
        for name, rgba in (('T_Karin_FlatN', (128, 128, 255, 255)), ('T_Karin_Black', (0, 0, 0, 255)),
                           ('T_Karin_SkinM', (0, 102, 255, 255)), ('T_Karin_SkinSSS', (176, 97, 79, 255))):
            spec = cfg['textures'][name]
            with Image.open(run / 'textures' / spec['file']) as im:
                self.assertEqual((im.mode, im.size, im.getpixel((3, 3))), ('RGBA', (4, 4), rgba))
        self.assertEqual((cfg['textures']['T_Karin_FlatN']['normal'], cfg['textures']['T_Karin_SkinSSS']['srgb']), (True, True))
        self.assertEqual(cfg['textures']['T_Karin_Body'], {'file': 'Karin_Body.png', 'srgb': True, 'normal': False})
        mats = cfg['materials']
        self.assertEqual(sorted(mats), ['MI_Karin_Costume', 'MI_Karin_Face', 'MI_Karin_Hair', 'MI_Karin_Skin'])
        self.assertEqual((mats['MI_Karin_Skin']['parent'], mats['MI_Karin_Face']['textures']['Base Texture']),
                         ('/Game/Pal/Material/Character/Common/MI_PalLit_HumanSkin', 'T_Karin_Face'))
        self.assertTrue(all(t in cfg['textures'] for m in mats.values() for t in m['textures'].values()))
        sock = cfg['body_sockets'][0]
        self.assertEqual((sock['name'], sock['bone']), ('Socket_BackWeapon_R', 'spine_03'))
        self.assertAlmostEqual(sock['loc'][0], 8.96 * 0.85)
        bad = subprocess.run([sys.executable, '-B', str(script), str(run)], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)

    def test_pal_tools_environment_and_staging(self):
        import shutil
        tools = pal_kit() / 'tools'
        pwsh = shutil.which('pwsh')
        if not pwsh or sys.platform != 'win32':
            self.skipTest('needs PowerShell 7 (pwsh) on Windows')
        names = ('palx_run.ps1', 'cook_and_pack.ps1', 'verify_paks.ps1', 'run_py.ps1', 'build_plugin.ps1')
        env = {k: v for k, v in os.environ.items() if not k.startswith('PAL_')}

        def ps(script, *args, extra=None, ok=True):
            process = subprocess.run([pwsh, '-NoProfile', '-NonInteractive', '-File', str(script), *map(str, args)],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace',
                                     env=dict(env, **(extra or {})), timeout=120)
            if (process.returncode == 0) != ok:
                raise AssertionError(f'{script}: exit {process.returncode}\n{process.stdout}\n{process.stderr}')
            return process.stdout
        # every tool parses, and stops before doing anything when its machine paths are not given
        driver = self.root / 'driver.ps1'
        driver.write_text("$r = [ordered]@{}\nforeach ($f in $args) {\n  $e = $null; $t = $null\n"
                          "  [void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e)\n"
                          "  try { & $f *> $null; $m = 'ran' } catch { $m = \"$_\" }\n"
                          "  $r[(Split-Path $f -Leaf)] = @{ parse = $e.Count; error = $m } }\n$r | ConvertTo-Json -Compress\n",
                          encoding='utf-8')
        report = json.loads(ps(driver, *(tools / n for n in names)))
        for name, want in zip(names, ('PAL_GAME_DIR', 'PAL_WORK_ROOT', 'PAL_WORK_ROOT', 'PAL_UE_ROOT', 'PAL_UE_ROOT')):
            self.assertEqual(report[name]['parse'], 0, name)
            self.assertIn(want, report[name]['error'], name)
        # fake executables: PalExport echoes its arguments, repak lists the stage folder into the pak file
        echo, repak = self.root / 'echo.cmd', self.root / 'repak.cmd'
        echo.write_text('@echo off\r\necho ARGS %*\r\n', encoding='ascii')
        repak.write_text('@echo off\r\nif not "%~1"=="pack" exit /b 3\r\ndir /s /b /a-d "%~6" > "%~7"\r\n', encoding='ascii')
        work, game, project = self.root / 'work root', self.root / 'game dir', self.root / 'project'
        (work / 'tools').mkdir(parents=True)
        out = ps(tools / 'palx_run.ps1', 'ue', 'list', 'Player/', '-Exe', echo, extra={'PAL_WORK_ROOT': str(work), 'PAL_GAME_DIR': str(game)})
        self.assertIn(f'ARGS "{game}\\Pal\\Content\\Paks" "{work}\\tools\\Mappings.usmap" "{work}\\tools\\oo2core_9_win64.dll" '
                      f'"{work}\\extract\\ue" list Player/', out)
        out = ps(tools / 'verify_paks.ps1', 'r9', '-Exe', echo, '-Usmap', 'm.usmap', '-Oodle', 'o.dll', extra={'PAL_WORK_ROOT': str(work)})
        self.assertEqual(out.count(f'ARGS "{work}\\out\\r9" m.usmap o.dll "{work}\\extract\\verify_r9"'), 3)
        self.assertIn('VERIFY_DONE', out)
        cooked = project / 'Saved/Cooked/Windows/Pal/Content'
        content = {'Karin_Body_P': ['Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001.uasset',
                                    'Pal/Blueprint/Character/Player/Imp_Cloth/ABP_F_OldCloth001_Implimentation.uexp',
                                    'Mods/KarinPal/Textures/T_Karin_Body.uasset', 'Mods/KarinPal/Materials/MI_Karin_Skin.uasset'],
                   'Karin_Face_P': ['Pal/Model/Character/Player/Head/Head001/SK_Player_Female_Head001.uasset',
                                    'Pal/Model/Character/Player/Head/Head026/SK_Player_Female_Head026.ubulk'],
                   'Karin_HideHair_P': ['Pal/Model/Character/Player/Hair/Hair001/SK_Player_Hair001.uasset']}
        dummies = ['Pal/Model/Character/Skeleton/Human/SK_PalHuman_Skeleton.uasset',
                   'Pal/Blueprint/Character/Player/Female/ALI_HumanCloth.uasset',
                   'Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/MI_Other.uasset',
                   'Pal/Model/Character/Player/Head/Head001/SK_Player_Male_Head001.uasset']
        for rel in [r for v in content.values() for r in v] + dummies:
            (cooked / rel).parent.mkdir(parents=True, exist_ok=True)
            (cooked / rel).write_bytes(b'synthetic')
        ps(tools / 'cook_and_pack.ps1', '-SkipCook', '-Install', 't1', '-Repak', repak, extra={'PAL_WORK_ROOT': str(work), 'PAL_UE_ROOT': str(self.root / 'ue'),
           'PAL_PROJECT': str(project), 'PAL_GAME_DIR': str(game)})
        mods = game / 'Pal/Content/Paks/~mods'
        self.assertEqual(sorted(p.name for p in mods.iterdir()), sorted(f'{n}.pak' for n in content))
        for name, files in content.items():
            listed = (mods / f'{name}.pak').read_text(encoding='utf-8', errors='replace').splitlines()
            stage = work / 'stage' / 't1' / name
            self.assertEqual(sorted(listed), sorted(str(stage / 'Pal/Content' / f).replace('/', '\\') for f in files))
        ps(tools / 'cook_and_pack.ps1', '-SkipCook', '-Install', 't2', '-Repak', repak,
           extra={'PAL_WORK_ROOT': str(work), 'PAL_UE_ROOT': str(self.root / 'ue'), 'PAL_PROJECT': str(project)}, ok=False)
        self.assertFalse((work / 'out' / 't2').exists())                     # -Install without the game folder: refused first

    def test_pal_provenance_and_portability(self):
        import hashlib
        import re
        kit = pal_kit()
        rows = [r for r in json.loads((KITS / 'PROVENANCE.json').read_text(encoding='utf-8-sig'))
                if r['path'].startswith('portable-kits/palworld/')]
        files = sorted(p.relative_to(ROOT).as_posix() for p in kit.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        own = {'portable-kits/palworld/' + n for n in ('README.md', 'toolchain.json', 'requirements.txt')}
        self.assertEqual(sorted(r['path'] for r in rows), sorted(set(files) - own))
        for r in rows:
            data = (ROOT / r['path']).read_bytes()
            self.assertEqual((hashlib.sha256(data).hexdigest(), len(data)), (r['portable_sha256'], r['portable_bytes']), r['path'])
            self.assertTrue(r['source'].startswith('ModTools/Palworld/') or r['source'] == 'PalModding/tools/palx_run.ps1')
            self.assertEqual(r['modified_for_portability'], r['portable_sha256'] != r['original_sha256'], r['path'])
        bundled = json.loads((kit / 'toolchain.json').read_text(encoding='utf-8'))['bundled_scripts']
        self.assertEqual(sorted('portable-kits/palworld/' + s for s in bundled), sorted(r['path'] for r in rows))
        # no machine paths, LF only, and no third-party plugin source (KawaiiPhysics is obtained separately)
        drive = re.compile(r'(?i)(?<![\w<])[a-z]:[\\/](?![\\/])|[\\/]users[\\/]')
        for rel in files:
            data = (ROOT / rel).read_bytes()
            text = data.decode('utf-8')
            self.assertFalse(drive.search(text), f'{rel}: {drive.search(text)}')
            self.assertNotIn(b'\r', data, rel)
            self.assertNotIn('kawaiiphysics', Path(rel).name.lower())

SM2 = 'marvels-spider-man-2'
# Spider-Man 2 scripts whose import (and --help) needs only the standard library; the others also need numpy and Pillow.
# scipy, etcpak and ALERT's dat1lib are imported on first use, so no script needs them for --help.
SM2_STDLIB_SCRIPTS = {'sm2_common', 'sm2_dat1', 'crc64_table', 'sm2_stage', 'sm2_install', 'i30_build', 'i30_texture',
                      'i30_actor', 'i30_actor_edit', 'sm2_index', 'sm2_find', 'sm2_extract', 'suit_models',
                      'test_actor_roundtrip'}


def sm2_missing(script):
    """numpy / Pillow that a Spider-Man 2 script imports and that are not installed."""
    if script in SM2_STDLIB_SCRIPTS:
        return []
    return [m for m in ('numpy', 'PIL') if importlib.util.find_spec(m) is None]


def sm2_header(pairs, fill):
    """i30 asset header: u32 type, u8 0, u8 pairs, u16 extra (0), then 8 bytes per pair."""
    return struct.pack('<IBBH', 0x98906B9F, 0, pairs, 0) + bytes([fill]) * (8 * pairs)


def sm2_archive(name):
    return name.encode('ascii').ljust(40, b'\0') + struct.pack('<QQIHI', 1, 2, 3, 4, 5)


def sm2_toc(dat1, inst, path, spans, ids, sizes, archives, tex_ids, tex_meta, headers):
    """Minimal i30 toc in the layout sm2_install.TOC reads: u32 magic, u32 size, DAT1 with its eight sections."""
    d = dat1.DAT1(struct.pack('<IIIHH', dat1.MAGIC, 0x51B8E006, 16, 0, 0))
    for tag, data in ((inst.T_SPANS, b''.join(struct.pack('<II', *s) for s in spans)),
                      (inst.T_IDS, struct.pack(f'<{len(ids)}Q', *ids)),
                      (inst.T_SIZES, b''.join(struct.pack('<IIIi', *s) for s in sizes)),
                      (inst.T_ARCH, b''.join(archives)),
                      (inst.T_TEXIDS, struct.pack(f'<{len(tex_ids)}Q', *tex_ids)),
                      (inst.T_TEXMETA, b''.join(tex_meta)),
                      (inst.T_TEXHDR, struct.pack('<I', len(tex_ids))),
                      (inst.T_HDRS, headers)):
        d.set(tag, data)
    body = d.save()
    data = struct.pack('<II', inst.TOC_MAGIC, len(body)) + body
    Path(path).write_bytes(data)
    return data


class MarvelsSpiderMan2Tools(unittest.TestCase):
    """.stage format, the release installer and the .actor object codec on synthetic data. Index, extraction, fitting,
    the batch / carrier builders and the offline readbacks need the game, ALERT's dat1lib and the source VRM."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding sm2 ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_sm2_stage_roundtrip_and_asset_ids(self):
        import zipfile
        st = module(SM2, 'sm2_stage')
        table = module(SM2, 'crc64_table').TABLE

        def reference(path):     # bitwise reflected CRC-64/ECMA-182, init = polynomial, no final xor; id = crc >> 2 | 1 << 63
            p = path.lower().replace('\\', '/')
            while '//' in p:
                p = p.replace('//', '/')
            crc = poly = 0xC96C5795D7870F42
            for b in p.encode('utf-8'):
                crc ^= b
                for _ in range(8):
                    crc = (crc >> 1) ^ (poly if crc & 1 else 0)
            return (crc >> 2) | 1 << 63
        self.assertEqual(table[1], 0xB32E4CBE03A75F6F)
        for path in ('a', 'configs/inventory/x.config', 'Characters\\Hero\\X.model', 'ü/ß.texture'):
            self.assertEqual(st.crc64_path(path), reference(path), path)
        # asset ids of the default Peter / Miles suits as listed by the game's toc
        peter = 'characters/hero/hero_spiderman_advanced/hero_spiderman_advanced.model'
        self.assertEqual(st.crc64_path(peter), 0xA6D53AE572ACCADC)
        self.assertEqual(st.crc64_path('characters/hero/hero_spiderman_miles_updated/hero_spiderman_miles_updated.model'),
                         0x841353C2023080D8)
        self.assertEqual(st.crc64_path('Characters\\Hero\\hero_spiderman_advanced//HERO_SPIDERMAN_ADVANCED.model'),
                         0xA6D53AE572ACCADC)
        # write -> read keeps order, spans, ids, headers, texture meta and payloads
        header, meta = sm2_header(2, 0x11)[:-3], bytes(range(72))      # 21 bytes: padding after it is exercised
        tex = st.crc64_path('characters/hero/x/textures/x_c.texture')
        assets = [(0, 0x8000000000000001, b'raw payload', None, None), (0, st.crc64_path(peter), b'model' * 9, header, None),
                  (1, tex, b'hd mips', None, None), (0, tex, b'sd mips', header, meta), (0, 0x8000000000000002, b'm', None, meta)]
        stage = self.root / 'synthetic mod.stage'
        st.write_stage(stage, assets, 'Synthetic', '', 'two spans')
        info, back = st.read_stage(stage)
        self.assertEqual(info, {'game': 'MSM2', 'format_version': 2, 'name': 'Synthetic', 'author': '',
                                'description': 'two spans'})
        self.assertEqual(back, [(s, a, h, t, d) for s, a, d, h, t in assets])
        with zipfile.ZipFile(stage) as z:
            names = z.namelist()
            self.assertEqual(names, ['info.json', '0/8000000000000001', '0/A6D53AE572ACCADC', f'1/{tex:016X}',
                                     f'0/{tex:016X}', '0/8000000000000002'])
            self.assertEqual(z.read(names[1]), b'raw payload')                 # no header / meta: stored as is
            blob = z.read(names[4])                                             # STG wrapper, header + meta
            self.assertEqual(struct.unpack_from('<4I', blob), (st.STG_MAGIC, 3, 21, 72))
            self.assertEqual((blob[16:37], blob[48:120], blob[128:]), (header, meta, b'sd mips'))
            blob = z.read(names[5])                                             # meta only
            self.assertEqual(struct.unpack_from('<4I', blob), (st.STG_MAGIC, 2, 0, 72))
            self.assertEqual((blob[16:88], blob[96:]), (meta, b'm'))
        self.assertEqual(st.stg_unwrap(b'STG'), (None, None, b'STG'))
        # entries may also be named by asset path; folders that are not span numbers are ignored
        other = self.root / 'paths.stage'
        with zipfile.ZipFile(other, 'w') as z:
            z.writestr('info.json', '{"name": "p"}')
            z.writestr('0/', b'')
            z.writestr('0/' + peter, b'by path')
            z.writestr('2\\' + peter.upper(), st.stg_wrap(b'x', header=header))
            z.writestr('docs/readme.txt', b'ignored')
        self.assertEqual(st.read_stage(other), ({'name': 'p'}, [(0, 0xA6D53AE572ACCADC, None, None, b'by path'),
                                                               (2, 0xA6D53AE572ACCADC, header, None, b'x')]))

    def test_sm2_install_status_uninstall(self):
        import warnings
        quiet = warnings.catch_warnings()
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)
        warnings.simplefilter('ignore', ResourceWarning)                      # the installer reads files with open().read()
        st, dat1, inst = module(SM2, 'sm2_stage'), module(SM2, 'sm2_dat1'), module(SM2, 'sm2_install')
        game = self.root / 'game dir'
        (game / 'd' / 'mods').mkdir(parents=True)
        (game / 'd' / 'mods' / 'mod7').write_bytes(b'stale')                   # left by an older install: removed
        a05, a10, a15, a20, a30 = (1 << 63 | k for k in (5, 10, 15, 20, 30))
        meta = lambda k: bytes([k]) * 72
        orig = sm2_toc(dat1, inst, game / 'toc', spans=[(0, 3), (3, 1)], ids=[a10, a20, a30, a20],
                       sizes=[(100, 0, 0, 0), (200, 0, 100, 16), (300, 1, 0, -1), (400, 1, 300, -1)],
                       archives=[sm2_archive('g\\a0'), sm2_archive('g\\a1')], tex_ids=[a20], tex_meta=[meta(1)],
                       headers=sm2_header(1, 0xA1) + sm2_header(1, 0xA2))
        inst.TOC(game / 'toc').save(self.root / 'resaved')                      # an untouched toc saves back byte for byte
        self.assertEqual((self.root / 'resaved').read_bytes(), orig)
        # a20: same-length header (in place) and new texture meta; a15: new, 2-pair header and meta; a05: new in span 1;
        # a10: longer header (appended, the old bytes stay)
        A, B, C, D = b'A' * 5, b'B' * 7, b'C' * 3, b'D' * 11
        one = self.root / 'one.stage'
        st.write_stage(one, [(0, a20, A, sm2_header(1, 0xB1), meta(2)), (0, a15, B, sm2_header(2, 0xB2), meta(3)),
                             (1, a05, C, None, None), (0, a10, D, sm2_header(2, 0xB4), None)], 'one', '')
        log = []
        report = inst.install(str(game), [str(one)], log.append)
        self.assertEqual([(r['mod'], r['span'], r['id'], r['size'], r['added'], r['header'], r['texmeta']) for r in report],
                         [(0, 0, f'{a20:016X}', 5, False, True, True), (0, 0, f'{a15:016X}', 7, True, True, True),
                          (0, 1, f'{a05:016X}', 3, True, False, False), (0, 0, f'{a10:016X}', 11, False, True, False)])
        self.assertTrue(any('created toc.BAK' in x for x in log))
        self.assertEqual((game / 'toc.BAK').read_bytes(), orig)
        self.assertEqual(sorted(p.name for p in (game / 'd' / 'mods').iterdir()), ['mod0'])
        self.assertEqual((game / 'd' / 'mods' / 'mod0').read_bytes(), A + B + C + D)
        t = inst.TOC(game / 'toc')
        self.assertEqual((t.spans, t.ids), ([[0, 4], [4, 2]], [a10, a15, a20, a30, a05, a20]))
        self.assertEqual([t.archive_name(i) for i in range(len(t.archives))], ['g\\a0', 'g\\a1', 'd\\mods\\mod0'])
        self.assertEqual(t.sizes, [[11, 2, 15, 56], [7, 2, 5, 32], [5, 2, 0, 16], [300, 1, 0, -1], [3, 2, 12, -1],
                                   [400, 1, 300, -1]])
        self.assertEqual([t.get_header(i) for i in range(3)], [sm2_header(2, 0xB4), sm2_header(2, 0xB2), sm2_header(1, 0xB1)])
        self.assertEqual(bytes(t.headers[:16]), sm2_header(1, 0xA1))
        self.assertEqual((t.tex_ids, bytes(t.tex_meta)), ([a15, a20], meta(3) + meta(2)))
        first = (game / 'toc').read_bytes()
        out = cli(SM2, 'sm2_install', '--game', game, 'status').stdout
        self.assertIn('archives 3', out)
        self.assertIn('mod0', out)
        self.assertIn('toc.BAK present', out)
        # two stages: mod0, mod1 in command-line order, the later one wins for the same asset; toc.BAK is kept
        two = self.root / 'two.stage'
        st.write_stage(two, [(0, a20, b'EE', None, None)], 'two', '')
        cli(SM2, 'sm2_install', '--game', game, 'install', one, two, '--report', self.root / 'report.json')
        t = inst.TOC(game / 'toc')
        self.assertEqual([t.archive_name(i) for i in (2, 3)], ['d\\mods\\mod0', 'd\\mods\\mod1'])
        self.assertEqual(t.sizes[t.ids.index(a20)], [2, 3, 0, 16])
        self.assertEqual([r['mod'] for r in json.loads((self.root / 'report.json').read_text())], [0, 0, 0, 0, 1])
        self.assertEqual((game / 'toc.BAK').read_bytes(), orig)
        # every install starts again from toc.BAK
        cli(SM2, 'sm2_install', '--game', game, 'install', one)
        self.assertEqual((game / 'toc').read_bytes(), first)
        self.assertEqual(sorted(p.name for p in (game / 'd' / 'mods').iterdir()), ['mod0'])
        cli(SM2, 'sm2_install', '--game', game, 'uninstall')
        self.assertEqual((game / 'toc').read_bytes(), orig)
        self.assertEqual(list((game / 'd' / 'mods').iterdir()), [])

    def test_sm2_actor_object_roundtrip(self):
        A = module(SM2, 'i30_actor')
        names = ['Transform', 'Light', 'Enabled', 'Count', 'Scale', 'Offset', 'Id', 'Model', 'Tags', 'Empty', 'Child',
                 'Nothing', 'Small', 'Signed']
        str_base = 16 + 12 * 2                                                  # two sections, no unknowns
        strings, offs = b'', {}
        for n in names:
            offs[n] = str_base + len(strings)
            strings += n.encode() + b'\0'

        def field(name, t, value):
            flags = (len(value) << 4 | 1) if isinstance(value, list) else 1 << 4
            return A.Field(name, offs[name], zlib.crc32(name.encode()), flags, 0, t, value)
        child = A.Obj([field('Small', A.T_U8, 7), field('Signed', A.T_I16, -3)])
        obj = A.Obj([field('Enabled', A.T_BOOL, True), field('Count', A.T_U32, 0xDEADBEEF), field('Scale', A.T_F32, 1.5),
                     field('Offset', A.T_F32, [0.25, -2.0, 8.0]), field('Id', A.T_ID, 0x8000000000001234),
                     field('Model', A.T_STR, A.Str('characters/x/x.model', 0x1234, 0x8000000000005678)),
                     field('Tags', A.T_STR, [A.Str('ab', 1, 2), A.Str('', 0, 0)]), field('Empty', A.T_U16, []),
                     field('Child', A.T_OBJ, child), field('Nothing', A.T_NULL, None)])
        want = {'Enabled': True, 'Count': 0xDEADBEEF, 'Scale': 1.5, 'Offset': [0.25, -2.0, 8.0], 'Id': 0x8000000000001234,
                'Model': 'characters/x/x.model', 'Tags': ['ab', ''], 'Empty': [], 'Child': {'Small': 7, 'Signed': -3},
                'Nothing': None}
        w = A.Writer()
        w.obj(obj)
        blob = bytes(w.b)
        self.assertEqual(struct.unpack_from('<4I', blob), (0, A.MARK, 10, len(blob) - 16))
        self.assertEqual(len(blob) % 4, 0)
        self.assertEqual(blob.index(struct.pack('<I', 0xDEADBEEF)) % 2, 1)     # values are packed without alignment
        by_off = {v: k for k, v in offs.items()}
        back, end = A.Reader(blob, 0, by_off.__getitem__).obj(0)
        self.assertEqual((end, back.to_py()), (len(blob), want))
        self.assertEqual((back.field('Model').value.h32, back.field('Model').value.h64), (0x1234, 0x8000000000005678))
        w2 = A.Writer()
        w2.obj(back)
        self.assertEqual(bytes(w2.b), blob)
        with self.assertRaises(ValueError):
            A.Reader(blob[:4] + b'\0' * 4 + blob[8:], 0, by_off.__getitem__).obj(0)
        # actor container: header, DAT1, strings block, ActorPriusBuilt rows, 16-aligned component data
        actor = A.Actor.__new__(A.Actor)
        actor.hdr_a, actor.hdr_b, actor.trailer, actor.unknowns, actor.refs = 0x40000000, 0x1234, b'', b'', []
        actor.tags, actor.order = [A.SEC_PRIUS, A.SEC_PRIUS_DATA], [A.SEC_PRIUS, A.SEC_PRIUS_DATA]
        actor.str_base, actor.strings = str_base, strings
        actor.sec = {A.SEC_PRIUS: b'', A.SEC_PRIUS_DATA: b''}
        actor.components = [A.Component(0x1111, 'Transform', offs['Transform'], 0xAAAA, 0, 0, 0, 0xFFFFFFFF, obj=obj),
                            A.Component(0x2222, 'Light', offs['Light'], 0xBBBB, 0, 0, 0, 0xFFFFFFFF)]
        raw = actor.save()
        parsed = A.Actor(raw)
        self.assertEqual(struct.unpack_from('<IBBHI', raw), (A.ACTOR_TYPE, 0, 1, 0, 0x40000000 | (len(raw) - 16)))
        self.assertEqual([(c.id, c.name, c.size) for c in parsed.components],
                         [(0x1111, 'Transform', len(blob)), (0x2222, 'Light', 0)])
        self.assertEqual((parsed.components[0].raw, parsed.components[0].obj.to_py(), parsed.components[1].obj),
                         (blob, want, None))
        self.assertEqual(parsed.find_string('Model'), offs['Model'])
        self.assertEqual(parsed.save(), raw)
        self.assertEqual(parsed.save(reencode=False), raw)
        self.assertNotIn('dat1lib', sys.modules)                              # ALERT is imported only to hash new names


DG_KIT = KITS / 'days-gone'
# Days Gone scripts that need only the standard library; the others import numpy.
DG_STDLIB_SCRIPTS = {'paklist', 'pakextract', 'pakwrite', 'uhdr', 'upkg', 'retarget_imports', 'retarget_inplace',
                     'shader_skips', 'fix_root_pose', 'patch_looks', 'make_pak', 'dgpaths'}


def dg_missing(script=None):
    """numpy, when a Days Gone script needs it and it is not installed"""
    if script in DG_STDLIB_SCRIPTS:
        return []
    return [m for m in ('numpy',) if importlib.util.find_spec(m) is None]


def dg_kit():
    if not DG_KIT.is_dir():
        raise unittest.SkipTest('days-gone is not included in this single-game export')
    return DG_KIT


def dg(name):
    dg_kit()
    if dg_missing(name):
        raise unittest.SkipTest('pip install -r portable-kits/days-gone/requirements.txt (missing numpy)')
    return module('days-gone', name)


def dg_run(name, *args, env=None, ok=True):
    """Run a Days Gone kit script with none of the caller's DG_* variables (plus env)"""
    path = dg_kit() / 'scripts' / f'{name}.py'
    full = {k: v for k, v in os.environ.items() if not k.startswith('DG_')}
    full.update(env or {}, PYTHONIOENCODING='utf-8')
    process = subprocess.run([sys.executable, '-B', str(path), *map(str, args)], capture_output=True, text=True,
                             encoding='utf-8', env=full, timeout=120)
    if (process.returncode == 0) != ok:
        raise AssertionError(f'{name}: exit {process.returncode}\n{process.stdout}\n{process.stderr}')
    return process


def dg_fstr(s):
    b = s.encode('ascii') + b'\0'
    return struct.pack('<i', len(b)) + b


def dg_package(names, imports, exports, ver=500, licensee=34):
    """Minimal cooked UE4 package in the layout upkg.Package reads: summary, name table (with the 4-byte hash pairs of
    Bend's version 500 / licensee 34 packages), imports, exports, empty depends map, asset registry count, export data.
    imports: (class package, class name, outer, object name); exports: (class index, outer, name, data)."""
    ix = {n: i for i, n in enumerate(names)}
    hb = b'\0' * 4 if ver >= 504 or licensee >= 34 else b''
    def summary(total, name_off, imp_off, exp_off, dep_off, reg_off):
        return (struct.pack('<Iiiiii', 0x9E2A83C1, -6, 864, ver, licensee, 0) + struct.pack('<i', total)
                + dg_fstr('None') + struct.pack('<I', 0x80000000)
                + struct.pack('<8i', len(names), name_off, 0, 0, len(exports), exp_off, len(imports), imp_off)
                + struct.pack('<4i', dep_off, 0, reg_off, 0) + b'\x11' * 16
                + struct.pack('<3i', 1, len(exports), len(names)) + struct.pack('<HHHIi', 4, 11, 2, 0, 0) * 2
                + struct.pack('<IiIii', 0, 0, 0, 0, 0) + struct.pack('<iqii', reg_off, 0, 0, 0))
    name_blob = b''.join(dg_fstr(n) + hb for n in names)
    imp_blob = b''.join(struct.pack('<7i', ix[cp], 0, ix[cn], 0, outer, ix[n], 0) for cp, cn, outer, n in imports)
    name_off = len(summary(0, 0, 0, 0, 0, 0))
    imp_off = name_off + len(name_blob)
    exp_off = imp_off + len(imp_blob)
    dep_off = exp_off + 72 * len(exports)
    reg_off = dep_off + 4 * len(exports)
    total = off = reg_off + 4
    exp_blob = b''
    for cls, outer, name, data in exports:
        exp_blob += struct.pack('<iiiiiIii', cls, 0, outer, ix[name], 0, 0, len(data), off) + bytes(40)
        off += len(data)
    return (summary(total, name_off, imp_off, exp_off, dep_off, reg_off) + name_blob + imp_blob + exp_blob
            + bytes(4 * len(exports)) + bytes(4) + b''.join(e[3] for e in exports))


def dg_mesh(bones, extra_pose=None):
    """Synthetic cooked skeletal mesh: one export whose data holds the reference skeleton (bone infos, then local
    transforms quat xyzw / translation / scale) and, optionally, a second serialized copy of some transforms, then
    64 bytes of other data. bones: (name, parent, quat, translation)"""
    names = ['/Script/CoreUObject', '/Script/Engine', 'Package', 'Class', 'SkeletalMesh', 'Skeleton', 'None',
             '/Game/Karin/deacon_head_standard_Skeleton', 'deacon_head_standard_Skeleton', 'deacon_head_standard']
    names += [b[0] for b in bones]
    ix = {n: i for i, n in enumerate(names)}
    pose = b''.join(struct.pack('<10f', *q, *t, 1, 1, 1) for _, _, q, t in bones)
    data = (b'\0' * 8 + struct.pack('<i', len(bones)) + b''.join(struct.pack('<iii', ix[n], 0, p) for n, p, _, _ in bones)
            + struct.pack('<i', len(bones)) + pose + b'\0' * 8 + (extra_pose(pose) if extra_pose else b'') + b'\xcd' * 64)
    imports = [('/Script/CoreUObject', 'Package', 0, '/Script/Engine'), ('/Script/CoreUObject', 'Class', -1, 'SkeletalMesh'),
               ('/Script/CoreUObject', 'Package', 0, '/Game/Karin/deacon_head_standard_Skeleton'),
               ('/Script/Engine', 'Skeleton', -3, 'deacon_head_standard_Skeleton')]
    return dg_package(names, imports, [(-2, 0, 'deacon_head_standard', data)])


class DaysGoneTools(unittest.TestCase):
    """pak v3, package / reference skeleton, root pose, lid amplifier, vertex buffer, AnimDynamics spring and
    per-track anim tools, lid calibration and the PowerShell tools on synthetic data. The Blender scripts, the UE 4.11
    editor import / cook and DgExport (C#) need Blender, UE 4.11 or the game."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='modding days gone ')
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_dg_pak_v3_write_list_extract(self):
        import hashlib
        src = self.root / 'src'
        files = {'Characters/Deacon/parts/head/deacon_head_standard.uasset': bytes(range(256)) * 700,   # 3 zlib blocks
                 'Karin/Materials/Karin_Face.uasset': b'synthetic texture',
                 'Animation/Deacon/empty.uasset': b''}
        for rel, data in files.items():
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / rel).write_bytes(data)
        for flag in ('', '--store'):
            pak = self.root / f'out{flag} 1.pak'
            out = dg_run('pakwrite', src, pak, *([flag] if flag else [])).stdout
            self.assertIn('3 files, mount ../../../BendGame/Content/', out)
            blob = pak.read_bytes()
            magic, ver, io, size = struct.unpack_from('<IIqq', blob, len(blob) - 44)
            self.assertEqual((magic, ver, io + size + 44), (0x5A6F12E1, 3, len(blob)))
            self.assertEqual(blob[-20:], hashlib.sha1(blob[io:io + size]).digest())
            listing = dg_run('paklist', pak).stdout.splitlines()
            self.assertEqual(listing[1], 'mount ../../../BendGame/Content/ count 3')
            rows = [l.split() for l in listing[2:]]
            self.assertEqual([r[3] for r in rows], sorted(files))                  # stored in sorted path order
            for usz, sz, comp, name in rows:
                self.assertEqual(int(usz), len(files[name]))
                self.assertEqual(comp, 'c1' if not flag and files[name] else 'c0')
                if comp == 'c1' and int(usz) > 1000:
                    self.assertLess(int(sz), int(usz))
            dest = self.root / f'x{flag}'
            self.assertIn('ok 3', dg_run('pakextract', pak, dest).stdout)
            for rel, data in files.items():
                self.assertEqual((dest / rel).read_bytes(), data)
        mounted = self.root / 'mount.pak'
        dg_run('pakwrite', src, mounted, '--mount', '../../../Other/Content/')
        self.assertIn('mount ../../../Other/Content/ count 3', dg_run('paklist', mounted).stdout)
        dg_run('pakwrite', src, ok=False)

    def test_dg_package_refskel_retarget_and_root_pose(self):
        import contextlib, io
        upkg, refskel, R, fix = dg('upkg'), dg('refskel'), dg('retarget_imports'), dg('fix_root_pose')
        import numpy as np
        h = 0.70710677
        bones = [('Armature', -1, (0, 0, 0, 1), (0, 0, 0)), ('Align', 0, (h, 0, 0, -h), (0, 0, 0)),
                 ('Hips', 1, (0, 0, 0, 1), (0, -97.1, 1.5)), ('spine', 2, (0, 0.6, 0, 0.8), (0, 10, 0)),
                 ('face_1544', 3, (0, 0, 0, 1), (1, 2, 3))]
        src = self.root / 'mesh.uasset'
        src.write_bytes(dg_mesh(bones, extra_pose=lambda pose: pose[:80]))   # a second copy of [Armature, Align]
        pkg = upkg.Package(src.read_bytes())
        self.assertTrue(pkg.hashes)
        self.assertEqual(pkg.obj_path(-4), '/Game/Karin/deacon_head_standard_Skeleton.deacon_head_standard_Skeleton')
        self.assertEqual(pkg.ref(pkg.exports[0]['Class']), 'import:Class /Script/Engine.SkeletalMesh')
        rs = refskel.read(src)
        self.assertEqual((rs['names'], rs['parents']), ([b[0] for b in bones], [b[1] for b in bones]))
        rot_x = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])                  # Align: quat (h, 0, 0, -h)
        self.assertTrue(np.allclose(rs['component'][2][:3, :3], rot_x, atol=1e-6))
        self.assertTrue(np.allclose(rs['component'][2][:3, 3], rot_x @ (0, -97.1, 1.5), atol=1e-5))
        spine = rs['component'][3][:3, :3]
        self.assertTrue(np.allclose(spine, rot_x @ refskel.quat_mat(0, 0.6, 0, 0.8), atol=1e-6))
        # retarget the skeleton import: the package grows by the new names, export data and offsets follow
        R.retarget(pkg, '/Game/Karin/deacon_head_standard_Skeleton', '/Game/Characters/Deacon/deacon_master_Skeleton')
        moved = self.root / 'retargeted.uasset'
        moved.write_bytes(pkg.write())
        q = upkg.Package(moved.read_bytes())
        self.assertEqual(q.obj_path(-4), '/Game/Characters/Deacon/deacon_master_Skeleton.deacon_master_Skeleton')
        self.assertEqual(q.export_data(0), pkg.export_data(0))
        self.assertEqual(q.s['TotalHeaderSize'] - pkg.s['TotalHeaderSize'],
                         sum(len(dg_fstr(n)) + 4 for n in ('/Game/Characters/Deacon/deacon_master_Skeleton', 'deacon_master_Skeleton')))
        self.assertTrue(np.allclose(refskel.read(moved)['component'], rs['component']))
        with self.assertRaises(SystemExit):                                   # unknown import: refused
            R.retarget(upkg.Package(src.read_bytes()), '/Game/Nope', '/Game/Other')
        # root pose: Armature -90 deg about X, Align identity, in every serialized copy; component poses from Align
        # down unchanged (identity * R == R * identity), so the bind matrices stay valid
        fixed = self.root / 'fixed.uasset'
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            fix.main(str(moved), str(fixed))
        self.assertIn('patched 2 copies', printed.getvalue())
        rf = refskel.read(fixed)
        self.assertTrue(np.allclose(rf['local'][0][:3, :3], rot_x, atol=1e-6))
        self.assertTrue(np.allclose(rf['local'][1][:3, :3], np.eye(3), atol=1e-6))
        self.assertTrue(np.allclose(rf['component'][1:], rs['component'][1:], atol=1e-5))   # Align and below
        fp = upkg.Package(fixed.read_bytes())
        po = rf['pose_offset'] - fp.exports[0]['SerialOffset']
        self.assertEqual(fp.export_data(0)[-144:-64], fp.export_data(0)[po:po + 80])   # the second copy is patched too
        with self.assertRaises(SystemExit):                                   # no [Armature, Align] pair to patch
            fix.main(str(self._plain_mesh()), str(self.root / 'x.uasset'))

    def _plain_mesh(self):
        path = self.root / 'plain.uasset'
        path.write_bytes(dg_mesh([('Root', -1, (0, 0, 0, 1), (0, 0, 5)), ('Head', 0, (0, 0, 0, 1), (0, 0, 150))]))
        return path

    def test_dg_blink_amp_lid_rest_pose(self):
        amp, refskel = dg('blink_amp'), dg('refskel')
        import numpy as np
        bones = [('Root', -1, (0, 0, 0, 1), (0, 0, 0)), ('Head', 0, (0, 0, 0.6, 0.8), (0, 2, 150)),
                 ('face_1544', 1, (0, 0, 0, 1), (3, 4, 5)), ('KB_Amp_L_Xn', 1, (0, 0, 0, 1), (2, 3, 4)),
                 ('KB_Blink_L_Xn', 3, (0, 0, 0, 1), (0.5, 0, 0))]
        src = self.root / 'mesh.uasset'
        src.write_bytes(dg_mesh(bones, extra_pose=lambda pose: pose))              # the whole pose array twice
        rig, cal = self.root / 'blink_rig.json', self.root / 'lid_calib.json'
        rig.write_text(json.dumps({'bones': {'KB_Blink_L_Xn': {'side': 'L', 'axis_head_local': [-1, 0, 0], 'magnitude': 1.2}}}))
        d_open, d_closed = np.array([0.17, -0.01, -0.14]), np.array([-0.61, -0.19, -0.01])
        cal.write_text(json.dumps({'face_1544': {'open': d_open.tolist(), 'closed': d_closed.tolist()}}))
        before = refskel.read(src)
        out = self.root / 'out.uasset'
        report = amp.main(str(src), str(out), str(rig), str(cal), str(self.root / 'report.json'))
        self.assertEqual(len(report['pose_copies']), 2)
        after = refskel.read(out)
        travel = d_open[0] - d_closed[0]
        L = after['local']
        S = np.linalg.norm(L[3][:3, :3], axis=0)                               # amplifier: R * diag(S)
        self.assertTrue(np.allclose(S, (1.2 / travel, amp.EPS, amp.EPS), atol=1e-5))
        self.assertTrue(np.allclose(L[3][:3, 0] / S[0], (1, 0, 0), atol=1e-6))    # Head X onto minus the lid axis (-X)
        self.assertTrue(np.allclose(L[4][:3, 3], np.array([3, 4, 5]) + d_open, atol=1e-5))
        self.assertTrue(np.allclose(after['component'][4][:3, 3], before['component'][4][:3, 3], atol=1e-4))   # lid rest
        for i in (0, 1, 2):
            self.assertTrue(np.allclose(after['local'][i], before['local'][i]))
        # closing the lid joint moves the lid bone by the magnitude along its axis (plus damped Y/Z motion)
        disp = np.array(report['bones']['KB_Blink_L_Xn']['closed_disp_head'])
        self.assertTrue(np.allclose(disp, (-1.2, 0, 0), atol=0.01))
        blob = out.read_bytes()
        first = after['pose_offset']
        self.assertEqual(blob[first:first + 200], blob[-264:-64])               # both copies carry the new pose
        self.assertEqual(json.loads((self.root / 'report.json').read_text())['verified_rest_positions'], True)

    def test_dg_skelmesh_normals_and_positions_in_place(self):
        N, P = dg('skelmesh_normals'), dg('skelmesh_positions')
        import numpy as np
        n = 1200
        k = np.arange(n)
        pos = np.c_[k % 12, (k // 12) % 10, k // 120].astype(np.float64) * 1.5 + 0.75   # no all-zero position
        uv = np.c_[(k % 37) / 37.0, (k % 41) / 41.0]
        v = np.zeros((n, 32), np.uint8)
        v[:, 0:4] = (255, 128, 128, 255)                                       # TangentX +X, W kept
        v[:, 4:8] = (128, 128, 255, 0)                                         # TangentZ +Z, W = binormal sign
        v[:, 8], v[:, 12] = 3, 255
        v[:, 16:28] = pos.astype('<f4').view(np.uint8).reshape(n, 12)
        v[:, 28:32] = uv.astype('<f2').view(np.uint8).reshape(n, 4)
        head = b'HEAD' * 8 + struct.pack('<6f', 1, 1, 1, 0, 0, 0) + struct.pack('<ii', 32, n)
        data = head + v.tobytes() + b'TAIL' * 4
        rng = np.random.default_rng(7)
        normal = rng.normal(size=(n, 3)) + (0, 0, 2.5)
        normal[7] = (0.3, 0.2, 0.9)
        normal /= np.linalg.norm(normal, axis=1)[:, None]
        cpos, cuv, cn = [pos], [uv], [normal]
        # vertex 5: a second corner at the same position with another UV; vertex 7: a back face (same position and
        # UV, opposite normal) that must not win over the side the old normal (+Z) is on
        cpos += [pos[[5]], pos[[7]]]; cuv += [uv[[5]] + 0.25, uv[[7]]]; cn += [[(1.0, 0, 0)], -normal[[7]]]
        corners = {'pos': np.vstack(cpos), 'uv': np.vstack(cuv), 'normal': np.vstack(cn)}
        out, rep = N.patch(data, corners)
        self.assertEqual((rep['buffer_offset'], rep['vertices'], rep['unmatched']), (len(head), n, 0))
        self.assertGreaterEqual(rep['two_sided_resolved'], 1)
        self.assertEqual(len(out), len(data))
        w = np.frombuffer(out, np.uint8, n * 32, len(head)).reshape(n, 32)
        z = w[:, 4:7] / 127.5 - 1
        x = w[:, 0:3] / 127.5 - 1
        self.assertTrue(np.allclose(z, normal, atol=0.01))
        self.assertLess(np.abs((x * normal).sum(1)).max(), 0.02)
        self.assertTrue((w[:, 3] == 255).all() and (w[:, 7] == 0).all())
        self.assertEqual(w[:, 8:].tobytes(), v[:, 8:].tobytes())
        self.assertEqual((out[:len(head)], out[-16:]), (head, b'TAIL' * 4))
        # vertex moves: matched by position, other float copies outside the buffer are counted, not touched
        sel = np.arange(10)
        tail = b''.join(struct.pack('<3f', *p) for p in pos[sel])
        moves = {'old': pos[sel], 'new': pos[sel] + (0, 0, -0.5)}
        out2, rep2 = P.patch(out + tail, corners['pos'], moves)
        self.assertEqual((rep2['moved_buffer_vertices'], rep2['moves_matched'], rep2['other_copies_of_50_sampled']), (10, 10, 10))
        w2 = np.frombuffer(out2, np.uint8, n * 32, len(head)).reshape(n, 32)
        p2 = w2[:, 16:28].copy().view('<f4').astype(np.float64)
        self.assertTrue(np.allclose(p2[sel], pos[sel] + (0, 0, -0.5)))
        self.assertTrue(np.array_equal(p2[10:], pos[10:]))
        self.assertEqual(w2[:, :16].tobytes(), w[:, :16].tobytes())
        self.assertEqual(out2[-len(tail):], tail)
        with self.assertRaises(ValueError):
            N.find_buffer(data, pos + 100.0)

    def test_dg_abp_springs_quaternions_springs_and_names(self):
        S, refskel, upkg = dg('abp_springs'), dg('refskel'), dg('upkg')
        import numpy as np
        rng = np.random.default_rng(3)
        mats = [np.eye(3), np.diag([1.0, -1, -1]), np.diag([-1.0, 1, -1]), np.diag([-1.0, -1, 1])]   # 180 deg turns
        for _ in range(20):
            qm, r = np.linalg.qr(rng.normal(size=(3, 3)))
            qm = qm @ np.diag(np.sign(np.diag(r)))
            mats.append(qm * np.linalg.det(qm))
        for m in mats:
            q = S.quat_from_matrix(m)
            self.assertAlmostEqual(float(np.linalg.norm(q)), 1.0, places=9)
            self.assertTrue(np.allclose(refskel.quat_mat(*q), m, atol=1e-9))
        # one spring node per chain bone: k = I_pivot * omega^2 (box mass 1), damping = 1 - exp(-drag)
        names = ['Root', 'Head', 'KO_Hair_tail_L', 'KO_Hair_tail_L_001', 'KO_Hair_tail_L_002']
        at = [(0, 0, 0), (0, 0, 150), (8, 3, 160), (9, 5, 150), (10, 6, 138)]
        comp = np.tile(np.eye(4), (5, 1, 1))
        comp[:, :3, 3] = at
        rs = {'names': names, 'parents': [-1, 0, 1, 2, 3], 'component': comp}
        self.assertEqual(S.chain_bones(rs, 'KO_Hair_tail_L'), [(2, 3), (3, 4)])
        cfg = {'groups': [{'name': 'twin', 'chains': ['KO_Hair_tail_L'], 'omega': [15, 13], 'drag': 12, 'limit': [5, 7],
                           'planes': [{'kind': 'radial', 'bone': 'Head', 'center': [0, -2], 'margin': 0.5}]}]}
        specs = S.node_specs(rs, cfg)
        self.assertEqual([s['bone'] for s in specs], ['KO_Hair_tail_L', 'KO_Hair_tail_L_001'])
        for k, s in enumerate(specs):
            a, b = np.array(at[k + 2], float), np.array(at[k + 3], float)
            L = np.linalg.norm(b - a); d = L / 2
            I = (L * L + 4) / 12 + d * d
            self.assertAlmostEqual(s['k'], I * (15, 13)[k] ** 2)
            self.assertAlmostEqual(s['damping'], 1 - np.exp(-12))
            self.assertEqual((s['limit'], s['box'], s['offset'], s['gravity']), ((5, 7)[k], [2.0, L, 2.0], [0.0, d, 0.0], 0.0))
            com = a + (b - a) / L * d
            (pl,) = s['planes']
            n = com - (0, -2, com[2]); n[2] = 0; n /= np.linalg.norm(n)
            self.assertEqual((pl['bone'], pl['clear']), ('Head', 0.5))
            self.assertTrue(np.allclose(refskel.quat_mat(*pl['quat'])[:, 2], n, atol=1e-9))   # plane normal = frame Z
            dist = np.linalg.norm((com - (0, -2, com[2]))[:2])
            self.assertTrue(np.allclose(pl['pos'], np.array((0, -2, com[2])) + n * (dist - 0.5) - at[1], atol=1e-9))
        # bone FNames: a trailing _<number> without leading zeros is the instance number
        stub = type('Names', (), {'names': ['None'], 'name_index': upkg.Package.name_index})()
        def fname(s):
            i, num = struct.unpack('<ii', S.fname(stub, s))
            return stub.names[i], num
        self.assertEqual([fname(s) for s in ('KO_Skirt_0', 'KO_Ribbon_hand_L_1', 'KO_Skirt_0_001', 'Head', 'face_1544')],
                         [('KO_Skirt', 1), ('KO_Ribbon_hand_L', 2), ('KO_Skirt_0_001', 0), ('Head', 0), ('face', 1545)])

    def test_dg_anim_pertrack_track_decoding(self):
        A = dg('anim_pertrack')
        import numpy as np
        def hdr(nkeys, flags, fmt): return struct.pack('<i', nkeys | flags << 24 | fmt << 28)
        # translation, Float96NoW, all components, 3 keys spread over 5 frames (no frame table)
        blob = hdr(3, 0, A.ACF_Float96NoW) + b''.join(struct.pack('<3f', *t) for t in ((0, 0, 0), (2, 4, -6), (4, 4, 0)))
        # translation, Float96NoW, only X and Z stored (component flags 1 | 4), one key = constant
        blob += hdr(1, 5, A.ACF_Float96NoW) + struct.pack('<2f', 1.5, -2.5)
        # rotation, IntervalFixed32NoW: min / range per component, packed 11-11-10 bit keys, frame table (flag 8)
        rot_at = len(blob)
        blob += hdr(2, 7 | 8, A.ACF_IntervalFixed32NoW) + struct.pack('<6f', 0, 1, 0, 1, 0, 0.6)
        blob += struct.pack('<2I', 1023 << 21 | 1023 << 10 | 511, 1023 << 21 | 1023 << 10 | 1022) + bytes([0, 3]) + bytes(2)
        # rotation, Fixed48NoW, one key
        f48_at = len(blob)
        blob += hdr(1, 0, A.ACF_Fixed48NoW) + struct.pack('<3H', 32767, 32767, 32767 + 16384) + bytes(2)
        t, o = A._track(blob, 0, 5, False)
        self.assertEqual(o, 40)
        self.assertTrue(np.allclose(t, [(0, 0, 0), (1, 2, -3), (2, 4, -6), (3, 4, -3), (4, 4, 0)]))
        t, o = A._track(blob, o, 5, False)
        self.assertEqual(o, rot_at)
        self.assertTrue(np.allclose(t, [(1.5, 0, -2.5)] * 5))
        self.assertEqual(A._sizes(A.ACF_IntervalFixed32NoW, 7, True), (4, 24))
        q, o = A._track(blob, o, 4, True)
        self.assertEqual(o, f48_at)
        z = float(np.float32(0.6))
        mid = np.array([0, 0, z / 3, 1 + (np.sqrt(1 - z * z) - 1) / 3])
        self.assertTrue(np.allclose(q[0], (0, 0, 0, 1)) and np.allclose(q[3], (0, 0, z, np.sqrt(1 - z * z))))
        self.assertTrue(np.allclose(q[1], mid / np.linalg.norm(mid)))
        q, o = A._track(blob, o, 3, True)
        self.assertEqual(o, len(blob))
        z = 16384 / 32767
        self.assertTrue(np.allclose(q, [(0, 0, z, np.sqrt(1 - z * z))] * 3, atol=1e-6))

    def test_dg_lid_calib_and_machine_paths(self):
        from unittest import mock
        L, paths = dg('lid_calib'), dg('dgpaths')
        import numpy as np
        names = ['Root', 'Head', 'face_1544', 'face_1911']
        x = np.array([0.2, 0.18, -0.3, -0.6, -0.4, 0.17, 0.19])
        neutral = {'tracks': [{'bone_index': 2, 't': np.c_[x + 1, np.linspace(0, 0.6, 7) + 2, np.full(7, 3.0)]},
                              {'bone_index': 3, 't': np.c_[x[::-1] + 5, np.full(7, 1.0), np.linspace(-1, 1, 7)]}]}
        ref = {'tracks': [{'bone_index': 2, 't': np.array([[1.0, 2, 3], [9, 9, 9]])},
                          {'bone_index': 3, 't': np.array([[5.0, 1, 0], [9, 9, 9]])}]}
        out = L.calib(names, neutral, ref)
        self.assertTrue(np.allclose(out['face_1544']['open'], (0.17, 0.3, 0)))    # per-axis median over the frames
        self.assertTrue(np.allclose(out['face_1544']['closed'], (-0.6, 0.3, 0)))  # the frame lowest along X
        self.assertTrue(np.allclose(out['face_1911']['open'], (0.17, 0, 0)))
        self.assertTrue(np.allclose(out['face_1911']['closed'], (-0.6, 0, 0)))
        # command line: inputs under --cache in the DgExport / raw layout, output JSON with indent 1
        cache = self.root / 'cache dir'
        cache.mkdir()
        (cache / paths.SKEL_JSON).write_text(json.dumps({'bones': [{'name': n} for n in names]}), encoding='utf-8')
        seen = []
        def decode(path):
            seen.append(Path(path))
            return neutral if 'dcn_face_neutral' in str(path) else ref
        target = self.root / 'lid_calib.json'
        with mock.patch.object(L.A, 'decode', decode), mock.patch('sys.stdout', new=__import__('io').StringIO()):
            L.main(['--cache', str(cache), '--out', str(target)])
            L.main(['--cache', str(cache), '--out', str(self.root / 'right.json'), '--joints', 'face_1911'])
        base = cache.joinpath(*paths.ANIM_DIR)
        self.assertEqual(seen[:2], [base / 'facial/FaceMoods/dcn_face_neutral.uasset', base / 'misc/dcn_ref_pose.uasset'])
        self.assertEqual(json.loads(target.read_text()), out)
        self.assertTrue(target.read_text().startswith('{\n "face_1544": {\n  "open": [\n   0.1'))   # indent 1
        self.assertEqual(list(json.loads((self.root / 'right.json').read_text())), ['face_1911'])
        # machine paths come only from DG_CACHE / DG_MODELS_DIR; without them the scripts stop and name the variable
        clean = {k: v for k, v in os.environ.items() if not k.startswith('DG_')}
        with mock.patch.dict(os.environ, clean, clear=True):
            for call, var in ((paths.skel_json, 'DG_CACHE'), (paths.looks_dir, 'DG_CACHE'), (paths.karin_vrm, 'DG_MODELS_DIR')):
                with self.assertRaises(SystemExit) as stop:
                    call()
                self.assertIn(var, str(stop.exception))
        with mock.patch.dict(os.environ, dict(clean, DG_CACHE=str(cache), DG_MODELS_DIR=str(self.root))):
            self.assertEqual(paths.head_uemodel(), str(cache.joinpath(*paths.HEAD_UEMODEL)))
            self.assertEqual(paths.raw_content(), str(cache / 'raw' / 'BendGame' / 'Content'))
            self.assertEqual(paths.karin_vrm(), str(self.root / 'Karin_Original' / 'Karin(Clone).vrm'))
        self.assertIn('DG_CACHE', dg_run('lid_calib', '--out', self.root / 'x.json', ok=False).stderr)
        stage = self.root / 'stage'
        err = dg_run('make_pak', self.root / 'cooked', self.root / 'zz.pak', '--stage', stage, ok=False).stderr
        self.assertIn('DG_CACHE', err)
        self.assertFalse(stage.exists() or (self.root / 'zz.pak').exists())     # refused before anything is written

    def test_dg_tools_environment_and_install(self):
        import hashlib
        import shutil
        tools = dg_kit() / 'tools'
        pwsh = shutil.which('pwsh')
        if not pwsh or sys.platform != 'win32':
            self.skipTest('needs PowerShell 7 (pwsh) on Windows')
        env = {k: v for k, v in os.environ.items() if not k.startswith('DG_')}

        def ps(script, *args, extra=None, ok=True):
            process = subprocess.run([pwsh, '-NoProfile', '-NonInteractive', '-File', str(script), *map(str, args)],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace',
                                     env=dict(env, **(extra or {})), timeout=120)
            if (process.returncode == 0) != ok:
                raise AssertionError(f'{script}: exit {process.returncode}\n{process.stdout}\n{process.stderr}')
            return process.stdout
        # every tool parses; the ones that touch the machine stop first when their paths are not given
        # (set_resolution.ps1 is only parsed: running it would change this machine's display mode)
        driver = self.root / 'driver.ps1'
        driver.write_text("param([string]$Dir)\n$r = [ordered]@{}\n"
                          "foreach ($f in Get-ChildItem -LiteralPath $Dir -Filter *.ps1) { $e = $null; $t = $null\n"
                          "  [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$t, [ref]$e)\n"
                          "  $r[$f.Name] = @{ parse = $e.Count; error = 'not run' } }\n"
                          "function Run($name, [object[]]$a) { try { & (Join-Path $Dir $name) @a *> $null; $r[$name].error = 'ran' }"
                          " catch { $r[$name].error = \"$_\" } }\n"
                          "Run 'dgx_run.ps1' @('out', 'list'); Run 'cook.ps1' @('log'); Run 'ue_editor.ps1' @()\n"
                          "Run 'install_pak.ps1' @('00'); Run 'watch_launch.ps1' @()\n$r | ConvertTo-Json -Compress\n",
                          encoding='utf-8')
        report = json.loads(ps(driver, tools))
        self.assertEqual(sorted(report), sorted(p.name for p in tools.glob('*.ps1')))
        want = {'dgx_run.ps1': 'DG_GAME_DIR', 'cook.ps1': 'DG_WORK_ROOT', 'ue_editor.ps1': 'DG_UE_ROOT',
                'install_pak.ps1': 'DG_WORK_ROOT', 'watch_launch.ps1': 'DG_WORK_ROOT', 'set_resolution.ps1': 'not run'}
        for name, value in report.items():
            self.assertEqual(value['parse'], 0, name)
            self.assertIn(want[name], value['error'], name)
        # dgx_run.ps1: DgExport gets the game's pak folder, <work>\out\<sub>, the command and its arguments
        work, game = self.root / 'work root', self.root / 'game dir'
        echo = self.root / 'echo.cmd'
        echo.write_text('@echo off\r\necho ARGS %*\r\necho GC %DOTNET_gcServer%\r\n', encoding='ascii')
        out = ps(tools / 'dgx_run.ps1', 'raw', 'list', 'deacon_head', '-Exe', echo,
                 extra={'DG_WORK_ROOT': str(work), 'DG_GAME_DIR': str(game)})
        self.assertIn(f'ARGS "{game}\\BendGame\\Content\\Paks" "{work}\\out\\raw" list deacon_head', out)
        self.assertIn('GC 0', out)
        # install_pak.ps1: hash-checked move from staging into ~mods, the previous pak kept in disabled_mods
        staged, mods = work / 'staging' / 'zz_Karin_P.pak', game / 'BendGame' / 'Content' / 'Paks' / '~mods'
        staged.parent.mkdir(parents=True)
        mods.mkdir(parents=True)
        staged.write_bytes(b'new synthetic pak')
        (mods / 'zz_Karin_P.pak').write_bytes(b'old synthetic pak')
        sha = hashlib.sha256(b'new synthetic pak').hexdigest()
        paths = {'DG_WORK_ROOT': str(work), 'DG_GAME_DIR': str(game)}
        self.assertIn('staged pak hash mismatch', ps(tools / 'install_pak.ps1', '0' * 64, extra=paths, ok=False))
        self.assertEqual((mods / 'zz_Karin_P.pak').read_bytes(), b'old synthetic pak')
        self.assertTrue(staged.is_file())
        self.assertIn('installed ' + sha[:12].upper(), ps(tools / 'install_pak.ps1', sha.upper(), extra=paths))
        self.assertEqual((mods / 'zz_Karin_P.pak').read_bytes(), b'new synthetic pak')
        self.assertEqual((work / 'disabled_mods' / 'zz_Karin_P_prev.pak').read_bytes(), b'old synthetic pak')
        self.assertFalse(staged.exists())
        self.assertIn('no staged pak', ps(tools / 'install_pak.ps1', sha, extra=paths, ok=False))

    def test_dg_provenance_and_portability(self):
        import hashlib
        import re
        kit = dg_kit()
        rows = [r for r in json.loads((KITS / 'PROVENANCE.json').read_text(encoding='utf-8-sig'))
                if r['path'].startswith('portable-kits/days-gone/')]
        files = sorted(p.relative_to(ROOT).as_posix() for p in kit.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        own = {'portable-kits/days-gone/' + n for n in ('README.md', 'toolchain.json', 'requirements.txt')}
        self.assertEqual(sorted(r['path'] for r in rows), sorted(set(files) - own))
        sources = ('ModTools/DaysGone/pytools/', 'ModTools/DaysGone/src/DgExport/', 'ModTools/DaysGone/runs/t',
                   'Mods/DaysGone/Karin_Original_Deacon/Scripts/', 'DGModding/tools/')
        for r in rows:
            data = (ROOT / r['path']).read_bytes()
            self.assertEqual((hashlib.sha256(data).hexdigest(), len(data)), (r['portable_sha256'], r['portable_bytes']), r['path'])
            if r['original_sha256'] is None:
                self.assertTrue(r['source'].startswith('new file written for the portable kit'), r['path'])
                self.assertTrue(r['modified_for_portability'])
            else:
                self.assertTrue(r['source'].startswith(sources), r['source'])
                self.assertEqual(r['modified_for_portability'], r['portable_sha256'] != r['original_sha256'], r['path'])
        bundled = json.loads((kit / 'toolchain.json').read_text(encoding='utf-8'))['bundled_scripts']
        self.assertEqual(sorted('portable-kits/days-gone/' + s for s in bundled), sorted(r['path'] for r in rows))
        # no machine paths; one line-ending style per file (migrated files keep the original's); no sys.path entry is a
        # written-in path; the rejected PhysX / AnimDynamics-retarget tools are not bundled
        drive = re.compile(r'(?i)(?<![\w<])[a-z]:[\\/](?![\\/])|[\\/]users[\\/]')
        for rel in files:
            data = (ROOT / rel).read_bytes()
            text = data.decode('utf-8')
            self.assertFalse(drive.search(text), f'{rel}: {drive.search(text)}')
            self.assertIn(data.count(b'\r\n'), (0, data.count(b'\n')), rel)
            self.assertNotRegex(text, r'sys\.path\.insert\(0, *r?[\'"]', rel)
        for name in ('physchain_v1.py', 'physasset_edit.py', 'abp_dynamics.py'):
            self.assertFalse(list(kit.rglob(name)), name)

if __name__ == '__main__': unittest.main(verbosity=2)
