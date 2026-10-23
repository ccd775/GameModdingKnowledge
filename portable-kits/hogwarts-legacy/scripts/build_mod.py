#!/usr/bin/env python3
"""Karin -> Dark Arts outfit build (port of the project's build.sh). Stages run in the order given:
  fit       Blender fit (fit_<g>.json) -> <work>/fit_<g>/{fit.blend, skel_ext.json, dyn_chains.json}
  params    AnimDynamics node settings (<work>/dyn.json) -> <work>/fit_<g>/dyn_nodes.json
  export    FBX parts from fit.blend
  import    UE 4.27 import (meshes, Karin skeletons, anim blueprints; textures too with --textures)
  cook      UE cook (CookAll)
  assemble  per-gender legacy tree: cooked files, GA outfit DA, HL mesh patch (skel_ext ref pose), DA AnimClass,
            female MI clones
  pack      merge genders -> retoc to-zen -> <work>/mod_mf/out/zzz_KarinDarkArts_<MF|F>_P.* + KarinDarkArts.tar.xz
Paths come from options or HL_* variables (see --help); every setting the given stages need is checked first."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile

KIT = Path(__file__).resolve().parents[1]
SCRIPTS = KIT / 'scripts'
STAGES = ('fit', 'params', 'export', 'import', 'cook', 'assemble', 'pack')
ENV = {'work': 'HL_WORK', 'blender': 'HL_BLENDER', 'ue_cmd': 'HL_UE_CMD', 'project': 'HL_PROJECT', 'probe': 'HL_PROBE',
       'retoc': 'HL_RETOC'}
NEEDS = {'fit': ('blender',), 'params': (), 'export': ('blender',), 'import': ('ue_cmd', 'project'),
         'cook': ('ue_cmd', 'project'), 'assemble': ('project', 'probe'), 'pack': ('retoc',)}
TOOLS = ('blender', 'ue_cmd', 'probe', 'retoc')
HUM = 'Phoenix/Content/RiggedObjects/Characters/Human'
FEMALE = re.compile(r'_F/|/AVA_YF_|/Hair_F/')
F_HAIR = ('STUHair13/DA_HUM_F_Hair_StuHair13_Loose_LowBun_Master', 'STUHair18/DA_HUM_F_Hair_StuHair18_PrincessLong_Bangs1')
M_HAIR = 'StuHair03/DA_HUM_M_Hair_StuHair03_ShavedBob'
# The vanilla female outfit uses the male outfit's MIs. The female pieces get clones at unused _F paths that
# point at the Karin textures, so the male outfit (and its textures) stays vanilla.
MI_CLONES = ('Upper_M/Jacket_DarkArtsDeluxe01:HUM_M_Upp_DarkArtsDeluxe01', 'Lower_M/Pants_DarkArtsDeluxe01:HUM_M_Low_DarkArtsDeluxe01',
             'Accessory/Mask_M/DarkArtsDeluxe01:HUM_M_Mask_DarkArtsDeluxe01',
             'Accessory/Scarf_M/DarkArtsDeluxe01U:HUM_M_Acc_DarkArtsDeluxe01U', 'Hat_M/DarkArtsDeluxe01:HUM_M_Hat_DarkArtsDeluxe01')
FIT_KEEP = r'dynamic bones|^part |head morphs|normals carried|missing key|Traceback|Error'
IMPORT_KEEP = r'\[HLK\] (ALL|IMPORT|abp|karin|morphs)|LogHLK: (Error|Warning)|Error:'
PLACEHOLDER = re.compile(r'<[A-Z][A-Z0-9_]*>')


class Stop(Exception):
    pass


def quoted(cmd):
    if isinstance(cmd, str): return cmd
    return subprocess.list2cmdline(cmd) if os.name == 'nt' else shlex.join(cmd)


class Build:
    def __init__(self, args, cfg):
        self.dry = args.dry_run
        self.genders = cfg['genders']
        self.textures = args.textures
        self.work = Path(cfg['work']).resolve()
        self.blender, self.ue, self.probe, self.retoc = (cfg.get(k) for k in TOOLS)
        self.project = Path(cfg['project']).resolve() if cfg.get('project') else None
        self.pak = 'zzz_KarinDarkArts_%s_P' % ''.join(self.genders).upper()
        self.env = dict(os.environ, CUE4PARSE_SKIP_NATIVE='1', PYTHONIOENCODING='utf-8')

    def note(self, text):
        print('+ ' + text, flush=True)

    def run(self, cmd, keep=None, line=None, tail=None, quiet=False, cwd=None, env=None):
        """Print the tool's output lines that match keep (regex), rewritten by line(); with tail only the last ones,
        with quiet none (unless the tool fails). Returns the kept lines. Stops the build when the tool exits non-zero
        (build.sh ran under set -e without pipefail, so only its last pipe command could stop it)."""
        self.note(('(in %s) ' % cwd if cwd else '') + quoted(cmd))
        if self.dry: return []
        proc = subprocess.Popen(cmd, cwd=cwd, env=dict(self.env, **(env or {})), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        kept = []
        for raw in proc.stdout:
            s = raw.rstrip('\r\n')
            if keep and not re.search(keep, s): continue
            if line: s = line(s)
            if s is None: continue
            kept.append(s)
            if not (tail or quiet): print(s, flush=True)
        rc = proc.wait()
        for s in kept if quiet and rc else kept[-tail:] if tail and not quiet else ():
            print(s, flush=True)
        if rc: raise Stop('%s exited with %d' % (Path(cmd if isinstance(cmd, str) else cmd[0]).name, rc))
        return kept

    def py(self, script, *args, **kw):
        return self.run([sys.executable, '-B', str(SCRIPTS / script), *map(str, args)], **kw)

    def ue_cmd(self, *args, script=None, rest=()):
        uproject = str(self.project / 'Phoenix.uproject')
        if script is None: return [self.ue, uproject, *args, *rest]
        if os.name == 'nt':  # UE reads -script= up to the next space unless the value itself is quoted
            return '%s -script="%s" %s' % (subprocess.list2cmdline([self.ue, uproject, *args]), script, subprocess.list2cmdline(rest))
        return [self.ue, uproject, *args, '-script=' + str(script), *rest]

    # ------------------------------------------------------------------ stages
    def fit(self):
        for g in self.genders:
            self.run([self.blender, '-b', '--factory-startup', '--python', str(SCRIPTS / 'blender' / 'fit.py'), '--',
                      str(self.work / f'fit_{g}.json')], keep=FIT_KEEP, line=lambda s: s[:200])

    def params(self):
        for g in self.genders:
            fit = self.work / f'fit_{g}'
            self.py('dyn_params.py', fit, self.work / 'dyn.json', fit / 'dyn_nodes.json', tail=1)

    def export(self):
        for g in self.genders:
            fit = self.work / f'fit_{g}'
            self.run([self.blender, '-b', str(fit / 'fit.blend'), '--python', str(SCRIPTS / 'blender' / 'export_fbx.py'), '--',
                      str(fit), str(self.work / f'fit_{g}.json')], keep=r'^EXPORTED|Error')

    def import_(self):
        target = self.work / 'ue_build.json'
        for g in self.genders:
            self.note('write %s from ue_build_%s.json (textures %s)' % (target, g, 'kept' if self.textures else 'dropped'))
            if not self.dry:
                d = json.load(open(self.work / f'ue_build_{g}.json', encoding='utf-8'))
                d['textures'] = d['textures'] if self.textures else []
                with open(target, 'w') as f: json.dump(d, f, indent=1)
            cmd = self.ue_cmd('-run=pythonscript', script=SCRIPTS / 'ue' / 'ue_import.py',
                              rest=('-unattended', '-nop4', '-nosplash', '-NoSound', '-stdout', '-FullStdOutLogOutput'))
            self.run(cmd, keep=IMPORT_KEEP, cwd=self.project, env={'HL_UE_BUILD': str(target), 'HL_WORK': str(self.work)},
                     line=lambda s: None if 'LogInit: Display' in s else re.sub(r'.*\[HLK\]', '[HLK]', s, count=1)[:200])

    def cook(self):
        log = self.work / 'cook.log'
        cmd = self.ue_cmd('-run=cook', '-targetplatform=WindowsNoEditor', '-CookAll', '-unattended', '-nop4', '-nosplash', '-NoSound', '-stdout')
        self.note('(in %s) %s > %s' % (self.project, quoted(cmd), log))
        if self.dry: return
        with open(log, 'wb') as f:
            rc = subprocess.call(cmd, cwd=self.project, env=self.env, stdout=f, stderr=subprocess.STDOUT)
        with open(log, 'rb') as f:
            errors = sum(1 for s in f if b'Error:' in s)
        print('cook rc=%d errors=%d' % (rc, errors), flush=True)
        if rc: raise Stop('cook exited with %d' % rc)

    def assemble(self):
        cooked = self.project / 'Saved/Cooked/WindowsNoEditor/Phoenix/Content'
        for g in self.genders:
            gu = g.upper(); d = self.work / f'mod_{g}'
            outfit = d / 'legacy/Phoenix/Content/Data/GearAppearances/Outfit'
            self.note('reset %s, %s' % (d / 'legacy', d / 'legacy_hl'))
            self.note('copy %s (%s paths, no Materials/) -> %s' % (cooked / 'RiggedObjects/Characters/Human',
                                                                   'female' if g == 'f' else 'non-female', d / 'legacy/Phoenix/Content'))
            ga = sorted((self.work / 'ga_out2').glob(f'DA_GA_Outfit_072_{gu}.*'))
            self.note('copy %s -> %s' % (self.work / 'ga_out2' / f'DA_GA_Outfit_072_{gu}.*', outfit))
            if not self.dry:
                for sub in ('legacy', 'legacy_hl'):
                    if (d / sub).exists(): shutil.rmtree(d / sub)
                outfit.mkdir(parents=True)
                human = cooked / 'RiggedObjects/Characters/Human'
                if not human.is_dir(): raise Stop('no cooked files under %s' % human)
                for f in sorted(human.rglob('*')):
                    rel = f.relative_to(cooked).as_posix()
                    if not f.is_file() or '/Materials/' in rel or bool(FEMALE.search(rel)) != (g == 'f'): continue
                    dst = d / 'legacy/Phoenix/Content' / rel
                    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, dst)
                if not ga: raise Stop('no %s/ga_out2/DA_GA_Outfit_072_%s.*' % (self.work, gu))
                for f in ga: shutil.copyfile(f, outfit / f.name)
            lines = self.run([self.probe, 'patch', str(d / 'legacy'), str(d / 'legacy_hl'), str(self.work / f'fit_{g}' / 'skel_ext.json')],
                             keep=r'verify|WARN|FAIL', quiet=True)
            counts = {}
            for s in sorted(lines): counts[s] = counts.get(s, 0) + 1
            for s, n in list(counts.items())[:5]: print('%7d %s' % (n, s), flush=True)
            legacy_hl = d / 'legacy_hl' / HUM; abp = f'/Game/RiggedObjects/Characters/Human/Karin_{gu}'
            self.py('da_animclass.py', self.work / 'dami' / f'DA_HUM_{gu}_Upp_DarkArtsDeluxe01_Master.uasset',
                    legacy_hl / f'Clothing/Upper_{gu}/Jacket_DarkArtsDeluxe01/DA_HUM_{gu}_Upp_DarkArtsDeluxe01_Master.uasset',
                    f'{abp}/ABP_Karin_{gu}_Body', tail=1)
            if g == 'f':
                for h in F_HAIR:
                    self.py('da_animclass.py', self.work / 'hairda_out' / (h.rsplit('/', 1)[1] + '.uasset'),
                            legacy_hl / f'Hair/Hair_F/{h}.uasset', f'{abp}/ABP_Karin_F_Hair', tail=1)
                for mi in MI_CLONES:
                    folder, tok = mi.split(':'); ffolder = folder.replace('_M/', '_F/', 1); ftok = tok.replace('HUM_M_', 'HUM_F_', 1)
                    out = legacy_hl / f'Clothing/{ffolder}/Materials'
                    if not self.dry: out.mkdir(parents=True, exist_ok=True)
                    lines = self.py('mi_clone.py', self.work / 'dami' / f'MI_{tok}.uasset', out / f'MI_{ftok}.uasset',
                                    f'{folder}={ffolder}', f'{tok}={ftok}', quiet=True)
                    if not self.dry: print(''.join(s + ' ' for s in lines), flush=True)
            else:
                self.py('da_animclass.py', self.work / 'hairda_out' / (M_HAIR.rsplit('/', 1)[1] + '.uasset'),
                        legacy_hl / f'Hair/Hair_M/{M_HAIR}.uasset', f'{abp}/ABP_Karin_M_Hair', tail=1)
            if not self.dry:
                print('%s files: %d' % (g, sum(1 for f in (d / 'legacy_hl').rglob('*.uasset'))), flush=True)

    def pack(self):
        mf = self.work / 'mod_mf'
        self.note('reset %s; merge %s' % (mf, ', '.join(str(self.work / f'mod_{g}' / 'legacy_hl') for g in self.genders)))
        if not self.dry:
            if mf.exists(): shutil.rmtree(mf)
            (mf / 'legacy_hl').mkdir(parents=True); (mf / 'out').mkdir()
            for g in self.genders:
                src = self.work / f'mod_{g}' / 'legacy_hl'
                if not src.is_dir(): raise Stop('missing %s (run assemble first)' % src)
                shutil.copytree(src, mf / 'legacy_hl', dirs_exist_ok=True)
        utoc = f'mod_mf/out/{self.pak}.utoc'
        self.run([self.retoc, 'to-zen', '--version', 'UE4_27', 'mod_mf/legacy_hl', utoc], tail=1, cwd=self.work)
        self.run([self.retoc, 'verify', utoc], tail=1, cwd=self.work)
        xz = mf / 'KarinDarkArts.tar.xz'
        self.note('tar %s.pak/.ucas/.utoc | xz -9 > %s' % (self.pak, xz))
        if self.dry: return
        with tarfile.open(xz, 'w:xz', preset=9, format=tarfile.GNU_FORMAT) as t:
            for ext in ('pak', 'ucas', 'utoc'):
                t.add(mf / 'out' / f'{self.pak}.{ext}', arcname=f'{self.pak}.{ext}')
        data = xz.read_bytes()
        print('xz %d sha256 %s' % (len(data), hashlib.sha256(data).hexdigest()[:16]), flush=True)


def check(args, cfg, stages):
    """Every setting, tool and hand-made input the given stages need, before any stage runs."""
    keys = {'work'} | {k for s in stages for k in NEEDS[s]}
    missing = [k for k in ENV if k in keys and not cfg.get(k)]
    if missing:
        raise Stop('set ' + ', '.join('%s (--%s)' % (ENV[k], k.replace('_', '-')) for k in missing)
                   + ' for stage(s) ' + ' '.join(stages))
    work = Path(cfg['work']).resolve()
    problems = []
    if not args.dry_run:
        for k in TOOLS:
            if k in keys and not (Path(cfg[k]).is_file() or shutil.which(cfg[k])):
                problems.append('%s not found: %s' % (ENV[k], cfg[k]))
        if {'import', 'cook'} & set(stages) and not (Path(cfg['project']) / 'Phoenix.uproject').is_file():
            problems.append('no Phoenix.uproject in HL_PROJECT %s' % cfg['project'])
    inputs = []
    for g in cfg['genders']:
        gu = g.upper()
        if {'fit', 'export'} & set(stages): inputs.append(work / f'fit_{g}.json')
        if 'import' in stages: inputs.append(work / f'ue_build_{g}.json')
        if 'assemble' in stages:
            das = [work / 'dami' / f'DA_HUM_{gu}_Upp_DarkArtsDeluxe01_Master.uasset']
            if g == 'f':
                das += [work / 'hairda_out' / (h.rsplit('/', 1)[1] + '.uasset') for h in F_HAIR]
                das += [work / 'dami' / ('MI_%s.uasset' % mi.split(':')[1]) for mi in MI_CLONES]
            else:
                das.append(work / 'hairda_out' / (M_HAIR.rsplit('/', 1)[1] + '.uasset'))
            inputs += [p for da in das for p in (da, da.with_suffix('.uexp'))]
            if not args.dry_run and not list((work / 'ga_out2').glob(f'DA_GA_Outfit_072_{gu}.*')):
                problems.append('missing %s' % (work / 'ga_out2' / f'DA_GA_Outfit_072_{gu}.uasset'))
    if 'params' in stages: inputs.append(work / 'dyn.json')
    for p in inputs:
        if p.is_file() and p.suffix == '.json':
            left = sorted(set(PLACEHOLDER.findall(p.read_text(encoding='utf-8-sig'))))
            if left: problems.append('%s still has placeholders %s' % (p, ' '.join(left)))
        elif not p.is_file() and not args.dry_run:
            problems.append('missing %s' % p)
    if problems: raise Stop('\n  '.join(['cannot start:'] + problems))


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(errors='replace')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stages', nargs='+', choices=STAGES, metavar='stage', help=' '.join(STAGES))
    ap.add_argument('--work', help='work directory (HL_WORK): fit_<g>.json, ue_build_<g>.json, dyn.json, dami/, hairda_out/, ga_out2/')
    ap.add_argument('--blender', help='Blender executable (HL_BLENDER)')
    ap.add_argument('--ue-cmd', help='UE 4.27 Engine/Binaries/Win64/UE4Editor-Cmd.exe (HL_UE_CMD)')
    ap.add_argument('--project', help='content project directory holding Phoenix.uproject (HL_PROJECT)')
    ap.add_argument('--probe', help='HLMeshProbe executable (HL_PROBE)')
    ap.add_argument('--retoc', help='retoc 0.1.5 executable (HL_RETOC)')
    ap.add_argument('--genders', default=os.environ.get('HL_GENDERS', 'm f'),
                    help='"m f" (default, HL_GENDERS) or "f" for the female-only release; also sets the pak name')
    ap.add_argument('--textures', action='store_true', default=os.environ.get('HL_TEXTURES') == '1',
                    help='import the textures listed in ue_build_<g>.json too (HL_TEXTURES=1)')
    ap.add_argument('--dry-run', action='store_true', help='print the commands and file steps without running them')
    args = ap.parse_args(argv)
    genders = args.genders.split()
    if not genders or any(g not in ('m', 'f') for g in genders) or len(set(genders)) != len(genders):
        ap.error('--genders takes "m f", "f m", "m" or "f"')
    cfg = {k: getattr(args, k) or os.environ.get(v) for k, v in ENV.items()}
    cfg['genders'] = genders
    try:
        check(args, cfg, args.stages)
        build = Build(args, cfg)
        for stage in args.stages:
            print('=== ' + stage, flush=True)
            getattr(build, 'import_' if stage == 'import' else stage)()
    except (Stop, OSError) as error:
        sys.exit('build_mod: %s' % error)


if __name__ == '__main__':
    main()
