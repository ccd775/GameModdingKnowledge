#!/usr/bin/env python3
"""Portable project records and deterministic packages. Never launches a game."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
from datetime import datetime, timezone
import zipfile

GAMES = ('hitman-world-of-assassination', 'watch-dogs', 'assassins-creed-black-flag',
         'resident-evil-4-remake', 'left-4-dead-2', 'helldivers-2', 'mortal-kombat-1')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def relative_file(root, name):
    rel = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'Unsafe relative file name: {name}')
    path = (Path(root) / rel).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError(f'File escapes root: {name}')
    return path


def records(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Inventory root must be a directory')
    result, seen = [], set()
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symbolic links are not packaged: {path.name}')
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        relative_file(root, name)
        if name.casefold() in seen:
            raise ValueError(f'Case-insensitive path collision: {name}')
        seen.add(name.casefold())
        result.append({'path': name, 'size': path.stat().st_size, 'sha256': digest(path)})
    if not result:
        raise ValueError('Empty inventory is not an accepted package')
    return result


def verify(root, manifest):
    expected = read_json(manifest)
    if expected.get('schema') != 'modding-file-manifest/v2' or not expected.get('files'):
        raise ValueError('Expected nonempty modding-file-manifest/v2')
    for row in expected['files']:
        relative_file(root, row['path'])
    actual = records(root)
    if actual != expected['files']:
        raise ValueError('File set, byte size or SHA-256 differs from the manifest')
    return actual


def inventory(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError('Write the manifest outside the input tree')
    result = records(root)
    write_new(output, {'schema': 'modding-file-manifest/v2', 'files': result})
    return {'files': len(result), 'manifest': str(output)}


def initialize(project, game):
    if game not in GAMES:
        raise ValueError(f'Unknown game: {game}')
    project = Path(project).resolve()
    project.mkdir(parents=True, exist_ok=False)
    for name in ('Ref', 'Work/reports', 'Work/candidates', 'Output', 'reports/runtime', 'history'):
        (project / name).mkdir(parents=True, exist_ok=True)
    write_new(project / 'project.json', {
        'schema': 'modding-project/v1', 'game': game, 'build': None, 'target': None,
        'tools': {}, 'notes': 'Paths are local configuration. Set tool paths and SHA-256 after acquisition.'})
    write_new(project / 'source-lock.json', {'schema': 'modding-source-lock/v1', 'inputs': [], 'tools': []})
    (project / 'PROJECT_STATE.md').write_text(
        f'# Project State\n\nGame: {game}\n\n'
        '## Current Work\n\nTarget/build: not yet inventoried\n\n'
        'Current candidate: none\n\nNext action: inspect source, target and toolchain.\n\n'
        '## Session Handoff\n\nRecord completed work, open questions, evidence paths, '
        'rejected candidates, and the next useful command. Steps may be revisited.\n\n'
        '## Runtime\n\nNo runtime observations recorded.\n', encoding='utf-8')
    return {'project': str(project), 'game': game}


def checkpoint(project, milestone, status, note, reports):
    project = Path(project).resolve()
    read_json(project / 'project.json')
    if not milestone or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in milestone):
        raise ValueError('Use a lowercase alphanumeric milestone name')
    evidence = []
    for name in reports:
        path = relative_file(project, name)
        evidence.append({'path': name, 'size': path.stat().st_size, 'sha256': digest(path)})
    output = project / 'history' / f'{milestone}.json'
    write_new(output, {'schema': 'modding-milestone/v1', 'date': datetime.now(timezone.utc).isoformat(),
                      'milestone': milestone, 'status': status, 'note': note, 'evidence': evidence,
                      'interpretation': 'Status is recorded from the caller; this command does not infer acceptance.'})
    return {'checkpoint': str(output)}


def doctor(config):
    config_path = Path(config).resolve()
    value = read_json(config_path)
    observations = []
    for name, tool in value.get('tools', {}).items():
        path = Path(tool['path']).expanduser()
        if not path.is_absolute():
            path = config_path.parent / path
        found = path.is_file()
        actual = digest(path) if found else None
        expected = tool.get('sha256')
        observations.append({'tool': name, 'found': found, 'sha256': actual,
                             'pin_matches': bool(expected and actual == expected.lower())})
    return {'configured_tools': observations, 'all_configured_pins_match': bool(observations) and all(
        x['pin_matches'] for x in observations), 'scope': 'Files and pins only; format compatibility needs roundtrip.'}


def package(root, manifest, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root) or output == Path(manifest).resolve():
        raise ValueError('Package must be outside input tree and distinct from manifest')
    rows = verify(root, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_STORED) as archive:
        for row in rows:
            path = relative_file(root, row['path'])
            info = zipfile.ZipInfo(row['path'], (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            with path.open('rb') as source, archive.open(info, 'w', force_zip64=True) as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or archive.namelist() != [r['path'] for r in rows]:
            raise ValueError('ZIP readback failed')
        for row in rows:
            h = hashlib.sha256()
            with archive.open(row['path']) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != row['sha256']:
                raise ValueError(f"Input changed while packaging: {row['path']}; reject output")
    return {'package': str(output), 'sha256': digest(output), 'members': len(rows), 'runtime_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init'); p.add_argument('project'); p.add_argument('--game', choices=GAMES, required=True)
    p = sub.add_parser('inventory'); p.add_argument('root'); p.add_argument('--output', required=True)
    p = sub.add_parser('verify'); p.add_argument('root'); p.add_argument('--manifest', required=True)
    p = sub.add_parser('package'); p.add_argument('root'); p.add_argument('--manifest', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('doctor'); p.add_argument('config')
    p = sub.add_parser('checkpoint'); p.add_argument('project'); p.add_argument('milestone'); p.add_argument('--status', required=True)
    p.add_argument('--note', required=True); p.add_argument('--report', action='append', default=[])
    args = parser.parse_args()
    try:
        if args.cmd == 'init': result = initialize(args.project, args.game)
        elif args.cmd == 'inventory': result = inventory(args.root, args.output)
        elif args.cmd == 'verify': result = {'verified_files': len(verify(args.root, args.manifest))}
        elif args.cmd == 'doctor':
            result = doctor(args.config)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['all_configured_pins_match'] else 1
        elif args.cmd == 'checkpoint': result = checkpoint(args.project, args.milestone, args.status, args.note, args.report)
        else: result = package(args.root, args.manifest, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
