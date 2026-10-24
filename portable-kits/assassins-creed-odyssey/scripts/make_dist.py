"""Finish a redeployable ACOd package dir (2026-10-24; the v8 package was made with the same steps from a scratchpad
script): copy the build payload, write BUILD_INFO.json + MANIFEST.sha256, zip the dir next to itself.

  python make_dist.py <package_dir> <build_payload_dir> <info.json>

<package_dir> already holds README.md, aco_install.py, _env.cmd, install.cmd, uninstall.cmd, status.cmd.
<info.json>: {"name", "version", "built", "status", "build": {...}}; game, payload and installer hashes are added here.
"""
import argparse
import hashlib
import json
import os
import shutil


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package_dir")
    ap.add_argument("build_payload_dir")
    ap.add_argument("info_json")
    a = ap.parse_args()
    pkg, build, info_path = a.package_dir, a.build_payload_dir, a.info_json
    pay = os.path.join(pkg, "payload")
    if os.path.exists(pay):
        shutil.rmtree(pay)
    shutil.copytree(build, pay)
    info = json.load(open(info_path, encoding="utf-8"))
    info = {"name": info["name"], "version": info["version"], "built": info["built"],
            "game": {"store": "Ubisoft Connect", "product": 5059, "version": "1.5.6", "exe": "ACOdyssey.exe"},
            "status": info["status"], "build": info["build"],
            "payload": {n: {"bytes": os.path.getsize(os.path.join(pay, n)), "sha256": sha(os.path.join(pay, n))}
                        for n in sorted(os.listdir(pay))},
            "installer": {"aco_install.py": sha(os.path.join(pkg, "aco_install.py"))}}
    with open(os.path.join(pkg, "BUILD_INFO.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    lines = []
    for root, _, files in os.walk(pkg):
        for n in files:
            if n != "MANIFEST.sha256":
                p = os.path.join(root, n)
                lines.append((os.path.relpath(p, pkg).replace(os.sep, "/"), sha(p)))
    with open(os.path.join(pkg, "MANIFEST.sha256"), "w", newline="\n") as f:
        f.writelines(f"{d}  {r}\n" for r, d in sorted(lines))
    base = os.path.abspath(pkg)
    z = shutil.make_archive(base, "zip", os.path.dirname(base), os.path.basename(base))
    print(f"{len(lines)} files hashed; {z} {os.path.getsize(z)} bytes sha256 {sha(z)}")


if __name__ == "__main__":
    main()
