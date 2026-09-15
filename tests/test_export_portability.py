"""Run selected-game tests in detached exports with space-containing paths."""
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
                    print(f'{game}: detached tests passed (unselected games skipped)')


if __name__=='__main__': unittest.main(verbosity=2)
