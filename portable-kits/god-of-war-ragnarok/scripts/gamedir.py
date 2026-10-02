"""Where the game is installed: one setter and two getters shared by every builder module.

The game root is the folder that holds exec/ and libSceAgcTextureTool.dll. It comes from set_game() (the entry
scripts pass --game) or else from the GOWR_GAME environment variable. Nothing is read until a getter is called,
so every module imports without the game.   usage: gamedir.py [--game G]  (prints the resolved folders)"""
import os

ENV = 'GOWR_GAME'
_root = None


def set_game(path):
    """Use `path` as the game root; None falls back to the GOWR_GAME environment variable."""
    global _root
    _root = os.fspath(path) if path else None


def game_root():
    root = _root or os.environ.get(ENV)
    if not root:
        raise SystemExit(f'game folder not set: pass --game <folder with exec/ and libSceAgcTextureTool.dll> '
                         f'or set the {ENV} environment variable')
    if not os.path.isdir(os.path.join(root, 'exec', 'wad', 'pc_le')):
        raise SystemExit(f'{root} is not the God of War Ragnarok folder (exec/wad/pc_le is missing)')
    return root


def wad_dir():
    """<game root>/exec/wad/pc_le: root.lodpack, root.texpack and the character WADs."""
    return os.path.join(game_root(), 'exec', 'wad', 'pc_le')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', help=f'game folder (default: the {ENV} environment variable)')
    set_game(ap.parse_args().game)
    print('game', game_root())
    print('wad ', wad_dir())
