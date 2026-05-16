# db.py — K-Transition OS
# Universal DB connection: Turso cloud (via HTTP API) OR local SQLite fallback
# NO libsql-experimental needed — uses only built-in + requests
#
# Setup:
#   pip install requests
#   Add to .env:
#     TURSO_URL=libsql://your-db-name.turso.io   (ya https:// bhi kaam karta hai)
#     TURSO_TOKEN=your-auth-token

import os
import re
import logging

logger = logging.getLogger(__name__)

TURSO_URL   = os.getenv("TURSO_URL", "")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")


# ──────────────────────────────────────────────
# Turso HTTP Client (libsql-experimental ki jagah)
# ──────────────────────────────────────────────

def _turso_http_url(raw_url: str) -> str:
    """libsql:// → https://  convert karo"""
    return re.sub(r"^libsql://", "https://", raw_url)


class _TursoHTTPConnection:
    """
    Turso ke HTTP Pipeline API ko use karke synchronous connection.
    Same interface hai jaise sqlite3 connection — ? params supported.
    Docs: https://docs.turso.tech/sdk/http/reference
    """
    def __init__(self, url: str, token: str):
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        self._base_url = _turso_http_url(url)
        self._pipeline_url = f"{self._base_url}/v2/pipeline"

    def _run(self, sql: str, params=None) -> "_TursoHTTPCursor":
        """Ek SQL statement seedha execute karo (read queries ke liye)."""
        stmt = self._build_stmt(sql, params)
        payload = {"requests": [{"type": "execute", "stmt": stmt}]}
        resp = self._session.post(self._pipeline_url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data["results"][0]
        if result.get("type") == "error":
            raise Exception(f"Turso error: {result['error']['message']}")
        return _TursoHTTPCursor(result["response"]["result"])

    def execute(self, sql: str, params=None) -> "_TursoHTTPCursor":
        try:
            return self._run(sql, params)
        except Exception as e:
            logger.error("Turso execute error: %s | SQL: %.200s", e, sql)
            raise

    @staticmethod
    def _build_stmt(sql: str, params=None) -> dict:
        """? placeholders ko Turso ke named args mein convert karo."""
        stmt: dict = {"sql": sql}
        if params:
            stmt["args"] = [_turso_encode_value(v) for v in params]
        return stmt

    def commit(self):
        pass   # Turso HTTP auto-commits har statement

    def rollback(self):
        pass   # HTTP API mein rollback supported nahi (single stmt auto-commit)

    def close(self):
        try:
            self._session.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _turso_encode_value(v):
    """Python value → Turso HTTP API ka format."""
    if v is None:
        return {"type": "null"}
    elif isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    elif isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    elif isinstance(v, float):
        return {"type": "float", "value": float(v)}
    elif isinstance(v, (bytes, bytearray)):
        import base64
        return {"type": "blob", "base64": base64.b64encode(v).decode()}
    else:
        return {"type": "text", "value": str(v)}


class _TursoHTTPCursor:
    """Turso HTTP response ko sqlite3.Row jaisa interface deta hai."""
    def __init__(self, result: dict):
        cols = [c["name"] for c in result.get("cols", [])]
        rows_raw = result.get("rows", [])
        self._rows = [
            _DictRow(dict(zip(cols, [_turso_decode_value(cell) for cell in row])))
            for row in rows_raw
        ]
        self.lastrowid = result.get("last_insert_rowid")
        self._idx = 0

    def fetchone(self):
        if self._idx >= len(self._rows):
            return None
        row = self._rows[self._idx]
        self._idx += 1
        return row

    def fetchall(self):
        remaining = self._rows[self._idx:]
        self._idx = len(self._rows)
        return remaining


def _turso_decode_value(cell: dict):
    """Turso cell → Python value."""
    t = cell.get("type", "null")
    v = cell.get("value")
    if t == "null" or v is None:
        return None
    elif t == "integer":
        return int(v)
    elif t == "float":
        return float(v)
    elif t == "blob":
        import base64
        return base64.b64decode(cell.get("base64", ""))
    else:
        return v  # text


# ──────────────────────────────────────────────
# Public API — baaki code ke liye same interface
# ──────────────────────────────────────────────

def get_conn():
    """
    Returns a connection object that works identically for both
    Turso (cloud) and SQLite (local dev). Same ? syntax everywhere.
    Usage:
        with get_conn() as conn:
            conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    """
    if TURSO_URL and TURSO_TOKEN:
        try:
            return _TursoHTTPConnection(TURSO_URL, TURSO_TOKEN)
        except ImportError:
            logger.error("requests not installed. Run: pip install requests")
        except Exception as e:
            logger.warning("Turso connection failed, falling back to SQLite: %s", e)

    # Local SQLite fallback
    import sqlite3
    from config import DB_FILE
    raw = sqlite3.connect(str(DB_FILE))
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA journal_mode=WAL")
    raw.execute("PRAGMA busy_timeout=5000")
    return _SQLiteConnection(raw)


def get_backend() -> str:
    return "turso" if (TURSO_URL and TURSO_TOKEN) else "sqlite"


def check_connection() -> bool:
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        return False


# ──────────────────────────────────────────────
# SQLite wrapper (same interface as Turso)
# ──────────────────────────────────────────────

class _SQLiteConnection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=None):
        try:
            cur = self._raw.execute(sql, params) if params else self._raw.execute(sql)
            return _SQLiteCursor(cur)
        except Exception as e:
            logger.error("SQLite execute error: %s | SQL: %.200s", e, sql)
            raise

    def commit(self):
        self._raw.commit()

    def rollback(self):
        try:
            self._raw.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._raw.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


class _SQLiteCursor:
    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = cur.lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


# ──────────────────────────────────────────────
# DictRow — Turso rows ko dict jaisa banata hai
# ──────────────────────────────────────────────

class _DictRow:
    """Dict-like row access — sqlite3.Row ke compatible."""
    def __init__(self, d: dict):
        self._d = d

    def __getitem__(self, key):
        return self._d[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()

    def __contains__(self, key):
        return key in self._d

    def __iter__(self):
        return iter(self._d)

    def __repr__(self):
        return f"DictRow({self._d})"
