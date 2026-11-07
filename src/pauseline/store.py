"""SQLite persistence: payees, transfers, timeline events, and app settings."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from statistics import median

SCHEMA = """
CREATE TABLE IF NOT EXISTS payees (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    relationship TEXT NOT NULL DEFAULT '',
    known INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    payee_id TEXT NOT NULL REFERENCES payees(id),
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    statement TEXT NOT NULL DEFAULT '',
    hour_of_day INTEGER,
    status TEXT NOT NULL,
    decision TEXT,
    risk REAL,
    scam_type TEXT,
    assessment TEXT,
    answers TEXT NOT NULL DEFAULT '{}',
    asked TEXT NOT NULL DEFAULT '[]',
    order_id TEXT,
    authorization_id TEXT,
    capture_id TEXT,
    payout_batch_id TEXT,
    release_at REAL,
    family_decision TEXT,
    family_note TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_id TEXT,
    at REAL NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS past_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

TRANSFER_JSON_FIELDS = {"assessment", "answers", "asked"}


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

    # -- helpers ------------------------------------------------------------
    def _exec(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, params)
            self._db.commit()
            return cur

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._db.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def reset(self) -> None:
        """Wipe all demo data (payees, payments, timeline, settings)."""
        with self._lock:
            for table in ("events", "transfers", "payees", "past_payments", "settings"):
                self._db.execute(f"DELETE FROM {table}")
            self._db.commit()

    # -- settings -----------------------------------------------------------
    def get_setting(self, key: str, default: str = "") -> str:
        row = self._one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._exec(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    # -- payees -------------------------------------------------------------
    def add_payee(self, name: str, email: str = "", relationship: str = "", known: bool = False, blocked: bool = False) -> dict:
        pid = uuid.uuid4().hex[:10]
        self._exec(
            "INSERT INTO payees(id, name, email, relationship, known, blocked) VALUES(?,?,?,?,?,?)",
            (pid, name, email, relationship, int(known), int(blocked)),
        )
        return self.get_payee(pid)  # type: ignore[return-value]

    def get_payee(self, pid: str) -> dict | None:
        row = self._one("SELECT * FROM payees WHERE id = ?", (pid,))
        if row:
            row["known"], row["blocked"] = bool(row["known"]), bool(row["blocked"])
        return row

    def find_payee_by_name(self, name: str) -> dict | None:
        row = self._one("SELECT id FROM payees WHERE lower(name) = lower(?)", (name.strip(),))
        return self.get_payee(row["id"]) if row else None

    def list_payees(self) -> list[dict]:
        rows = self._all("SELECT * FROM payees ORDER BY known DESC, name")
        for r in rows:
            r["known"], r["blocked"] = bool(r["known"]), bool(r["blocked"])
        return rows

    def update_payee(self, pid: str, **fields) -> None:
        allowed = {"name", "email", "relationship", "known", "blocked"}
        sets = {k: (int(v) if isinstance(v, bool) else v) for k, v in fields.items() if k in allowed}
        if sets:
            cols = ", ".join(f"{k} = :{k}" for k in sets)
            self._exec(f"UPDATE payees SET {cols} WHERE id = :id", {**sets, "id": pid})

    # -- payment history ----------------------------------------------------
    def add_past_payment(self, amount: float, at: float | None = None) -> None:
        self._exec("INSERT INTO past_payments(amount, at) VALUES(?, ?)", (amount, at or time.time()))

    def history_median(self) -> float | None:
        amounts = [r["amount"] for r in self._all("SELECT amount FROM past_payments")]
        return float(median(amounts)) if amounts else None

    def recent_count(self, seconds: float = 3600) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM transfers WHERE created_at >= ? AND status != 'draft'",
            (time.time() - seconds,),
        )
        return int(row["n"]) if row else 0

    # -- transfers ----------------------------------------------------------
    def create_transfer(self, **fields) -> dict:
        tid = uuid.uuid4().hex[:12]
        now = time.time()
        data = {"id": tid, "created_at": now, "updated_at": now, **fields}
        for k in TRANSFER_JSON_FIELDS & data.keys():
            data[k] = json.dumps(data[k], ensure_ascii=False)
        cols = ", ".join(data)
        marks = ", ".join(f":{k}" for k in data)
        self._exec(f"INSERT INTO transfers({cols}) VALUES({marks})", data)
        return self.get_transfer(tid)  # type: ignore[return-value]

    def update_transfer(self, tid: str, **fields) -> dict:
        fields["updated_at"] = time.time()
        for k in TRANSFER_JSON_FIELDS & fields.keys():
            fields[k] = json.dumps(fields[k], ensure_ascii=False)
        cols = ", ".join(f"{k} = :{k}" for k in fields)
        self._exec(f"UPDATE transfers SET {cols} WHERE id = :id", {**fields, "id": tid})
        return self.get_transfer(tid)  # type: ignore[return-value]

    def _decode(self, row: dict) -> dict:
        for k in TRANSFER_JSON_FIELDS:
            if row.get(k):
                row[k] = json.loads(row[k])
        return row

    def get_transfer(self, tid: str) -> dict | None:
        row = self._one("SELECT * FROM transfers WHERE id = ?", (tid,))
        return self._decode(row) if row else None

    def find_transfer_by_order(self, order_id: str) -> dict | None:
        row = self._one("SELECT * FROM transfers WHERE order_id = ?", (order_id,))
        return self._decode(row) if row else None

    def find_transfer_by_authorization(self, auth_id: str) -> dict | None:
        row = self._one("SELECT * FROM transfers WHERE authorization_id = ?", (auth_id,))
        return self._decode(row) if row else None

    def list_transfers(self, limit: int = 50) -> list[dict]:
        return [self._decode(r) for r in self._all("SELECT * FROM transfers ORDER BY created_at DESC LIMIT ?", (limit,))]

    def due_for_release(self, now: float | None = None) -> list[dict]:
        rows = self._all(
            "SELECT * FROM transfers WHERE status = 'held' AND decision = 'cool_off' "
            "AND release_at IS NOT NULL AND release_at <= ? AND family_decision IS NULL",
            (now or time.time(),),
        )
        return [self._decode(r) for r in rows]

    # -- events -------------------------------------------------------------
    def log(self, transfer_id: str | None, kind: str, detail: str | dict = "") -> None:
        if isinstance(detail, dict):
            detail = json.dumps(detail, ensure_ascii=False)
        self._exec("INSERT INTO events(transfer_id, at, kind, detail) VALUES(?,?,?,?)", (transfer_id, time.time(), kind, detail))

    def events(self, transfer_id: str | None = None, limit: int = 200) -> list[dict]:
        if transfer_id:
            return self._all("SELECT * FROM events WHERE transfer_id = ? ORDER BY id DESC LIMIT ?", (transfer_id, limit))
        return self._all("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
