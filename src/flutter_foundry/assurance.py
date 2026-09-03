from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .safe_paths import resolve_inside, safe_identifier


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_source(root: Path, value: str) -> Path | None:
    try:
        candidate = resolve_inside(root, value, must_exist=True)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def build_assurance_archive(root: Path, task_id: str, destination_root: Path | None = None) -> dict[str, Any]:
    """Create a portable, hash-manifested assurance archive.

    Runtime evidence lives outside Git by design, so the archive includes the proof,
    ledger, reviews, and any proof-referenced local artifacts before a task worktree
    can be cleaned up. ``destination_root`` lets an isolated worktree persist its
    assurance record in the parent/control repository.
    """

    task_id = safe_identifier(task_id, label="task_id")
    root = root.resolve()
    destination_root = (destination_root or root).resolve()
    out_dir = destination_root / ".factory" / "assurance"
    out_dir.mkdir(parents=True, exist_ok=True)

    sources: list[Path] = []
    proof_path = root / ".factory" / "proofs" / f"{task_id}.json"
    ledger_path = root / ".factory" / "evidence" / "ledger.jsonl"
    for p in [proof_path, ledger_path]:
        if p.exists():
            sources.append(p)

    reviews = root / ".factory" / "reviews" / task_id
    if reviews.exists():
        sources.extend(sorted(reviews.glob("*.json")))

    # Preserve evidence artifacts referenced by the proof itself.
    if proof_path.exists():
        try:
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
        except Exception:
            proof = {}
        for ev in proof.get("evidence", []):
            art = ev.get("artifact") or {}
            rel = art.get("path") if isinstance(art, dict) else None
            if rel:
                p = _safe_source(root, str(rel))
                if p is not None:
                    sources.append(p)

    # Stable de-duplication.
    unique: list[Path] = []
    seen: set[str] = set()
    for p in sources:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key); unique.append(p)

    manifest = {
        "schema": "foundry/assurance-archive/v2",
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": None,
        "artifacts": [],
    }
    if proof_path.exists():
        try:
            manifest["source_commit"] = json.loads(proof_path.read_text(encoding="utf-8")).get("git", {}).get("commit")
        except Exception:
            pass

    for p in unique:
        archive_path = p.relative_to(root).as_posix()
        manifest["artifacts"].append({
            "path": archive_path,
            "sha256": _sha(p),
            "size": p.stat().st_size,
        })

    manifest_path = out_dir / f"{task_id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    archive = out_dir / f"{task_id}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(manifest_path, "manifest.json")
        for p in unique:
            z.write(p, p.relative_to(root).as_posix())
    return {"status": "pass", "archive": str(archive), "sha256": _sha(archive), "manifest": manifest}


def verify_assurance_archive(path: Path) -> dict[str, Any]:
    """Verify archive integrity without trusting the source worktree."""

    path = path.resolve(); findings: list[str] = []
    if not path.exists():
        return {"status": "fail", "findings": ["assurance archive missing"]}
    try:
        with zipfile.ZipFile(path, "r") as z:
            infos = z.infolist()
            if len(infos) > 500:
                return {"status": "fail", "findings": ["archive contains too many entries"]}
            total = 0
            for info in infos:
                name = info.filename
                parts = Path(name).parts
                if Path(name).is_absolute() or ".." in parts:
                    findings.append(f"unsafe archive path: {name}")
                if info.file_size > 100 * 1024 * 1024:
                    findings.append(f"archive entry too large: {name}")
                total += info.file_size
            if total > 500 * 1024 * 1024:
                findings.append("archive uncompressed size exceeds safety limit")
            names = set(z.namelist())
            if "manifest.json" not in names:
                return {"status": "fail", "findings": ["manifest.json missing"]}
            manifest = json.loads(z.read("manifest.json"))
            if manifest.get("schema") != "foundry/assurance-archive/v2":
                findings.append("unsupported assurance manifest schema")
            for art in manifest.get("artifacts", []):
                name = art.get("path")
                if not name or name not in names:
                    findings.append(f"missing archived artifact: {name}")
                    continue
                data = z.read(name)
                if len(data) != art.get("size"):
                    findings.append(f"size mismatch: {name}")
                if hashlib.sha256(data).hexdigest() != art.get("sha256"):
                    findings.append(f"hash mismatch: {name}")
    except Exception as exc:
        findings.append(f"invalid assurance archive: {exc}")
    return {"status": "fail" if findings else "pass", "findings": findings, "path": str(path)}
