#!/usr/bin/env python3
"""Run L4D2 studiomdl with captured logs and hashed output artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


MODELNAME_RE = re.compile(r'^\s*\$modelname\s+"([^"]+)"', re.I | re.M)
COLLISION_RE = re.compile(r'^\s*\$collisionjoints\b', re.I | re.M)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--studiomdl", required=True, type=Path)
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--qc", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    args = parse_args()
    studiomdl = args.studiomdl.resolve()
    game = args.game.resolve()
    qc = args.qc.resolve()
    log_path = args.log.resolve()
    report_path = args.report.resolve()
    qc_text = qc.read_text(encoding="utf-8", errors="replace")
    model_match = MODELNAME_RE.search(qc_text)
    if not model_match:
        raise ValueError(f"No $modelname in {qc}")
    model_relative = Path(*model_match.group(1).replace("\\", "/").split("/"))
    if model_relative.is_absolute() or '..' in model_relative.parts or ':' in str(model_relative):
        raise ValueError("$modelname must stay inside the sandbox models directory")
    for path in (log_path, report_path):
        if path.exists():
            raise FileExistsError(path)
    existing = game / 'models' / model_relative
    if existing.exists():
        raise FileExistsError("Compile into a fresh sandbox to avoid stale-output acceptance")

    command = [str(studiomdl), "-nop4", "-game", str(game), str(qc)]
    result = subprocess.run(
        command,
        cwd=str(qc.parent),
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    combined = result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else "")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(combined, encoding="utf-8")

    mdl_path = game / "models" / model_relative
    companions = [
        mdl_path,
        mdl_path.with_suffix(".vvd"),
        mdl_path.with_name(mdl_path.stem + ".dx90.vtx"),
    ]
    expects_phy = bool(re.search(r'^\s*\$collision(?:joints|model)\b', qc_text, re.I | re.M))
    if expects_phy:
        companions.append(mdl_path.with_suffix(".phy"))
    outputs = []
    for path in companions:
        if path.is_file():
            outputs.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    accepted = result.returncode == 0 and len(outputs) == len(companions)
    report = {
        "schema": "karin-l4d2-studiomdl-run/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "studiomdl": {
            "path": str(studiomdl),
            "sha256": sha256_file(studiomdl),
        },
        "game": str(game),
        "qc": {"path": str(qc), "sha256": sha256_file(qc)},
        "model_relative": model_relative.as_posix(),
        "expects_phy": expects_phy,
        "returncode": result.returncode,
        "accepted": accepted,
        "evidence_scope": "compiler exit and companion existence only; binary and runtime checks remain separate",
        "log": {"path": str(log_path), "sha256": sha256_file(log_path)},
        "outputs": outputs,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"STUDIOMDL_RETURNCODE={result.returncode}")
    print(f"STUDIOMDL_ACCEPTED={accepted}")
    print(f"STUDIOMDL_LOG={log_path}")
    print(f"STUDIOMDL_REPORT={report_path}")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
