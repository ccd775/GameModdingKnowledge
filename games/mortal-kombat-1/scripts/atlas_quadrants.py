"""Losslessly combine four square RGBA pages; does NOT edit model UVs. Requires Pillow."""
import argparse
import json
from pathlib import Path
from PIL import Image
from mk1_checks import sha256


def merge(paths, destination):
    if len(paths) != 4:
        raise ValueError('Exactly four input pages required')
    destination = Path(destination).resolve()
    report_path = destination.with_suffix('.atlas.json')
    if destination.exists() or report_path.exists():
        raise ValueError('Output/report already exist')
    paths = [Path(p).resolve(strict=True) for p in paths]
    images = [Image.open(p).convert('RGBA') for p in paths]
    size = images[0].width
    if size < 1 or size & (size-1) or any(im.size != (size, size) for im in images):
        raise ValueError('Equal square power-of-two pages required')
    if size * 2 > 8192:
        raise ValueError('This helper supports output up to 8192; review larger requests separately')
    quadrants = [(0, 0), (1, 0), (0, 1), (1, 1)]
    atlas = Image.new('RGBA', (size*2, size*2), (0, 0, 0, 0))
    for im, (x, y) in zip(images, quadrants):
        atlas.paste(im, (x*size, (1-y)*size))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        atlas.save(stream, format='PNG')
    check = Image.open(destination).convert('RGBA')
    for im, (x, y) in zip(images, quadrants):
        assert check.crop((x*size, (1-y)*size, (x+1)*size, (2-y)*size)).tobytes() == im.tobytes()
    report = {'size': size*2, 'pixel_scale': 1, 'rgba_exact_before_cook': True,
              'uv_formula': '(old_uv + quadrant) / 2', 'output_sha256': sha256(destination),
              'pages': [{'name': p.name, 'sha256': sha256(p), 'uv_quadrant': list(q)} for p, q in zip(paths, quadrants)]}
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pages', nargs=4, type=Path, required=True, metavar=('BOTTOM_LEFT','BOTTOM_RIGHT','TOP_LEFT','TOP_RIGHT'))
    args = parser.parse_args()
    print(json.dumps(merge(args.pages, args.output), indent=2))
