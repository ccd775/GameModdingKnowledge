"""Run selected-game tests in detached exports with space-containing paths."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from export_kit import export, GAMES


class DetachedExports(unittest.TestCase):
    def test_all_games_without_parent_checkout(self):
        with tempfile.TemporaryDirectory(prefix='modding detached ') as folder:
            for game in GAMES:
                with self.subTest(game=game):
                    target = Path(folder)/game
                    summary = export(game, target)
                    self.assertGreater(summary['files'], 20)
                    config=json.loads((target/f'portable-kits/{game}/toolchain.json').read_text())
                    for script in config['bundled_scripts']:
                        self.assertTrue((target/f'portable-kits/{game}'/script).is_file())
                    process = subprocess.run([sys.executable,'-B','tests/test_portable_tools.py'],
                                             cwd=target, capture_output=True, text=True, timeout=60)
                    self.assertEqual(process.returncode,0,process.stdout+'\n'+process.stderr)
                    if game == 'mortal-kombat-1':
                        self.assertIn('test_mk1_synthetic_suite_and_cli', process.stderr)
                        self.assertNotIn("test_mk1_synthetic_suite_and_cli (__main__.MK1Tools.test_mk1_synthetic_suite_and_cli) ... skipped", process.stderr)
                    if game == 'ghost-of-tsushima':
                        self.assertTrue((target/'portable-kits/ghost-of-tsushima/requirements.txt').is_file())
                    if game == 'ghost-of-tsushima' and all(importlib.util.find_spec(m) for m in
                                                           ('numpy', 'scipy', 'etcpak', 'texture2ddecoder', 'PIL')):
                        self.assertIn('test_got_hang_pose_and_rest_solve', process.stderr)
                        self.assertFalse([l for l in process.stderr.splitlines() if 'test_got_' in l and 'skipped' in l])
                    if game == 'horizon-forbidden-west':
                        self.assertTrue((target/'portable-kits/horizon-forbidden-west/requirements.txt').is_file())
                    if game == 'horizon-forbidden-west' and all(importlib.util.find_spec(m) for m in
                                                                ('numpy', 'scipy', 'PIL')):
                        self.assertIn('test_hfw_core_patch_and_refusal', process.stderr)
                        self.assertFalse([l for l in process.stderr.splitlines() if 'test_hfw_' in l and 'skipped' in l])
                    if game == 'god-of-war-ragnarok':
                        self.assertTrue((target/'portable-kits/god-of-war-ragnarok/requirements.txt').is_file())
                    if game == 'god-of-war-ragnarok' and all(importlib.util.find_spec(m) for m in
                                                             ('numpy', 'scipy', 'PIL', 'lz4', 'etcpak', 'texture2ddecoder')):
                        self.assertIn('test_gowr_joint_layouts_roundtrip', process.stderr)
                        self.assertFalse([l for l in process.stderr.splitlines() if 'test_gowr_' in l and 'skipped' in l])
                    if game == 'watch-dogs':
                        self.assertTrue((target/'portable-kits/watch-dogs/requirements.txt').is_file())
                        self.assertIn('test_wd_fat8_repack_replace_and_extract', process.stderr)
                    if game == 'watch-dogs' and all(importlib.util.find_spec(m) for m in ('numpy', 'PIL')):
                        self.assertIn('test_wd_xbg_palette_growth_keeps_matrix_table_aligned', process.stderr)
                        self.assertFalse([l for l in process.stderr.splitlines() if 'test_wd_' in l and 'skipped' in l])
                    print(f'{game}: detached tests passed (unselected games skipped)')


if __name__=='__main__': unittest.main(verbosity=2)
