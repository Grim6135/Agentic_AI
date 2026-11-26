"""Transactional trip storage using PostgreSQL or a local SQLite volume."""

import secrets
import sqlite3
import time
import os
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from app.config import settings


def initialize(db):
    db.execute(
        "CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, owner TEXT, result TEXT, trace TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS quota (bucket INTEGER, subject TEXT, n INTEGER, PRIMARY KEY(bucket,subject))"
    )


def execute(db, statement, parameters):
    # Both drivers bind values separately. Only their placeholder syntax differs.
    if not isinstance(db, sqlite3.Connection):
        statement = statement.replace("?", "%s")
    return db.execute(statement, parameters)


@contextmanager
def connection():
    url = settings.database_url.get_secret_value()
    if url:
        import psycopg

        with psycopg.connect(url, connect_timeout=5) as db:
            tables = db.execute("SELECT to_regclass('plans'), to_regclass('quota')").fetchone()
            if None in tables:
                db.execute("SELECT pg_advisory_xact_lock(722906101)")
                initialize(db)
            yield db
        return
    if os.getenv("VERCEL") == "1" or settings.research_service_url:
        raise RuntimeError("Connect a PostgreSQL database and set DATABASE_URL")
    directory = Path(settings.storage_dir)
    if settings.environment == "production" and not directory.is_absolute():
        raise RuntimeError("Set STORAGE_DIR to the persistent volume mount")
    directory.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(directory / "planner.sqlite3", timeout=5)
    try:
        with conn:
            initialize(conn)
            yield conn
    finally:
        conn.close()


def digest(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def admit(subject: str) -> bool:
    bucket = int(time.time()) // 3600
    with connection() as db:
        if isinstance(db, sqlite3.Connection):
            db.execute("BEGIN IMMEDIATE")
        else:
            db.execute("SELECT pg_advisory_xact_lock(722906102)")
        execute(db, "DELETE FROM quota WHERE bucket < ?", (bucket,))
        for key, limit in (
            ("global", settings.hourly_global_limit),
            (digest(subject), settings.hourly_client_limit),
        ):
            row = execute(db,
                "SELECT n FROM quota WHERE subject=? AND bucket=?", (key, bucket)
            ).fetchone()
            if row and row[0] >= limit:
                return False
        for key in ("global", digest(subject)):
            execute(db,
                "INSERT INTO quota VALUES (?,?,1) ON CONFLICT(bucket,subject) DO UPDATE SET n=quota.n+1",
                (bucket, key),
            )
    return True


def save(result, state):
    token = secrets.token_urlsafe(32)
    with connection() as db:
        execute(db,
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
        row = execute(db,
            "SELECT result,trace FROM plans WHERE id=? AND owner=?",
            (trip_id, digest(token)),
        ).fetchone()
    return row[int(trace)] if row else None
