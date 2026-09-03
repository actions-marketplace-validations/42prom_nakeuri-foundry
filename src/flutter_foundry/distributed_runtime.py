from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .execution_fabric import RISK_ORDER
from .safe_paths import safe_identifier


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


@dataclass(frozen=True)
class WorkerCapability:
    worker_id: str
    host: str
    providers: tuple[str, ...]
    platforms: tuple[str, ...]
    max_risk: str
    cpu_slots: int = 1
    labels: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkerRegistry:
    """Transactional worker registry and placement/reservation model.

    SQLite/WAL gives one-node durable atomic placement and is safe for multiple
    worker processes on the same shared filesystem. The contract deliberately
    separates registry semantics from storage so a deployment can replace this
    backend with Postgres/etcd without changing Foundry placement rules.

    It is *not* advertised as multi-region HA; distributed/HA deployments must
    use an external transactional registry implementation.
    """

    SCHEMA_VERSION = 2

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / ".factory" / "orchestration" / "workers.db"
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

    def _init(self) -> None:
        with self._db() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS workers(
                  worker_id TEXT PRIMARY KEY,
                  host TEXT NOT NULL,
                  providers TEXT NOT NULL,
                  platforms TEXT NOT NULL,
                  max_risk TEXT NOT NULL,
                  cpu_slots INTEGER NOT NULL,
                  labels TEXT NOT NULL,
                  heartbeat_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  generation INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS reservations(
                  reservation_id TEXT PRIMARY KEY,
                  worker_id TEXT NOT NULL REFERENCES workers(worker_id) ON DELETE CASCADE,
                  task_id TEXT,
                  provider TEXT,
                  platform TEXT,
                  risk TEXT NOT NULL,
                  slots INTEGER NOT NULL DEFAULT 1,
                  owner TEXT,
                  created_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  released_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_worker_expiry ON workers(expires_at);
                CREATE INDEX IF NOT EXISTS idx_res_worker_active ON reservations(worker_id, released_at, expires_at);
                CREATE TABLE IF NOT EXISTS registry_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """
            )
            con.execute(
                "INSERT INTO registry_meta(key,value) VALUES('schema_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(self.SCHEMA_VERSION),),
            )

    @staticmethod
    def _csv(values: tuple[str, ...] | list[str]) -> str:
        return ",".join(sorted({str(x).strip() for x in values if str(x).strip()}))

    @staticmethod
    def _split(value: str) -> list[str]:
        return [x for x in str(value or "").split(",") if x]

    def _worker_dict(self, row: sqlite3.Row, *, now: datetime | None = None, con: sqlite3.Connection | None = None) -> dict[str, Any]:
        now = now or _now()
        owned = False
        if con is None:
            con = sqlite3.connect(self.path)
            con.row_factory = sqlite3.Row
            owned = True
        try:
            busy = con.execute(
                "SELECT COALESCE(SUM(slots),0) FROM reservations WHERE worker_id=? AND released_at IS NULL AND expires_at>?",
                (row["worker_id"], _iso(now)),
            ).fetchone()[0]
            return {
                "worker_id": row["worker_id"],
                "host": row["host"],
                "providers": self._split(row["providers"]),
                "platforms": self._split(row["platforms"]),
                "max_risk": row["max_risk"],
                "cpu_slots": int(row["cpu_slots"]),
                "labels": self._split(row["labels"]),
                "heartbeat_at": row["heartbeat_at"],
                "expires_at": row["expires_at"],
                "generation": int(row["generation"]),
                "busy_slots": int(busy or 0),
            }
        finally:
            if owned:
                con.close()

    def schema_status(self) -> dict[str, Any]:
        with self._db() as con:
            value = con.execute("SELECT value FROM registry_meta WHERE key='schema_version'").fetchone()
            version = int(value[0]) if value else 0
            quick = [str(r[0]) for r in con.execute("PRAGMA quick_check").fetchall()]
        return {
            "status": "pass" if version == self.SCHEMA_VERSION and quick == ["ok"] else "fail",
            "version": version,
            "expected": self.SCHEMA_VERSION,
            "quick_check": quick,
            "backend": "sqlite-wal",
            "ha_claim": False,
        }

    def register(self, capability: WorkerCapability, ttl_seconds: int = 60) -> dict[str, Any]:
        worker_id = safe_identifier(capability.worker_id, label="worker_id")
        if capability.max_risk not in RISK_ORDER:
            raise ValueError("invalid max_risk")
        if capability.cpu_slots < 1:
            raise ValueError("cpu_slots must be >= 1")
        now = _now()
        expires = _iso(now + timedelta(seconds=max(5, ttl_seconds)))
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            previous = con.execute("SELECT generation FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
            generation = int(previous[0]) + 1 if previous else 1
            con.execute(
                """INSERT INTO workers(worker_id,host,providers,platforms,max_risk,cpu_slots,labels,heartbeat_at,expires_at,generation)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(worker_id) DO UPDATE SET
                     host=excluded.host,providers=excluded.providers,platforms=excluded.platforms,max_risk=excluded.max_risk,
                     cpu_slots=excluded.cpu_slots,labels=excluded.labels,heartbeat_at=excluded.heartbeat_at,
                     expires_at=excluded.expires_at,generation=excluded.generation""",
                (
                    worker_id,
                    capability.host,
                    self._csv(capability.providers),
                    self._csv(capability.platforms),
                    capability.max_risk,
                    int(capability.cpu_slots),
                    self._csv(capability.labels),
                    _iso(now),
                    expires,
                    generation,
                ),
            )
            row = con.execute("SELECT * FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
            out = self._worker_dict(row, now=now, con=con)
            con.execute("COMMIT")
        return out

    def heartbeat(self, worker_id: str, ttl_seconds: int = 60) -> dict[str, Any]:
        worker_id = safe_identifier(worker_id, label="worker_id")
        now = _now()
        with self._db() as con:
            cur = con.execute(
                "UPDATE workers SET heartbeat_at=?,expires_at=? WHERE worker_id=?",
                (_iso(now), _iso(now + timedelta(seconds=max(5, ttl_seconds))), worker_id),
            )
            if cur.rowcount != 1:
                return {"status": "missing"}
        return {"status": "pass", "worker_id": worker_id}

    def recover_expired_reservations(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or _now()
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute(
                "SELECT reservation_id FROM reservations WHERE released_at IS NULL AND expires_at<=?",
                (_iso(now),),
            ).fetchall()
            if rows:
                con.execute(
                    "UPDATE reservations SET released_at=? WHERE released_at IS NULL AND expires_at<=?",
                    (_iso(now), _iso(now)),
                )
            con.execute("COMMIT")
        return {"status": "pass", "recovered": len(rows), "reservations": [r[0] for r in rows]}

    def eligible(
        self,
        *,
        risk: str,
        platform: str | None = None,
        provider: str | None = None,
        now: datetime | None = None,
        slots: int = 1,
        labels: tuple[str, ...] | list[str] = (),
    ) -> list[dict[str, Any]]:
        risk = risk.upper()
        if risk not in RISK_ORDER:
            raise ValueError("invalid risk")
        if slots < 1:
            raise ValueError("slots must be >= 1")
        required_labels = set(labels)
        now = now or _now()
        out: list[dict[str, Any]] = []
        with self._db() as con:
            rows = con.execute("SELECT * FROM workers WHERE expires_at>? ORDER BY worker_id", (_iso(now),)).fetchall()
            for row in rows:
                w = self._worker_dict(row, now=now, con=con)
                if RISK_ORDER[risk] > RISK_ORDER.get(w.get("max_risk", "LOW"), -1):
                    continue
                if platform and platform not in w["platforms"]:
                    continue
                if provider and provider not in w["providers"]:
                    continue
                if required_labels and not required_labels.issubset(set(w["labels"])):
                    continue
                if w["busy_slots"] + slots > w["cpu_slots"]:
                    continue
                out.append(w)
        return sorted(out, key=lambda x: (x["busy_slots"] / max(1, x["cpu_slots"]), x["busy_slots"], x["worker_id"]))

    def select(self, **requirements: Any) -> dict[str, Any]:
        eligible = self.eligible(**requirements)
        return {"status": "pass", "worker": eligible[0]} if eligible else {"status": "blocked", "reason": "no eligible worker", "requirements": requirements}

    def reserve(
        self,
        *,
        risk: str,
        platform: str | None = None,
        provider: str | None = None,
        task_id: str | None = None,
        owner: str | None = None,
        slots: int = 1,
        ttl_seconds: int = 900,
        labels: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        """Atomically select a worker and reserve capacity.

        Multiple schedulers/processes can race safely: BEGIN IMMEDIATE serializes
        the select+reserve decision, so one CPU slot cannot be double-booked.
        """
        risk = risk.upper()
        if risk not in RISK_ORDER:
            raise ValueError("invalid risk")
        if task_id is not None:
            task_id = safe_identifier(task_id, label="task_id")
        if slots < 1:
            raise ValueError("slots must be >= 1")
        now = _now()
        expires = _iso(now + timedelta(seconds=max(30, ttl_seconds)))
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE reservations SET released_at=? WHERE released_at IS NULL AND expires_at<=?",
                (_iso(now), _iso(now)),
            )
            rows = con.execute("SELECT * FROM workers WHERE expires_at>? ORDER BY worker_id", (_iso(now),)).fetchall()
            candidates: list[tuple[float, int, str, sqlite3.Row, dict[str, Any]]] = []
            required_labels = set(labels)
            for row in rows:
                w = self._worker_dict(row, now=now, con=con)
                if RISK_ORDER[risk] > RISK_ORDER.get(w["max_risk"], -1):
                    continue
                if platform and platform not in w["platforms"]:
                    continue
                if provider and provider not in w["providers"]:
                    continue
                if required_labels and not required_labels.issubset(set(w["labels"])):
                    continue
                if w["busy_slots"] + slots > w["cpu_slots"]:
                    continue
                candidates.append((w["busy_slots"] / max(1, w["cpu_slots"]), w["busy_slots"], w["worker_id"], row, w))
            if not candidates:
                con.execute("COMMIT")
                return {"status": "blocked", "reason": "no eligible worker capacity", "requirements": {"risk": risk, "platform": platform, "provider": provider, "slots": slots}}
            _, _, _, row, worker = sorted(candidates, key=lambda x: x[:3])[0]
            reservation_id = f"RSV-{uuid.uuid4().hex[:16].upper()}"
            con.execute(
                """INSERT INTO reservations(reservation_id,worker_id,task_id,provider,platform,risk,slots,owner,created_at,expires_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (reservation_id, row["worker_id"], task_id, provider, platform, risk, slots, owner, _iso(now), expires),
            )
            worker["busy_slots"] += slots
            con.execute("COMMIT")
        return {
            "status": "pass",
            "reservation_id": reservation_id,
            "worker": worker,
            "expires_at": expires,
            "task_id": task_id,
            "slots": slots,
        }

    def release(self, reservation_id: str, *, owner: str | None = None) -> dict[str, Any]:
        reservation_id = safe_identifier(reservation_id, label="reservation_id")
        with self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM reservations WHERE reservation_id=?", (reservation_id,)).fetchone()
            if not row:
                con.execute("ROLLBACK")
                return {"status": "missing", "reservation_id": reservation_id}
            if owner is not None and row["owner"] not in {None, owner}:
                con.execute("ROLLBACK")
                return {"status": "blocked", "reason": "reservation owner mismatch", "reservation_id": reservation_id}
            if row["released_at"] is None:
                con.execute("UPDATE reservations SET released_at=? WHERE reservation_id=?", (_iso(), reservation_id))
            con.execute("COMMIT")
        return {"status": "pass", "reservation_id": reservation_id}

    def status(self) -> dict[str, Any]:
        now = _now()
        with self._db() as con:
            workers = [self._worker_dict(r, now=now, con=con) for r in con.execute("SELECT * FROM workers ORDER BY worker_id")]
            active = [dict(r) for r in con.execute("SELECT * FROM reservations WHERE released_at IS NULL AND expires_at>? ORDER BY created_at", (_iso(now),))]
        return {
            "status": "pass",
            "schema": "nakeuri/worker-registry/v2",
            "backend": "sqlite-wal",
            "high_availability": False,
            "workers": workers,
            "active_reservations": active,
            "schema_status": self.schema_status(),
        }
