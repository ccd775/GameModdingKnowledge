import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from mk1_checks import compare, patch_indices, sha256


class ToolsTests(unittest.TestCase):
    def test_diff_scope(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'a', Path(d)/'b'; a.mkdir(); b.mkdir()
            (a/'mesh').write_bytes(b'a'); (b/'mesh').write_bytes(b'b')
            self.assertFalse(compare(a,b,[])['passed'])
            self.assertTrue(compare(a,b,['mesh'])['passed'])
            (b/'unexpected').write_bytes(b'x')
            self.assertFalse(compare(a,b,['mesh'])['passed'])

    def test_patch_and_rejections(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = Path(d)/'source', Path(d)/'out'
            indices = struct.pack('<6H',0,1,2,2,3,0)
            p.write_bytes(b'PREFIX'+bytes([2])+struct.pack('<II',2,6)+indices+b'KEEP')
            row = {'offset':15,'width':2,'count':6,'vertex_count':4,'buffer_sha256':hashlib.sha256(indices).hexdigest()}
            plan = {'source_sha256':sha256(p),'buffers':[row]}
            result = patch_indices(p,out,plan)
            self.assertEqual(result['triangles_collapsed'],2)
            self.assertEqual(out.read_bytes()[15:27],struct.pack('<6H',0,0,0,2,2,2))
            self.assertEqual(p.read_bytes()[-4:],out.read_bytes()[-4:])
            with self.assertRaises(ValueError): patch_indices(p,out,plan)
            for invalid in [dict(plan,source_sha256='0'*64),dict(plan,buffers=[row,row]),dict(plan,buffers=[dict(row,offset=999)]),dict(plan,buffers=[dict(row,vertex_count=2)])]:
                with self.assertRaises(ValueError): patch_indices(p,Path(d)/'new',invalid)
                self.assertFalse((Path(d)/'new').exists())

    def test_atlas_orientation_alpha(self):
        from PIL import Image
        from atlas_quadrants import merge
        with tempfile.TemporaryDirectory() as d:
            paths=[]; colors=[(10,20,30,0),(40,50,60,80),(70,80,90,120),(100,110,120,255)]
            for i,color in enumerate(colors):
                p=Path(d)/f'{i}.png';Image.new('RGBA',(2,2),color).save(p);paths.append(p)
            out=Path(d)/'atlas.png';r=merge(paths,out);im=Image.open(out)
            self.assertEqual(r['size'],4)
            for xy,color in zip([(0,2),(2,2),(0,0),(2,0)],colors):self.assertEqual(im.getpixel(xy),color)
            with self.assertRaises(ValueError):merge(paths,out)


if __name__=='__main__':unittest.main()
