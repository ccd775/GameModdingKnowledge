#!/usr/bin/env python3
"""Export a self-contained per-game handoff tree without game assets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

from check_repository import check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'portable-kits/common'))
from modkit import GAMES, inventory, package


def export(game, destination):
    destination = Path(destination).resolve()
    if destination.is_relative_to(ROOT) or destination.exists():
        raise ValueError('Export requires a new directory outside the repository')
    destination.mkdir(parents=True)
    roots = [f'games/{game}', f'portable-kits/{game}', 'portable-kits/common', 'references', 'templates']
    for rel in roots:
        shutil.copytree(ROOT/rel, destination/rel, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for rel in ('PLAYBOOK.md','NOTICE.md','requirements.txt','SOURCE_REFERENCES.md','SOURCE_REFERENCES.json',
                'portable-kits/VALIDATION.md','tools/check_repository.py','tests/test_portable_tools.py'):
        (destination/rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/rel, destination/rel)
    provenance = json.loads((ROOT/'portable-kits/PROVENANCE.json').read_text(encoding='utf-8-sig'))
    filtered = [r for r in provenance if f'/{game}/' in r['path'] or '/common/' in r['path']]
    (destination/'portable-kits/PROVENANCE.json').write_text(json.dumps(filtered, indent=2)+'\n', encoding='utf-8')
    refs = json.loads((ROOT/'SOURCE_REFERENCES.json').read_text(encoding='utf-8'))
    refs = [r for r in refs if r['document'].startswith(f'games/{game}/')]
    (destination/'SOURCE_REFERENCES.json').write_text(json.dumps(refs, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (destination/'references/TOOLCHAIN_AND_SCRIPTS.md').write_text(
        f'# Selected Toolchain\n\n[Commands](../portable-kits/{game}/README.md)\n\n'
        '[Common tools](../portable-kits/common/README.md)\n\n[External tools](TOOL_SOURCES.md)\n', encoding='utf-8')
    readme = f'''# {game} Portable Playbook

先读 [使用命令](portable-kits/{game}/README.md) 和 [长线工作手册](PLAYBOOK.md)。
完整文档位于 [游戏知识](games/{game}/README.md)，公共操作见 [公共层](portable-kits/common/README.md)。
无需父仓库或 Skill 注册。Python 3.10+，用自己的 Python 环境安装 requirements.txt。

```powershell
python -m pip install -r requirements.txt
python -B portable-kits/common/modkit.py init ../MyMod --game {game}
python -B tools/check_repository.py
python -B tests/test_portable_tools.py
```

外部编译器/游戏/模型由目标机器提供。各脚本的 --help、适用格式和未验证分支在使用命令页。
'''
    (destination/'README.md').write_text(readme,encoding='utf-8')
    (destination/'AGENTS.md').write_text(f'# Entry\n\nRead README.md, PLAYBOOK.md, then games/{game}/README.md.\n',encoding='utf-8')
    (destination/'portable-kits/README.md').write_text(f'# Selected Kit\n\n[{game}]({game}/README.md)\n\n[Common](common/README.md)\n',encoding='utf-8')
    # The root source index mentions portable tools; it intentionally stays in the bundle.
    result = check(destination)
    if not result['passed']:
        raise ValueError(json.dumps(result['errors'], ensure_ascii=False))
    return {'game':game,'files':result['files_checked'],'directory':str(destination)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',choices=GAMES)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--zip',action='store_true',help='Also emit deterministic ZIP and member manifest beside each directory')
    args=parser.parse_args()
    if bool(args.game)==args.all: parser.error('Choose --game or --all')
    results=[]
    try:
        for game in GAMES if args.all else (args.game,):
            target=args.output/game if args.all else args.output
            result=export(game,target)
            if args.zip:
                manifest=target.with_name(target.name+'.files.json')
                inventory(target,manifest)
                result['zip']=package(target,manifest,target.with_name(target.name+'.zip'))
            results.append(result)
    except (OSError,ValueError) as error:
        parser.exit(1,f'Export failed; partial output retained for inspection: {error}\n')
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
