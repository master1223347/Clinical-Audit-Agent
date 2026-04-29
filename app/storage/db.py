"""SQLite connection helper — pilot.md §6.1.7.

All repository code must use _connect(). Direct sqlite3.connect() calls are
forbidden in app/storage/ to ensure PRAGMA foreign_keys = ON is always set.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def _connect(path: str) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with FK enforcement; commit on success, always close."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
