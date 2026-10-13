# frames_to_gif.py <dir> <tag> <out_prefix> [x0 y0 x1 y1] [cols]
# Assemble burst frames (tag_NNN.jpg + tag.txt timings) into <out_prefix>.gif and a labelled contact sheet
# <out_prefix>_sheet.jpg (every frame, optional crop). The frames come from tools/burst.ps1.
import argparse, glob, os
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(description="Burst frames (<tag>_NNN.jpg + <tag>.txt timings) -> <out_prefix>.gif and "
                                         "a labelled contact sheet <out_prefix>_sheet.jpg.")
ap.add_argument("dir", help="capture folder of burst.ps1")
ap.add_argument("tag", help="capture tag")
ap.add_argument("out_prefix", help="output path without extension")
ap.add_argument("crop_cols", nargs="*", type=int, metavar="N",
                help="optional crop box x0 y0 x1 y1 (pixels of the saved frames), then optional sheet columns (default 6)")
args = ap.parse_args()
d, tag, out = args.dir, args.tag, args.out_prefix
crop = tuple(args.crop_cols[:4]) if len(args.crop_cols) >= 4 else None
cols = args.crop_cols[4] if len(args.crop_cols) >= 5 else 6
files = sorted(glob.glob(os.path.join(d, tag + "_*.jpg")))
times = [float(x) for x in open(os.path.join(d, tag + ".txt")).read().split()]
frames = [Image.open(f).convert("RGB") for f in files]
if crop:
    frames = [f.crop(crop) for f in frames]
dur = [max(20, int(round(times[i + 1] - times[i]))) for i in range(len(times) - 1)] + [100]
frames[0].save(out + ".gif", save_all=True, append_images=frames[1:], duration=dur, loop=0)
w, h = frames[0].size
rows = (len(frames) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), "black")
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(frames):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(f, (x, y))
    dr.text((x + 4, y + 4), "%d  %.0fms" % (i, times[i] - times[0]), fill=(255, 255, 0))
sheet.save(out + "_sheet.jpg", quality=88)
print(len(frames), "frames", "avg dt %.1f ms" % ((times[-1] - times[0]) / max(1, len(times) - 1)), sheet.size)
