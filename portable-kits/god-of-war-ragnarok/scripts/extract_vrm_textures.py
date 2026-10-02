"""Dump the embedded images of a .vrm (glTF binary) as PNG files: python extract_vrm_textures.py <in.vrm> <out_dir>"""
import json, struct, io, os, sys, argparse
from PIL import Image

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('vrm', help='source .vrm (glTF binary)')
ap.add_argument('out_dir', help='folder for <image name>.png (created if missing)')
args = ap.parse_args()
src, out = args.vrm, args.out_dir
os.makedirs(out, exist_ok=True)
d = open(src, 'rb').read()
jl = struct.unpack_from('<I', d, 12)[0]
js = json.loads(d[20:20 + jl])
bin_off = 20 + jl + 8
for im in js['images']:
    bv = js['bufferViews'][im['bufferView']]
    o = bin_off + bv.get('byteOffset', 0)
    Image.open(io.BytesIO(d[o:o + bv['byteLength']])).save(os.path.join(out, im['name'] + '.png'))
    print(im['name'])
