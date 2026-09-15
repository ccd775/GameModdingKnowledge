"""Read-only inventory/diff and hash-locked render-index patch. Python 3.10+."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(directory):
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Expected directory')
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_file():
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError('Refusing file outside inventory root')
            result[p.relative_to(root).as_posix()] = {'bytes': p.stat().st_size, 'sha256': sha256(p)}
    return result


def compare(left, right, allowed):
    a, b = inventory(left), inventory(right)
    changed = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
    added, removed = sorted(b.keys() - a.keys()), sorted(a.keys() - b.keys())
    unexpected = sorted((set(changed) | set(added) | set(removed)) - set(allowed))
    return {'changed': changed, 'added': added, 'removed': removed,
            'unexpected': unexpected, 'passed': not unexpected}


def patch_indices(source, output, plan):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.exists() or source == output:
        raise ValueError('Output must be a new file distinct from source')
    if sha256(source) != plan['source_sha256'].lower():
        raise ValueError('Source hash mismatch')
    raw = source.read_bytes()
    result = bytearray(raw)
    ranges = []
    total = 0
    for item in plan['buffers']:
        offset, width, count = item['offset'], item['width'], item['count']
        if not all(type(x) is int for x in (offset, width, count)):
            raise ValueError('Integer offset/width/count required')
        if width not in (2, 4) or count <= 0 or count % 3 or offset < 9:
            raise ValueError('Invalid index buffer shape')
        end = offset + width * count
        if end > len(raw) or any(offset < b and end > a for a, b in ranges):
            raise ValueError('Out-of-bounds or overlapping buffers')
        if raw[offset-9:offset] != bytes([width]) + struct.pack('<II', width, count):
            raise ValueError('Not the audited MultiSize bulk header')
        data = raw[offset:end]
        if hashlib.sha256(data).hexdigest() != item['buffer_sha256'].lower():
            raise ValueError('Index buffer evidence hash mismatch')
        fmt = 'H' if width == 2 else 'I'
        values = struct.unpack('<' + str(count) + fmt, data)
        if max(values) >= item['vertex_count']:
            raise ValueError('Index outside declared vertex range')
        for i in range(0, count, 3):
            struct.pack_into('<3' + fmt, result, offset+i*width, values[i], values[i], values[i])
        ranges.append((offset, end))
        total += count // 3
    if not ranges:
        raise ValueError('Empty plan')
    cursor = 0
    for begin, end in sorted(ranges):
        assert raw[cursor:begin] == result[cursor:begin]
        cursor = end
    assert raw[cursor:] == result[cursor:]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(result)
    return {'source_sha256': sha256(source), 'output_sha256': sha256(output),
            'triangles_collapsed': total, 'other_bytes_identical': True,
            'scope': 'Audited buffers only; does not prove all LODs or runtime hiding'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory'); inv.add_argument('directory', type=Path)
    diff = sub.add_parser('diff'); diff.add_argument('before', type=Path); diff.add_argument('after', type=Path)
    diff.add_argument('--allow', action='append', default=[], help='Exact relative path allowed to differ')
    patch = sub.add_parser('hide-indices'); patch.add_argument('source', type=Path)
    patch.add_argument('output', type=Path); patch.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inventory': result = inventory(args.directory)
    elif args.command == 'diff': result = compare(args.before, args.after, args.allow)
    else: result = patch_indices(args.source, args.output, json.loads(args.plan.read_text(encoding='utf-8-sig')))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('passed') is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
