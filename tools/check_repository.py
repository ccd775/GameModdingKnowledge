#!/usr/bin/env python3
"""Check documentation links, JSON, Python syntax, and public-file boundaries."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from markdown_it import MarkdownIt

MD = MarkdownIt('commonmark').enable('table')
ALLOWED = {'.md', '.json', '.py', '.ps1', '.txt', '.yml', '.yaml', '.toml', '.csv'}
ABSOLUTE = re.compile(r'(?i)\b[A-Z]:[\\/](?![\\/])|/(?:Users|home)/[^/\s]+')
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)')


def links(text):
    for token in MD.parse(text):
        for child in token.children or []:
            if child.type in ('link_open', 'image'):
                yield child.attrGet('href') or child.attrGet('src')


def check(root):
    root = Path(root).resolve()
    errors, checked = [], 0
    for file in sorted(root.rglob('*')):
        if not file.is_file() or '.git' in file.relative_to(root).parts:
            continue
        rel = file.relative_to(root).as_posix()
        checked += 1
        if file.name not in ('.gitignore', '.gitattributes') and file.suffix not in ALLOWED:
            errors.append(f'{rel}: disallowed file type')
            continue
        try:
            text = file.read_text(encoding='utf-8-sig')
            if '\x00' in text:
                errors.append(f'{rel}: binary content')
            # Source examples of path detection are not local machine identities.
            if file.suffix in ('.md', '.json', '.txt') and ABSOLUTE.search(text):
                errors.append(f'{rel}: absolute local path')
            if SECRET.search(text):
                errors.append(f'{rel}: possible credential')
            if file.suffix == '.json':
                obj = json.loads(text)
                if file.name == 'toolchain.json':
                    for name in obj.get('entry_documents', []):
                        if not (file.parent / name).is_file():
                            errors.append(f'{rel}: missing toolchain document {name}')
                if file.name == 'PROVENANCE.json':
                    for row in obj:
                        target = (root / row['path']).resolve()
                        if not target.is_relative_to(root) or not target.is_file():
                            errors.append(f"{rel}: missing migrated script {row['path']}")
                        elif hashlib.sha256(target.read_bytes()).hexdigest() != row['portable_sha256']:
                            errors.append(f"{rel}: script hash changed {row['path']}")
            if file.suffix == '.py':
                ast.parse(text)
            if file.suffix == '.md':
                for href in links(text):
                    target = urlsplit(href)
                    if target.scheme in ('http', 'https', 'mailto') or not target.path:
                        continue
                    if target.scheme:
                        errors.append(f'{rel}: nonportable scheme {target.scheme}')
                        continue
                    dest = (file.parent / unquote(target.path)).resolve()
                    if not dest.is_relative_to(root) or not dest.exists():
                        errors.append(f'{rel}: broken link {href}')
        except (UnicodeError, ValueError, SyntaxError) as error:
            errors.append(f'{rel}: {error}')
    return {'files_checked': checked, 'errors': errors, 'passed': not errors,
            'scope': 'Local file links (not heading anchors), public file types, JSON and Python syntax. No runtime claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = check(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
