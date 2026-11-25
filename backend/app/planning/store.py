"""SQLite on an operator-provided durable volume. Each transaction opens its own connection."""

import secrets
import sqlite3
import time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from app.config import settings


@contextmanager
def connection():
    directory = Path(settings.storage_dir)
    if settings.environment == "production" and not directory.is_absolute():
        raise RuntimeError("Set STORAGE_DIR to the persistent volume mount")
    directory.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(directory / "planner.sqlite3", timeout=5)
    try:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, owner TEXT, result TEXT, trace TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS quota (bucket INTEGER, subject TEXT, n INTEGER, PRIMARY KEY(bucket,subject))"
            )
            yield conn
    finally:
        conn.close()


def digest(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def admit(subject: str) -> bool:
    bucket = int(time.time()) // 3600
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM quota WHERE bucket < ?", (bucket,))
        for key, limit in (
            ("global", settings.hourly_global_limit),
            (digest(subject), settings.hourly_client_limit),
        ):
            row = db.execute(
                "SELECT n FROM quota WHERE subject=? AND bucket=?", (key, bucket)
            ).fetchone()
            if row and row[0] >= limit:
                return False
        for key in ("global", digest(subject)):
            db.execute(
                "INSERT INTO quota VALUES (?,?,1) ON CONFLICT(bucket,subject) DO UPDATE SET n=n+1",
                (bucket, key),
            )
    return True


def save(result, state):
    token = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute(
            "INSERT INTO plans VALUES (?,?,?,?)",
            (
                state.trip_id,
                digest(token),
                result.model_dump_json(exclude={"access_token"}),
                state.model_dump_json(
                    include={"trip_id", "events", "refinements", "evidence"}
                ),
            ),
        )
    return token


def read(trip_id: str, token: str, trace: bool):
    with connection() as db:
        row = db.execute(
            "SELECT result,trace FROM plans WHERE id=? AND owner=?",
            (trip_id, digest(token)),
        ).fetchone()
    return row[int(trace)] if row else None
