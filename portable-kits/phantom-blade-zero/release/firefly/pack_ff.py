r"""Firefly release packages, as the Lenko release:
  <release_dir>/<name>.zip  install.cmd / install.ps1 / uninstall.cmd / README.txt / files\ (+ SHA256SUMS.txt)
  <release_dir>/<name>.rar  README.txt + ~mods\ (+ SHA256SUMS.txt), made with WinRAR's Rar.exe (--rar)
install.ps1, README.txt and README_rar.txt ({DATE} replaced) are taken from this script's folder; the two .cmd
launchers are written by the script.
"""
import argparse, os, hashlib, shutil, zipfile, subprocess, tempfile
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("src", help="folder holding z_FireflyPBZ_P.pak / .ucas / .utoc (the build's out folder)")
ap.add_argument("out", help="release folder the .zip and .rar are written to")
ap.add_argument("name", help="package name, e.g. FireflyPBZ_20261107")
ap.add_argument("date", help="date written into the READMEs, e.g. 2026-11-07")
ap.add_argument("--rar", default=os.path.join(os.environ.get("ProgramFiles", ""), "WinRAR", "Rar.exe"),
                help="WinRAR command-line Rar.exe (default: under %%ProgramFiles%%)")
args = ap.parse_args()
SRC, OUTD, NAME, DATE, RAR = args.src, args.out, args.name, args.date, args.rar
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = ["z_FireflyPBZ_P.pak", "z_FireflyPBZ_P.ucas", "z_FireflyPBZ_P.utoc"]
# the two launchers are written here (the knowledge base does not take .cmd files); ASCII, CRLF
LAUNCH = '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"{}%*\r\npause\r\n'
def read(p):
    with open(p, "rb") as fh: return fh.read()
def write(p, data):
    with open(p, "wb") as fh: fh.write(data)
def sha(p): return hashlib.sha256(read(p)).hexdigest().upper()
sums = "".join(f"{sha(os.path.join(SRC, n))}  {n}\r\n" for n in NAMES).encode("ascii")
def text(src, dst):   # UTF-8 with BOM, CRLF (Notepad / PowerShell 5.1)
    s = read(src).decode("utf-8-sig").replace("\r\n", "\n").replace("{DATE}", DATE)
    write(dst, b"\xef\xbb\xbf" + s.replace("\n", "\r\n").encode("utf-8"))
tmp = tempfile.mkdtemp()
# zip: installer layout
d = os.path.join(tmp, "zip", NAME); os.makedirs(os.path.join(d, "files"))
shutil.copy2(os.path.join(HERE, "install.ps1"), d)
for f, extra in (("install.cmd", " "), ("uninstall.cmd", " -Uninstall ")):
    write(os.path.join(d, f), LAUNCH.format(extra).encode("ascii"))
text(os.path.join(HERE, "README.txt"), os.path.join(d, "README.txt"))
for n in NAMES: shutil.copy2(os.path.join(SRC, n), os.path.join(d, "files", n))
write(os.path.join(d, "files", "SHA256SUMS.txt"), sums)
zp = os.path.join(OUTD, NAME + ".zip")
if os.path.exists(zp): os.remove(zp)
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(d):
        for f in sorted(files):
            p = os.path.join(root, f); z.write(p, os.path.relpath(p, os.path.dirname(d)))
# rar: ~mods layout
r = os.path.join(tmp, "rar", NAME); os.makedirs(os.path.join(r, "~mods"))
text(os.path.join(HERE, "README_rar.txt"), os.path.join(r, "README.txt"))
for n in NAMES: shutil.copy2(os.path.join(SRC, n), os.path.join(r, "~mods", n))
write(os.path.join(r, "~mods", "SHA256SUMS.txt"), sums)
rp = os.path.join(OUTD, NAME + ".rar")
if os.path.exists(rp): os.remove(rp)
subprocess.run([RAR, "a", "-r", "-ep1", "-idq", rp, r], check=True)
shutil.rmtree(tmp)
print(sums.decode("ascii").strip())
for p in (zp, rp): print("PACK", p, os.path.getsize(p), sha(p))
