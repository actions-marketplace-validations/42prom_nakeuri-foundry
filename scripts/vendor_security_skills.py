#!/usr/bin/env python3
"""Vendor a reviewed, allowlisted subset of a third-party cybersecurity skill catalog.

This script intentionally requires an exact commit. It never executes upstream main directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = json.loads((ROOT / "registry/security/skill_allowlist.json").read_text(encoding="utf-8"))


def sha256_tree(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        h.update(p.relative_to(path).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True, help="Exact reviewed upstream commit SHA")
    ap.add_argument("--include-red-team", action="store_true", help="Vendor authorized-red-team skills too; they remain opt-in")
    args = ap.parse_args()
    if len(args.commit) < 12:
        raise SystemExit("Refusing unpinned/short commit. Supply an exact commit SHA.")

    dest = ROOT / "vendor" / "cybersecurity-skills"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    lock = {"upstream":ALLOW["upstream"],"commit":args.commit,"skills":{}}

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)/"upstream"
        subprocess.run(["git","clone","--filter=blob:none","--no-checkout",ALLOW["upstream"],str(repo)], check=True)
        subprocess.run(["git","-C",str(repo),"checkout","--detach",args.commit], check=True)
        for item in ALLOW["skills"]:
            if item["mode"] != "defensive" and not args.include_red_team:
                continue
            src = repo / "skills" / item["slug"]
            if not src.exists():
                lock["skills"][item["slug"]] = {"status":"missing-upstream"}
                continue
            dst = dest / item["slug"]
            shutil.copytree(src,dst)
            lock["skills"][item["slug"]] = {"status":"vendored","mode":item["mode"],"sha256":sha256_tree(dst)}

    (dest/"LOCK.json").write_text(json.dumps(lock,indent=2)+"\n",encoding="utf-8")
    print(dest/"LOCK.json")

if __name__ == "__main__":
    main()
