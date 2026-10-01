"""Foreground a game window and send held scan-code key presses (games that poll key state per frame).

usage: gamekey.py HANDLE KEY[:hold_ms] [KEY ...]   keys: enter esc up down left right space w a s d tab f1..f12 or 0xSC
"""
import ctypes
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True) if sys.platform == 'win32' else None
SC = {'enter': 0x1C, 'esc': 0x01, 'space': 0x39, 'tab': 0x0F, 'w': 0x11, 'a': 0x1E, 's': 0x1F, 'd': 0x20,
      'e': 0x12, 'q': 0x10, 'f': 0x21, 'r': 0x13, 'c': 0x2E, 'v': 0x2F, 'x': 0x2D, 'z': 0x2C, 'm': 0x32,
      'up': (0x48, True), 'down': (0x50, True), 'left': (0x4B, True), 'right': (0x4D, True),
      'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E, 'f5': 0x3F, 'f6': 0x40, 'f8': 0x42, 'f12': 0x58,
      'grave': 0x29, 'shift': 0x2A, 'ctrl': 0x1D, 'alt': 0x38}
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x8


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('pad', ctypes.c_byte * 32)]
    _anonymous_ = ('u',)
    _fields_ = [('type', wintypes.DWORD), ('u', _U)]


def key(sc, ext, up):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_EXTENDEDKEY if ext else 0) | (KEYEVENTF_KEYUP if up else 0)
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(0, sc, flags, 0, 0)
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise OSError(ctypes.get_last_error())


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Foreground a game window (by handle) and send held scan-code keys.')
    ap.add_argument('hwnd', type=int, help='top-level window handle of the game (match it by process id)')
    ap.add_argument('keys', nargs='+', help='KEY[:hold_ms] (default 120 ms) or waitMS; KEY is a name below '
                                            'or 0xSC: ' + ' '.join(SC))
    a = ap.parse_args()
    if user32 is None:
        ap.error('Windows only')
    hwnd = a.hwnd
    from pywinauto import Application
    w = Application(backend='win32').connect(handle=hwnd).window(handle=hwnd)
    if user32.GetForegroundWindow() != hwnd:
        w.set_focus()
        time.sleep(0.3)
    if user32.GetForegroundWindow() != hwnd:
        print('NOT FOREGROUND', user32.GetForegroundWindow())
        sys.exit(2)
    for tok in a.keys:
        name, _, hold = tok.partition(':')
        hold = int(hold) if hold else 120
        if name.startswith('wait'):
            time.sleep(int(name[4:]) / 1000.0)
            continue
        v = SC[name.lower()] if not name.startswith('0x') else int(name, 16)
        sc, ext = (v if isinstance(v, tuple) else (v, False))
        key(sc, ext, False)
        time.sleep(hold / 1000.0)
        key(sc, ext, True)
        time.sleep(0.15)
    print('ok fg', user32.GetForegroundWindow() == hwnd)


if __name__ == '__main__':
    main()
