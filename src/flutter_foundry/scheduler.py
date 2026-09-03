from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .safe_paths import safe_identifier

SCHEMA_VERSION = 4
TERMINAL = {"MERGED", "CANCELLED", "FAILED"}
RUNNABLE = {"READY", "REPAIRING"}
ALLOWED = {
    "DEFINED": {"READY", "BLOCKED", "CANCELLED"},
    "READY": {"IMPLEMENTING", "BLOCKED", "CANCELLED"},
    "IMPLEMENTING": {"VERIFYING", "REPAIRING", "BLOCKED", "CANCELLED"},
    "VERIFYING": {"REVIEWING", "REPAIRING", "BLOCKED", "CANCELLED"},
    "REVIEWING": {"MERGEABLE", "REPAIRING", "BLOCKED", "CANCELLED"},
    "REPAIRING": {"IMPLEMENTING", "VERIFYING", "BLOCKED", "CANCELLED", "FAILED"},
    "MERGEABLE": {"MERGED", "BLOCKED", "CANCELLED"},
    "BLOCKED": {"READY", "CANCELLED"},
    "MERGED": set(), "CANCELLED": set(), "FAILED": set(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _utcnow()).isoformat()


class Scheduler:
    """Durable local task scheduler with migrations, leases, retries and recovery."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / ".factory" / "orchestration" / "scheduler.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=15000")
        try:
            yield con
        finally:
            con.close()

    def _base_schema(self, con: sqlite3.Connection) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              risk TEXT NOT NULL,
              state TEXT NOT NULL,
              owner TEXT,
              writer TEXT,
              branch TEXT,
              worktree TEXT,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_attempts INTEGER NOT NULL DEFAULT 2,
              lease_owner TEXT,
              lease_until TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS deps(
              task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              depends_on TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
              PRIMARY KEY(task_id, depends_on)
            );
            CREATE TABLE IF NOT EXISTS task_usage(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              at TEXT NOT NULL,
              task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              actor TEXT NOT NULL,
              role TEXT NOT NULL,
              cost_usd REAL NOT NULL DEFAULT 0,
              tokens INTEGER NOT NULL DEFAULT 0,
              seconds REAL NOT NULL DEFAULT 0,
              metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              at TEXT NOT NULL,
              task_id TEXT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL DEFAULT '{}',
              prev_hash TEXT,
              event_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS migration_history(
              version INTEGER PRIMARY KEY,
              applied_at TEXT NOT NULL,
              description TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_usage_task ON task_usage(task_id, seq);
            CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
            CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id, seq);
            """
        )

    def _column_names(self, con: sqlite3.Connection, table: str) -> set[str]:
        return {str(r[1]) for r in con.execute(f"PRAGMA table_info({table})").fetchall()}

    def _migrate(self, con: sqlite3.Connection) -> None:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        # Databases created by pre-migration Foundry have user_version=0 but are v1.
        if version == 0:
            con.execute("PRAGMA user_version=1")
            con.execute(
                "INSERT OR IGNORE INTO migration_history(version,applied_at,description) VALUES(1,?,?)",
                (_iso(), "baseline schema adopted"),
            )
            version = 1
        if version < 2:
            cols = self._column_names(con, "tasks")
            if "idempotency_key" not in cols:
                con.execute("ALTER TABLE tasks ADD COLUMN idempotency_key TEXT")
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
            con.execute("PRAGMA user_version=2")
            con.execute(
                "INSERT OR IGNORE INTO migration_history(version,applied_at,description) VALUES(2,?,?)",
                (_iso(), "idempotent task creation and explicit schema versioning"),
            )
            version = 2
        if version < 3:
            cols = self._column_names(con, "events")
            if "prev_hash" not in cols:
                con.execute("ALTER TABLE events ADD COLUMN prev_hash TEXT")
            if "event_hash" not in cols:
                con.execute("ALTER TABLE events ADD COLUMN event_hash TEXT")
            self._backfill_event_hashes(con)
            con.execute("PRAGMA user_version=3")
            con.execute(
                "INSERT OR IGNORE INTO migration_history(version,applied_at,description) VALUES(3,?,?)",
                (_iso(), "tamper-evident orchestration event chain and replay verification"),
            )
            version = 3
        if version < 4:
            cols = self._column_names(con, "tasks")
            if "lease_token" not in cols:
                con.execute("ALTER TABLE tasks ADD COLUMN lease_token TEXT")
            con.execute("PRAGMA user_version=4")
            con.execute(
                "INSERT OR IGNORE INTO migration_history(version,applied_at,description) VALUES(4,?,?)",
                (_iso(), "lease fencing token prevents stale worker completion after recovery/reclaim"),
            )

    @staticmethod
    def _event_digest(at: str, task_id: str | None, kind: str, payload: str, prev_hash: str) -> str:
        canonical = json.dumps(
            {"at": at, "task_id": task_id, "kind": kind, "payload": json.loads(payload or "{}"), "prev_hash": prev_hash},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _backfill_event_hashes(self, con: sqlite3.Connection) -> None:
        prev = "0" * 64
        rows = con.execute("SELECT seq,at,task_id,kind,payload FROM events ORDER BY seq").fetchall()
        for row in rows:
            digest = self._event_digest(row["at"], row["task_id"], row["kind"], row["payload"], prev)
            con.execute("UPDATE events SET prev_hash=?,event_hash=? WHERE seq=?", (prev, digest, row["seq"]))
            prev = digest

    def _init(self) -> None:
        # sqlite3.executescript performs its own transaction boundary in autocommit
        # mode. Keep initialization idempotent and let each DDL statement commit
        # atomically rather than attempting a nested manual COMMIT.
        with self._db() as con:
            self._base_schema(con)
            self._migrate(con)

    def schema_status(self) -> dict[str, Any]:
        with self._db() as con:
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            history = [dict(r) for r in con.execute("SELECT * FROM migration_history ORDER BY version")]
        return {"status": "pass" if version == SCHEMA_VERSION else "fail", "version": version, "expected": SCHEMA_VERSION, "history": history}

    def integrity_check(self) -> dict[str, Any]:
        with self._db() as con:
            quick = [str(r[0]) for r in con.execute("PRAGMA quick_check").fetchall()]
            fk = [dict(r) for r in con.execute("PRAGMA foreign_key_check").fetchall()]
        findings = []
        if quick != ["ok"]:
            findings.extend(quick)
        if fk:
            findings.append(f"foreign key violations: {len(fk)}")
        return {"status": "fail" if findings else "pass", "quick_check": quick, "foreign_key_violations": fk, "findings": findings}

    def backup(self, destination: Path | None = None) -> dict[str, Any]:
        destination = destination or (self.path.parent / "backups" / f"scheduler-{_utcnow().strftime('%Y%m%dT%H%M%SZ')}.db")
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as src:
            dst = sqlite3.connect(destination)
            try:
                src.backup(dst)
            finally:
                dst.close()
        return {"status": "pass", "path": str(destination), "integrity": self._integrity_file(destination)}

    @staticmethod
    def _integrity_file(path: Path) -> dict[str, Any]:
        con = sqlite3.connect(path)
        try:
            quick = [str(r[0]) for r in con.execute("PRAGMA quick_check").fetchall()]
        finally:
            con.close()
        return {"status": "pass" if quick == ["ok"] else "fail", "quick_check": quick}

    def recover_expired_leases(self) -> dict[str, Any]:
        now = _iso()
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute(
                "SELECT id,state,lease_owner,lease_until FROM tasks WHERE lease_until IS NOT NULL AND lease_until < ? AND state NOT IN ('MERGED','CANCELLED','FAILED')",
                (now,),
            ).fetchall()
            for row in rows:
                new_state = "READY" if row["state"] == "IMPLEMENTING" else row["state"]
                con.execute(
                    "UPDATE tasks SET lease_owner=NULL,lease_until=NULL,lease_token=NULL,state=?,updated_at=? WHERE id=?",
                    (new_state, now, row["id"]),
                )
                self._event(con, row["id"], "lease_recovered", {"previous_owner": row["lease_owner"], "previous_until": row["lease_until"], "state": new_state})
            con.execute("COMMIT")
        return {"status": "pass", "recovered": len(rows), "tasks": [r["id"] for r in rows]}

    def repair(self, *, backup_first: bool = True) -> dict[str, Any]:
        before = self.integrity_check()
        backup = self.backup() if backup_first and before.get("status") == "pass" else None
        recovered = self.recover_expired_leases()
        after = self.integrity_check()
        return {"status": after["status"], "before": before, "backup": backup, "recovery": recovered, "after": after, "schema": self.schema_status()}

    def _event(self, con: sqlite3.Connection, task_id: str | None, kind: str, payload: dict[str, Any] | None = None) -> None:
        at = _iso()
        payload_text = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        row = con.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev_hash = str(row[0]) if row and row[0] else "0" * 64
        event_hash = self._event_digest(at, task_id, kind, payload_text, prev_hash)
        con.execute(
            "INSERT INTO events(at,task_id,kind,payload,prev_hash,event_hash) VALUES(?,?,?,?,?,?)",
            (at, task_id, kind, payload_text, prev_hash, event_hash),
        )

    def verify_event_chain(self) -> dict[str, Any]:
        with self._db() as con:
            rows = con.execute("SELECT seq,at,task_id,kind,payload,prev_hash,event_hash FROM events ORDER BY seq").fetchall()
        prev = "0" * 64
        for row in rows:
            if row["prev_hash"] != prev:
                return {"status": "fail", "seq": row["seq"], "reason": "prev_hash mismatch", "events": len(rows)}
            expected = self._event_digest(row["at"], row["task_id"], row["kind"], row["payload"], prev)
            if row["event_hash"] != expected:
                return {"status": "fail", "seq": row["seq"], "reason": "event_hash mismatch", "events": len(rows)}
            prev = expected
        return {"status": "pass", "events": len(rows), "head": prev, "schema": "nakeuri/orchestration-events/v1"}

    def replay_task(self, task_id: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        chain = self.verify_event_chain()
        if chain["status"] != "pass":
            return {"status": "fail", "reason": "event chain invalid", "chain": chain}
        with self._db() as con:
            rows = con.execute("SELECT seq,at,kind,payload,event_hash FROM events WHERE task_id=? ORDER BY seq", (task_id,)).fetchall()
        events = []
        for row in rows:
            events.append({"seq": row["seq"], "at": row["at"], "kind": row["kind"], "payload": json.loads(row["payload"] or "{}"), "event_hash": row["event_hash"]})
        return {"status": "pass", "task_id": task_id, "events": events, "count": len(events), "chain_head": chain["head"]}

    def create_task(
        self,
        title: str,
        risk: str = "MEDIUM",
        depends_on: list[str] | None = None,
        max_attempts: int = 2,
        metadata: dict[str, Any] | None = None,
        task_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if max_attempts < 0:
            raise ValueError("max_attempts must be >= 0")
        task_id = safe_identifier(task_id or f"TASK-{uuid.uuid4().hex[:8].upper()}", label="task_id")
        if idempotency_key is not None:
            idempotency_key = safe_identifier(idempotency_key, label="idempotency_key")
        now = _iso()
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                existing = con.execute("SELECT id FROM tasks WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if existing:
                    con.execute("COMMIT")
                    return self.get(existing["id"])
            for dep in depends_on or []:
                safe_identifier(dep, label="dependency task_id")
                if not con.execute("SELECT 1 FROM tasks WHERE id=?", (dep,)).fetchone():
                    con.execute("ROLLBACK")
                    raise ValueError(f"unknown dependency: {dep}")
            con.execute(
                "INSERT INTO tasks(id,title,risk,state,max_attempts,created_at,updated_at,metadata,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?)",
                (task_id, title, risk.upper(), "DEFINED", max_attempts, now, now, json.dumps(metadata or {}, sort_keys=True), idempotency_key),
            )
            for dep in depends_on or []:
                con.execute("INSERT INTO deps(task_id,depends_on) VALUES(?,?)", (task_id, dep))
            self._event(con, task_id, "created", {"risk": risk.upper(), "depends_on": depends_on or [], "idempotency_key": idempotency_key})
            con.execute("COMMIT")
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise KeyError(task_id)
            deps = [r[0] for r in con.execute("SELECT depends_on FROM deps WHERE task_id=? ORDER BY depends_on", (task_id,))]
        out = dict(row)
        out["metadata"] = json.loads(out["metadata"] or "{}")
        out["depends_on"] = deps
        return out

    def ready(self, task_id: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                con.execute("ROLLBACK"); raise KeyError(task_id)
            if row["state"] not in {"DEFINED", "BLOCKED"}:
                con.execute("ROLLBACK"); raise ValueError(f"cannot ready from {row['state']}")
            unmet = [r[0] for r in con.execute(
                """SELECT d.depends_on FROM deps d JOIN tasks t ON t.id=d.depends_on
                   WHERE d.task_id=? AND t.state!='MERGED'""", (task_id,)
            )]
            if unmet:
                con.execute("ROLLBACK"); raise ValueError(f"unmet dependencies: {unmet}")
            con.execute("UPDATE tasks SET state='READY',updated_at=? WHERE id=?", (_iso(), task_id))
            self._event(con, task_id, "ready")
            con.execute("COMMIT")
        return self.get(task_id)

    def claim_next(self, worker: str, lease_seconds: int = 900) -> dict[str, Any] | None:
        if not worker:
            raise ValueError("worker required")
        now = _utcnow(); until = _iso(now + timedelta(seconds=max(30, lease_seconds)))
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            # Claim also performs cheap crash recovery, but records it for auditability.
            expired = con.execute(
                "SELECT id,state,lease_owner,lease_until FROM tasks WHERE lease_until IS NOT NULL AND lease_until < ? AND state NOT IN ('MERGED','CANCELLED','FAILED')",
                (_iso(now),),
            ).fetchall()
            for old in expired:
                state = "READY" if old["state"] == "IMPLEMENTING" else old["state"]
                con.execute("UPDATE tasks SET lease_owner=NULL,lease_until=NULL,lease_token=NULL,state=?,updated_at=? WHERE id=?", (state, _iso(now), old["id"]))
                self._event(con, old["id"], "lease_recovered", {"previous_owner": old["lease_owner"], "previous_until": old["lease_until"], "state": state})
            row = con.execute(
                """SELECT t.id FROM tasks t
                   WHERE t.state IN ('READY','REPAIRING')
                     AND t.lease_owner IS NULL
                     AND NOT EXISTS(
                       SELECT 1 FROM deps d JOIN tasks p ON p.id=d.depends_on
                       WHERE d.task_id=t.id AND p.state!='MERGED'
                     )
                   ORDER BY CASE t.risk WHEN 'RELEASE' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                            t.created_at, t.id LIMIT 1"""
            ).fetchone()
            if not row:
                con.execute("COMMIT"); return None
            task_id = row["id"]
            lease_token = uuid.uuid4().hex
            cur = con.execute(
                "UPDATE tasks SET state='IMPLEMENTING',owner=?,writer=COALESCE(writer,?),lease_owner=?,lease_until=?,lease_token=?,updated_at=? WHERE id=? AND lease_owner IS NULL AND state IN ('READY','REPAIRING')",
                (worker, worker, worker, until, lease_token, _iso(now), task_id),
            )
            if cur.rowcount != 1:
                con.execute("ROLLBACK")
                return None
            self._event(con, task_id, "claimed", {"worker": worker, "lease_until": until, "lease_token_hash": hashlib.sha256(lease_token.encode()).hexdigest()})
            con.execute("COMMIT")
        return self.get(task_id)

    def heartbeat(self, task_id: str, worker: str, lease_seconds: int = 900, lease_token: str | None = None) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        until = _iso(_utcnow() + timedelta(seconds=max(30, lease_seconds)))
        with self._db() as con:
            if lease_token is None:
                cur = con.execute(
                    "UPDATE tasks SET lease_until=?,updated_at=? WHERE id=? AND lease_owner=? AND state='IMPLEMENTING'",
                    (until, _iso(), task_id, worker),
                )
            else:
                cur = con.execute(
                    "UPDATE tasks SET lease_until=?,updated_at=? WHERE id=? AND lease_owner=? AND lease_token=? AND state='IMPLEMENTING'",
                    (until, _iso(), task_id, worker, lease_token),
                )
            if cur.rowcount != 1:
                raise ValueError("task is not leased by this worker")
            self._event(con, task_id, "heartbeat", {"worker": worker, "lease_until": until})
        return self.get(task_id)

    def finish_attempt(self, task_id: str, worker: str, success: bool, reason: str = "", lease_token: str | None = None) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                con.execute("ROLLBACK"); raise KeyError(task_id)
            if row["lease_owner"] != worker:
                con.execute("ROLLBACK"); raise ValueError("task is not leased by this worker")
            if lease_token is not None and row["lease_token"] != lease_token:
                con.execute("ROLLBACK"); raise ValueError("stale lease fencing token")
            attempts = row["attempts"] + (0 if success else 1)
            if success:
                state = "VERIFYING"
            elif attempts <= row["max_attempts"]:
                state = "REPAIRING"
            else:
                state = "FAILED"
            con.execute(
                "UPDATE tasks SET state=?,attempts=?,lease_owner=NULL,lease_until=NULL,lease_token=NULL,updated_at=? WHERE id=?",
                (state, attempts, _iso(), task_id),
            )
            self._event(con, task_id, "attempt_finished", {"worker": worker, "success": success, "reason": reason, "attempts": attempts, "state": state})
            con.execute("COMMIT")
        return self.get(task_id)

    def transition(self, task_id: str, new_state: str, actor: str = "system", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        new_state = new_state.upper()
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                con.execute("ROLLBACK"); raise KeyError(task_id)
            old = row["state"]
            if new_state not in ALLOWED.get(old, set()):
                con.execute("ROLLBACK"); raise ValueError(f"illegal transition {old}->{new_state}")
            if new_state == "READY":
                unmet = [r[0] for r in con.execute(
                    """SELECT d.depends_on FROM deps d JOIN tasks p ON p.id=d.depends_on
                       WHERE d.task_id=? AND p.state!='MERGED'""", (task_id,)
                )]
                if unmet:
                    con.execute("ROLLBACK"); raise ValueError(f"unmet dependencies: {unmet}")
            con.execute("UPDATE tasks SET state=?,updated_at=? WHERE id=?", (new_state, _iso(), task_id))
            self._event(con, task_id, "transition", {"from": old, "to": new_state, "actor": actor, **(payload or {})})
            con.execute("COMMIT")
        return self.get(task_id)

    def attach_worktree(self, task_id: str, worktree: str, branch: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            if not con.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone(): raise KeyError(task_id)
            con.execute("UPDATE tasks SET worktree=?,branch=?,updated_at=? WHERE id=?", (worktree, branch, _iso(), task_id))
            self._event(con, task_id, "worktree_attached", {"worktree": worktree, "branch": branch})
        return self.get(task_id)

    def cancel(self, task_id: str, actor: str, reason: str = "") -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            row = con.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row: raise KeyError(task_id)
            if row["state"] in TERMINAL: raise ValueError(f"cannot cancel terminal task {row['state']}")
            con.execute("UPDATE tasks SET state='CANCELLED',lease_owner=NULL,lease_until=NULL,lease_token=NULL,updated_at=? WHERE id=?", (_iso(), task_id))
            self._event(con, task_id, "cancelled", {"actor": actor, "reason": reason})
        return self.get(task_id)

    def record_usage(self, task_id: str, actor: str, role: str, cost_usd: float = 0.0, tokens: int = 0, seconds: float = 0.0, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        if cost_usd < 0 or tokens < 0 or seconds < 0:
            raise ValueError("usage values must be non-negative")
        with self._db() as con:
            if not con.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone(): raise KeyError(task_id)
            con.execute(
                "INSERT INTO task_usage(at,task_id,actor,role,cost_usd,tokens,seconds,metadata) VALUES(?,?,?,?,?,?,?,?)",
                (_iso(), task_id, actor, role, float(cost_usd), int(tokens), float(seconds), json.dumps(metadata or {}, sort_keys=True)),
            )
            self._event(con, task_id, "usage", {"actor": actor, "role": role, "cost_usd": float(cost_usd), "tokens": int(tokens), "seconds": float(seconds)})
        return self.usage(task_id)

    def usage(self, task_id: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            if not con.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone(): raise KeyError(task_id)
            row=con.execute("SELECT COALESCE(SUM(cost_usd),0),COALESCE(SUM(tokens),0),COALESCE(SUM(seconds),0),COUNT(*) FROM task_usage WHERE task_id=?", (task_id,)).fetchone()
            entries=[{**dict(r), "metadata": json.loads(r["metadata"] or "{}")} for r in con.execute("SELECT * FROM task_usage WHERE task_id=? ORDER BY seq", (task_id,)).fetchall()]
        return {"task_id": task_id, "cost_usd": round(float(row[0]), 8), "tokens": int(row[1]), "seconds": round(float(row[2]), 3), "entries": int(row[3]), "records": entries}

    def block(self, task_id: str, actor: str, reason: str) -> dict[str, Any]:
        task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row=con.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row: con.execute("ROLLBACK"); raise KeyError(task_id)
            if "BLOCKED" not in ALLOWED.get(row["state"], set()): con.execute("ROLLBACK"); raise ValueError(f"cannot block from {row['state']}")
            con.execute("UPDATE tasks SET state='BLOCKED',lease_owner=NULL,lease_until=NULL,lease_token=NULL,updated_at=? WHERE id=?", (_iso(), task_id))
            self._event(con, task_id, "blocked", {"actor": actor, "reason": reason})
            con.execute("COMMIT")
        return self.get(task_id)

    def events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        if task_id is not None:
            task_id = safe_identifier(task_id, label="task_id")
        with self._db() as con:
            rows = con.execute("SELECT * FROM events WHERE task_id=? ORDER BY seq", (task_id,)).fetchall() if task_id else con.execute("SELECT * FROM events ORDER BY seq").fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]
