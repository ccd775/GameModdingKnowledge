"""Assemble the Full / Lite redeploy packages of the Karin_Original TotK mod (port of the project's assemble.sh).

Full = 00_Karin_Original + 01_Kalin_Base + 02_Visuals_UltraCam + the UltraCam settings (sdmc/UltraCam);
Lite = the same without 01_Kalin_Base. Each package folder gets install.bat / give_armor.bat (written here: the
repository carries no .bat files), README.md and tools/*.ps1 from the kit's release/ folder, and a ZIP beside it.

The related mods are the user's own installed mods (01_Kalin_Base, 02_Visuals_UltraCam) and UltraCam settings,
given as a ZIP or folder with load/01_Kalin_Base, load/02_Visuals_UltraCam and sdmc/UltraCam. Nothing is deleted:
--out must be a new folder.
"""
import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

TITLE = '0100F2C0115B6000'
MOD = '00_Karin_Original'
BAT = '@echo off\r\nchcp 65001 >nul\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\\{}" %*\r\npause\r\n'
BATS = {'install.bat': 'Install.ps1', 'give_armor.bat': 'Give-KarinArmor.ps1'}
RELEASE = Path(__file__).resolve().parents[1] / 'release'
RELATED = ('load/01_Kalin_Base', 'load/02_Visuals_UltraCam', 'sdmc/UltraCam')


def zip_folder(folder):
    """ZIP <folder>.zip with member names relative to the folder's parent (same layout as the project's zips)."""
    out = folder.with_name(folder.name + '.zip')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(p for p in folder.rglob('*') if p.is_file()):
            z.write(path, path.relative_to(folder.parent).as_posix())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mod', required=True, type=Path, help=f'built {MOD} folder (with romfs/ inside)')
    ap.add_argument('--related', required=True, type=Path, help='ZIP or folder with ' + ', '.join(RELATED))
    ap.add_argument('--version', required=True, help='package suffix, e.g. v7c')
    ap.add_argument('--out', required=True, type=Path, help='new folder for the package folders and ZIPs')
    ap.add_argument('--release', type=Path, default=RELEASE, help='README.md + tools/*.ps1 (default: the kit release/)')
    a = ap.parse_args()
    # check every input before anything is written
    if not (a.mod / 'romfs').is_dir():
        sys.exit(f'--mod has no romfs/: {a.mod}')
    for name in ['README.md'] + [f'tools/{ps1}' for ps1 in BATS.values()]:
        if not (a.release / name).is_file():
            sys.exit(f'--release is missing {name}: {a.release}')
    if a.related.is_file():
        with zipfile.ZipFile(a.related) as z:
            names = z.namelist()
        missing = [r for r in RELATED if not any(n.startswith(r + '/') for n in names)]
    elif a.related.is_dir():
        missing = [r for r in RELATED if not (a.related / r).is_dir()]
    else:
        sys.exit(f'--related not found: {a.related}')
    if missing:
        sys.exit(f'--related is missing {", ".join(missing)}')
    if a.out.exists():
        sys.exit(f'--out already exists (nothing is overwritten): {a.out}')
    a.out.mkdir(parents=True)
    related = a.related
    if related.is_file():
        related = a.out / 'related'
        with zipfile.ZipFile(a.related) as z:
            z.extractall(related)
    for edition in ('Full', 'Lite'):
        d = a.out / f'Karin_Original_{edition}_{a.version}'
        (d / 'load' / TITLE).mkdir(parents=True)
        (d / 'sdmc').mkdir()
        for bat, ps1 in BATS.items():
            (d / bat).write_bytes(BAT.format(ps1).encode('ascii'))
        shutil.copy2(a.release / 'README.md', d / 'README.md')
        shutil.copytree(a.release / 'tools', d / 'tools')
        shutil.copytree(a.mod, d / 'load' / TITLE / MOD)
        shutil.copytree(related / 'load/02_Visuals_UltraCam', d / 'load' / TITLE / '02_Visuals_UltraCam')
        if edition == 'Full':
            shutil.copytree(related / 'load/01_Kalin_Base', d / 'load' / TITLE / '01_Kalin_Base')
        shutil.copytree(related / 'sdmc/UltraCam', d / 'sdmc' / 'UltraCam')
        z = zip_folder(d)
        files = sum(1 for p in d.rglob('*') if p.is_file())
        print(f'{edition}: {files} files, {z.name} {os.path.getsize(z)} B')


if __name__ == '__main__':
    main()
