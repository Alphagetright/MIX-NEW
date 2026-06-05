# -*- coding: utf-8 -*-
"""SQLite persistence — sessions, poems, schema, batch runs, checkpoints."""
import json, os, sqlite3, threading, time, uuid

from . import config_loader

_DB = None
_DB_LOCK = threading.Lock()


def _db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state.db")


def _conn():
    global _DB
    if _DB is None:
        with _DB_LOCK:
            if _DB is None:
                _DB = sqlite3.connect(_db_path(), check_same_thread=False)
                _DB.row_factory = sqlite3.Row
                _DB.execute("PRAGMA journal_mode=WAL")
                _DB.execute("PRAGMA synchronous=NORMAL")
                _init_tables(_DB)
    return _DB


def _init_tables(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        name TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS poems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        编号 TEXT, 标题 TEXT, 作者 TEXT, 朝代 TEXT, 原文 TEXT
    );
    CREATE TABLE IF NOT EXISTS schema_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        stage TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS batch_runs (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        generated_prompt TEXT,
        column_mapping TEXT,
        total INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0,
        status TEXT DEFAULT 'running',
        csv_path TEXT,
        json_path TEXT,
        started_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS batch_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES batch_runs(id) ON DELETE CASCADE,
        编号 TEXT, 标题 TEXT, 作者 TEXT,
        result TEXT,
        success INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE INDEX IF NOT EXISTS idx_batch_results_run ON batch_results(run_id);
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'annotator',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS conversation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        poem_no TEXT, poem_title TEXT, poem_author TEXT,
        system_prompt TEXT, user_prompt TEXT,
        raw_response TEXT, parsed_result TEXT,
        model_name TEXT, tokens_used INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_history(session_id);
    """)


# ── Sessions ──

def create_session(name="") -> str:
    sid = uuid.uuid4().hex[:12]
    _conn().execute("INSERT INTO sessions (id, name) VALUES (?, ?)", (sid, name))
    _conn().commit()
    return sid


def list_sessions() -> list:
    rows = _conn().execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_session(sid: str) -> dict | None:
    r = _conn().execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    return dict(r) if r else None


# ── Poems ──

def save_poems(sid: str, poems: list):
    db = _conn()
    db.execute("DELETE FROM poems WHERE session_id=?", (sid,))
    for p in poems:
        db.execute(
            "INSERT INTO poems (session_id, 编号, 标题, 作者, 朝代, 原文) VALUES (?,?,?,?,?,?)",
            (sid, p.get("编号",""), p.get("标题",""), p.get("作者",""),
             p.get("朝代",""), p.get("原文",""))
        )
    db.commit()


def get_poems(sid: str) -> list:
    rows = _conn().execute(
        "SELECT 编号, 标题, 作者, 朝代, 原文 FROM poems WHERE session_id=? ORDER BY id", (sid,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_poem_count(sid: str) -> int:
    return _conn().execute("SELECT COUNT(*) FROM poems WHERE session_id=?", (sid,)).fetchone()[0]


def get_all_poems() -> list:
    """Get poems from ALL sessions — used by corpus browser for a single-user desktop app."""
    rows = _conn().execute(
        "SELECT 编号, 标题, 作者, 朝代, 原文 FROM poems ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_batch_runs() -> list:
    """Get batch runs from ALL sessions."""
    rows = _conn().execute(
        "SELECT * FROM batch_runs ORDER BY started_at DESC"
    ).fetchall()
    runs = []
    for r in rows:
        d = dict(r)
        d["column_mapping"] = json.loads(d["column_mapping"]) if d.get("column_mapping") else []
        runs.append(d)
    return runs


def get_all_conversations(limit: int = 50, offset: int = 0) -> list:
    """Get conversations from ALL sessions."""
    rows = _conn().execute(
        "SELECT id, poem_no, poem_title, poem_author, model_name, tokens_used, created_at FROM conversation_history ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def search_all_conversations(keyword: str, limit: int = 50) -> list:
    """Search conversations across ALL sessions."""
    kw = f"%{keyword}%"
    rows = _conn().execute(
        "SELECT id, poem_no, poem_title, poem_author, model_name, tokens_used, created_at FROM conversation_history WHERE poem_title LIKE ? OR poem_author LIKE ? OR poem_no LIKE ? ORDER BY id DESC LIMIT ?",
        (kw, kw, kw, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def count_all_conversations() -> int:
    return _conn().execute("SELECT COUNT(*) FROM conversation_history").fetchone()[0]


# ── Schema snapshots ──

def save_schema(sid: str, stage: str, data: dict):
    db = _conn()
    db.execute("DELETE FROM schema_snapshots WHERE session_id=? AND stage=?", (sid, stage))
    db.execute("INSERT INTO schema_snapshots (session_id, stage, data) VALUES (?,?,?)",
               (sid, stage, json.dumps(data, ensure_ascii=False)))
    db.commit()


def get_schema(sid: str, stage: str) -> dict | None:
    r = _conn().execute(
        "SELECT data FROM schema_snapshots WHERE session_id=? AND stage=? ORDER BY id DESC LIMIT 1",
        (sid, stage)
    ).fetchone()
    return json.loads(r["data"]) if r else None


# ── Batch runs ──

def create_batch_run(sid: str, generated_prompt: str, column_mapping: list, total: int) -> str:
    rid = uuid.uuid4().hex[:8]
    _conn().execute(
        "INSERT INTO batch_runs (id, session_id, generated_prompt, column_mapping, total) VALUES (?,?,?,?,?)",
        (rid, sid, generated_prompt, json.dumps(column_mapping, ensure_ascii=False), total)
    )
    _conn().commit()
    return rid


def save_batch_result(rid: str, poem: dict, result: dict | None):
    _conn().execute(
        "INSERT INTO batch_results (run_id, 编号, 标题, 作者, result, success) VALUES (?,?,?,?,?,?)",
        (rid, poem.get("编号",""), poem.get("标题",""), poem.get("作者",""),
         json.dumps(result, ensure_ascii=False) if result else None, 1 if result else 0)
    )
    _conn().commit()


def update_batch_progress(rid: str):
    db = _conn()
    completed = db.execute("SELECT COUNT(*) FROM batch_results WHERE run_id=? AND success=1", (rid,)).fetchone()[0]
    failed = db.execute("SELECT COUNT(*) FROM batch_results WHERE run_id=? AND success=0", (rid,)).fetchone()[0]
    db.execute("UPDATE batch_runs SET completed=?, failed=?, status=CASE WHEN ?+?>=total THEN 'completed' ELSE 'running' END, updated_at=datetime('now','localtime') WHERE id=?",
               (completed, failed, completed, failed, rid))
    db.commit()
    return completed, failed


def get_batch_progress(rid: str) -> dict:
    r = _conn().execute("SELECT * FROM batch_runs WHERE id=?", (rid,)).fetchone()
    return dict(r) if r else {}


def get_completed_nos(rid: str) -> set:
    rows = _conn().execute("SELECT 编号 FROM batch_results WHERE run_id=?", (rid,)).fetchall()
    return {r["编号"] for r in rows}


def get_batch_results(rid: str) -> list:
    rows = _conn().execute(
        "SELECT 编号, 标题, 作者, result, success FROM batch_results WHERE run_id=? ORDER BY id", (rid,)
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["result"] = json.loads(d["result"]) if d["result"] else None
        results.append(d)
    return results


def get_batch_run(rid: str) -> dict | None:
    r = _conn().execute("SELECT * FROM batch_runs WHERE id=?", (rid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["column_mapping"] = json.loads(d["column_mapping"]) if d["column_mapping"] else []
    return d


def get_run_csv_path(rid: str) -> str | None:
    r = _conn().execute("SELECT csv_path, json_path FROM batch_runs WHERE id=?", (rid,)).fetchone()
    return r["csv_path"] if r else None


def set_run_export_paths(rid: str, csv_path: str, json_path: str):
    _conn().execute("UPDATE batch_runs SET csv_path=?, json_path=? WHERE id=?", (csv_path, json_path, rid))
    _conn().commit()


# ── Users ──

def create_user(username: str, password_hash: str, role: str = "annotator") -> int | None:
    try:
        db = _conn()
        db.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                   (username, password_hash, role))
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]
    except Exception:
        return None


def get_user(username: str) -> dict | None:
    r = _conn().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(r) if r else None


def get_user_by_id(uid: int) -> dict | None:
    r = _conn().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None


def list_users() -> list:
    rows = _conn().execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# ── Conversation History ──

def save_conversation(sid: str, poem: dict, system_prompt: str, user_prompt: str,
                      raw_response: str, parsed_result: dict, model: str = "", tokens: int = 0):
    _conn().execute(
        "INSERT INTO conversation_history (session_id, poem_no, poem_title, poem_author, system_prompt, user_prompt, raw_response, parsed_result, model_name, tokens_used) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, poem.get("编号",""), poem.get("标题",""), poem.get("作者",""),
         system_prompt, user_prompt, raw_response,
         json.dumps(parsed_result, ensure_ascii=False) if parsed_result else None,
         model, tokens)
    )
    _conn().commit()


def get_conversations(sid: str, limit: int = 50, offset: int = 0) -> list:
    rows = _conn().execute(
        "SELECT id, poem_no, poem_title, poem_author, model_name, tokens_used, created_at FROM conversation_history WHERE session_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
        (sid, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conv_id: int) -> dict | None:
    r = _conn().execute("SELECT * FROM conversation_history WHERE id=?", (conv_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["parsed_result"] = json.loads(d["parsed_result"]) if d.get("parsed_result") else None
    return d


def count_conversations(sid: str) -> int:
    return _conn().execute("SELECT COUNT(*) FROM conversation_history WHERE session_id=?", (sid,)).fetchone()[0]


def search_conversations(sid: str, keyword: str, limit: int = 50) -> list:
    kw = f"%{keyword}%"
    rows = _conn().execute(
        "SELECT id, poem_no, poem_title, poem_author, created_at FROM conversation_history WHERE session_id=? AND (poem_title LIKE ? OR poem_author LIKE ? OR poem_no LIKE ? OR user_prompt LIKE ?) ORDER BY id DESC LIMIT ?",
        (sid, kw, kw, kw, kw, limit)
    ).fetchall()
    return [dict(r) for r in rows]
