from __future__ import annotations

import hashlib
import json
import os
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator

GENESIS = "0" * 64
LEDGER_SCHEMA = "foundry/evidence-ledger/v2"
ANCHOR_SCHEMA = "foundry/evidence-anchor/v1"


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(prev_hash: str, entry: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b"\n")
    h.update(_canonical(entry))
    return h.hexdigest()


def _git(root: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


@contextmanager
def _file_lock(handle: BinaryIO) -> Iterator[None]:
    """Cross-platform advisory lock for one-ledger-writer-at-a-time semantics.

    The handle belongs to a companion lock file, never to the JSONL ledger. Windows
    byte-range locking requires a byte to exist; putting that sentinel in the ledger
    itself would corrupt its line-oriented format.
    """
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        if handle.read(1) == b"":
            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class EvidenceLedger:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / ".factory" / "evidence" / "ledger.jsonl"
        self.lock_path = self.path.with_suffix(".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _rows(handle: TextIO) -> list[dict[str, Any]]:
        handle.seek(0)
        rows = []
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def append(self, evidence: dict[str, Any], actor: str) -> dict[str, Any]:
        if not actor:
            raise ValueError("actor required")
        # The companion lock keeps the ledger valid JSONL on Windows while still
        # serializing the read-head/write-entry critical section across processes.
        with self.lock_path.open("a+b") as lock:
            with _file_lock(lock):
                with self.path.open("a+", encoding="utf-8", newline="\n") as f:
                    rows = self._rows(f)
                    prev = rows[-1].get("entry_hash", GENESIS) if rows else GENESIS
                    body = {
                        "schema": LEDGER_SCHEMA,
                        "seq": len(rows) + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "actor": actor,
                        "evidence": evidence,
                    }
                    row = {**body, "prev_hash": prev, "entry_hash": _hash(prev, body)}
                    f.seek(0, os.SEEK_END)
                    f.write(json.dumps(row, sort_keys=True) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                    return row

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def verify(self) -> dict[str, Any]:
        prev = GENESIS; seq = 0; findings = []
        if not self.path.exists():
            return {"status": "pass", "entries": 0, "head": GENESIS, "findings": []}
        with self.path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    findings.append(f"line {lineno}: invalid JSON")
                    continue
                seq += 1
                if row.get("schema") not in {"foundry/evidence-ledger/v1", LEDGER_SCHEMA}:
                    findings.append(f"line {lineno}: unsupported schema")
                if row.get("seq") != seq:
                    findings.append(f"line {lineno}: sequence mismatch")
                if row.get("prev_hash") != prev:
                    findings.append(f"line {lineno}: previous hash mismatch")
                body = {k: row.get(k) for k in ["schema", "seq", "timestamp", "actor", "evidence"]}
                expected = _hash(prev, body)
                if row.get("entry_hash") != expected:
                    findings.append(f"line {lineno}: entry hash mismatch")
                prev = row.get("entry_hash", prev)
        return {"status": "fail" if findings else "pass", "entries": seq, "head": prev, "findings": findings}

    def create_anchor(self, actor: str, *, external_reference: str | None = None) -> dict[str, Any]:
        """Create a portable receipt binding the current ledger head to source Git state.

        This detects accidental/local rewriting when the receipt is preserved elsewhere.
        It is intentionally *not* described as an external trust anchor unless an external
        attestation/reference is supplied and independently preserved.
        """
        check = self.verify()
        if check["status"] != "pass":
            raise ValueError(f"cannot anchor invalid ledger: {check['findings']}")
        commit = _git(self.root, "rev-parse", "HEAD")
        if not commit:
            raise ValueError("ledger anchor requires a git commit")
        body = {
            "schema": ANCHOR_SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "git_commit": commit,
            "git_branch": _git(self.root, "branch", "--show-current"),
            "ledger_entries": check["entries"],
            "ledger_head": check["head"],
            "external_reference": external_reference,
            "external_trust": bool(external_reference),
        }
        receipt = {**body, "anchor_hash": hashlib.sha256(_canonical(body)).hexdigest()}
        out = self.root / ".factory" / "evidence" / "anchors"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{commit[:12]}-{check['head'][:12]}.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {**receipt, "path": str(path.relative_to(self.root))}

    def verify_anchor(self, receipt_or_path: dict[str, Any] | Path) -> dict[str, Any]:
        if isinstance(receipt_or_path, Path):
            try:
                receipt = json.loads(receipt_or_path.read_text(encoding="utf-8"))
            except Exception as exc:
                return {"status": "fail", "findings": [f"invalid anchor JSON: {exc}"]}
        else:
            receipt = dict(receipt_or_path)
        findings = []
        if receipt.get("schema") != ANCHOR_SCHEMA:
            findings.append("unsupported anchor schema")
        body = {k: receipt.get(k) for k in ["schema", "created_at", "actor", "git_commit", "git_branch", "ledger_entries", "ledger_head", "external_reference", "external_trust"]}
        if hashlib.sha256(_canonical(body)).hexdigest() != receipt.get("anchor_hash"):
            findings.append("anchor hash mismatch")
        ledger = self.verify()
        if ledger.get("status") != "pass":
            findings.append("ledger is invalid")
        if ledger.get("head") != receipt.get("ledger_head") or ledger.get("entries") != receipt.get("ledger_entries"):
            findings.append("ledger no longer matches anchor")
        commit = _git(self.root, "rev-parse", "HEAD")
        if commit and receipt.get("git_commit") != commit:
            findings.append("anchor is not bound to current HEAD")
        return {"status": "fail" if findings else "pass", "findings": findings, "external_trust": bool(receipt.get("external_trust"))}
