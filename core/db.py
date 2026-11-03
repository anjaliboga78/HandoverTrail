"""SQLite storage. One small file database, no server needed."""
from __future__ import annotations
import datetime as dt
import os
import sqlite3
import threading
import time
from contextlib import closing

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE, role TEXT);
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY, name TEXT, type TEXT, source_date TEXT, visibility TEXT,
  text TEXT, redaction_count INTEGER DEFAULT 0, extracted INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS redactions(
  id INTEGER PRIMARY KEY, source_id INTEGER, tag TEXT, preview TEXT);
CREATE TABLE IF NOT EXISTS items(
  id INTEGER PRIMARY KEY, source_id INTEGER, type TEXT, text TEXT, owner TEXT, quote TEXT,
  topic TEXT, confidence REAL, verify_status TEXT, verify_score REAL DEFAULT 0,
  flag TEXT DEFAULT '', is_conflict INTEGER DEFAULT 0, is_gap INTEGER DEFAULT 0,
  is_recurring INTEGER DEFAULT 0, conflict_with TEXT DEFAULT '[]', review_status TEXT DEFAULT 'pending', visibility TEXT,
  item_date TEXT, extractor TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS item_versions(
  id INTEGER PRIMARY KEY, item_id INTEGER, action TEXT, old_text TEXT, new_text TEXT,
  changed_by TEXT, changed_at TEXT);
CREATE TABLE IF NOT EXISTS handovers(
  id INTEGER PRIMARY KEY, version INTEGER, status TEXT, approved_by TEXT,
  approved_at TEXT, snapshot TEXT);
CREATE TABLE IF NOT EXISTS acks(
  id INTEGER PRIMARY KEY, handover_id INTEGER, user_name TEXT, acknowledged_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY, user_name TEXT, action TEXT, target TEXT, detail TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS prefs(
  user_name TEXT, key TEXT, value TEXT, PRIMARY KEY(user_name, key));
CREATE TABLE IF NOT EXISTS checklist(
  id INTEGER PRIMARY KEY, person TEXT, section TEXT, ref TEXT, label TEXT, custom INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0, done_by TEXT, done_at TEXT, note TEXT DEFAULT '', created_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY, author TEXT, body TEXT, kind TEXT DEFAULT 'todo', color TEXT DEFAULT 'yellow',
  link_item_id INTEGER, visibility TEXT DEFAULT 'me', remind_on TEXT, pinned INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0, promoted_item_id INTEGER, created_at TEXT, updated_at TEXT);
"""

DEFAULT_USERS = [("Riya", "Lead"), ("Karan", "Core"), ("Meera", "Core"), ("Aman", "Intern")]


TRANSFER_SCHEMA = """
CREATE TABLE IF NOT EXISTS transfers(
  id INTEGER PRIMARY KEY, item_id INTEGER, from_owner TEXT, to_owner TEXT, status TEXT, reason TEXT,
  proposed_by TEXT, proposed_at TEXT, decided_by TEXT, decided_at TEXT, completed_by TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS transfer_events(
  id INTEGER PRIMARY KEY, transfer_id INTEGER, event TEXT, by_user TEXT, at TEXT, note TEXT);
"""


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


_local = threading.local()


def use_path(path) -> None:
    """Point this thread at a different database file (used for per-visitor workspaces)."""
    _local.path = path


def current_path() -> str:
    return getattr(_local, "path", None) or config.DB_PATH


def cleanup_workspaces(folder: str, max_age_hours: float = 24) -> int:
    """Delete workspace databases that have not been touched for a while."""
    if not os.path.isdir(folder):
        return 0
    n = 0
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        if f.endswith(".db") and time.time() - os.path.getmtime(p) > max_age_hours * 3600:
            try:
                os.remove(p)
                n += 1
            except OSError:
                pass
    return n


def connect() -> sqlite3.Connection:
    path = current_path()
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    c = sqlite3.connect(path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with closing(connect()) as c:
        c.executescript(SCHEMA)
        c.executescript(TRANSFER_SCHEMA)
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.executemany("INSERT INTO users(name, role) VALUES (?, ?)", DEFAULT_USERS)
        c.commit()


def q(sql: str, params: tuple = ()) -> list:
    with closing(connect()) as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql: str, params: tuple = ()):
    rows = q(sql, params)
    return rows[0] if rows else None


def x(sql: str, params: tuple = ()) -> int:
    with closing(connect()) as c:
        cur = c.execute(sql, params)
        c.commit()
        return cur.lastrowid


def reset_all() -> None:
    """Delete everything and start fresh (demo reset)."""
    with closing(connect()) as c:
        for t in ("acks", "handovers", "item_versions", "items", "redactions", "sources", "audit_log", "notes", "transfers", "transfer_events", "checklist"):
            c.execute(f"DELETE FROM {t}")
        c.commit()


def log(user: str, action: str, target: str = "", detail: str = "") -> None:
    x("INSERT INTO audit_log(user_name, action, target, detail, at) VALUES (?,?,?,?,?)",
      (user, action, target, detail, now()))
