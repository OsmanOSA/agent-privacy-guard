"""Bounded per-session count aggregation. No values, body text or full paths.

Hook writes have a 50 ms SQLite lock deadline. Worker takes due batches only;
cooldown applies to suppressed batches too. Stale records are discarded.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEBOUNCE = 2
MAX_WAIT = 10
COOLDOWN = 30
TTL = 120
MAX_SESSIONS = 128


class NotificationQueue:
    def __init__(self, directory: Path):
        self.path = directory / "queue.sqlite"

    @contextmanager
    def _database(self, now):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=0.05)
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS batches "
                       "(session TEXT PRIMARY KEY, first REAL, last REAL, body TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS sent (session TEXT PRIMARY KEY, time REAL)")
            for table, column in (("batches", "last"), ("sent", "time")):
                db.execute(f"DELETE FROM {table} WHERE {column} < ? OR {column} > ?", (now - TTL, now))
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def publish(self, session, origin, summary, now):
        if not isinstance(session, str) or not 1 <= len(session) <= 1024:
            raise ValueError("Invalid notification session")
        key = hashlib.sha256(session.encode("utf-8")).hexdigest()
        record = summary.record()
        with self._database(now) as db:
            row = db.execute("SELECT first, body FROM batches WHERE session=?", (key,)).fetchone()
            first = row[0] if row else now
            body = json.loads(row[1]) if row else {
                "events": 0, "counts": {"pseudonymized": {}, "redacted": {}}, "documents": []}
            body["origin"] = origin
            body["events"] = min(body["events"] + 1, 999999)
            for action, counts in body["counts"].items():
                for category, count in record[action].items():
                    counts[category] = min(counts.get(category, 0) + count, 999999)
            document = record["document"]
            if document and document not in body["documents"] and len(body["documents"]) < 3:
                body["documents"].append(document)
            db.execute("INSERT OR REPLACE INTO batches VALUES (?, ?, ?, ?)",
                       (key, first, now, json.dumps(body, ensure_ascii=False)))
            db.execute("DELETE FROM batches WHERE session IN "
                       "(SELECT session FROM batches ORDER BY last DESC LIMIT -1 OFFSET ?)", (MAX_SESSIONS,))

    def take_due(self, now, limit=MAX_SESSIONS):
        with self._database(now) as db:
            rows = db.execute("SELECT b.session, b.body FROM batches b LEFT JOIN sent s "
                              "ON b.session=s.session WHERE (b.last<=? OR b.first<=?) "
                              "AND (s.time IS NULL OR s.time<=?) ORDER BY b.first LIMIT ?",
                              (now - DEBOUNCE, now - MAX_WAIT, now - COOLDOWN, limit)).fetchall()
            for session, _ in rows:
                db.execute("DELETE FROM batches WHERE session=?", (session,))
                db.execute("INSERT OR REPLACE INTO sent VALUES (?, ?)", (session, now))
            db.execute("DELETE FROM sent WHERE session IN "
                       "(SELECT session FROM sent ORDER BY time DESC LIMIT -1 OFFSET ?)", (MAX_SESSIONS,))
            return [json.loads(body) for _, body in rows]

    def clear(self, now):
        with self._database(now) as db:
            db.execute("DELETE FROM batches")
            db.execute("DELETE FROM sent")
