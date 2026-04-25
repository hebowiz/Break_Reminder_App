"""SQLite logging for MVP work sessions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class SQLiteLogger:
    """Persist work session events into SQLite."""

    def __init__(self, db_path: Path | str = Path("data") / "logs.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @property
    def db_path(self) -> Path:
        """Return SQLite DB file path."""
        return self._db_path

    @property
    def data_dir(self) -> Path:
        """Return directory containing the SQLite DB."""
        return self._db_path.parent

    def create_session(self, started_at: str | None = None) -> int:
        """Create a new work session row and return its id."""
        now = self._now_iso()
        work_started_at = started_at or now
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO work_sessions (
                    work_started_at,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?)
                """,
                (work_started_at, now, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def mark_timer_fired(self, session_id: int, fired_at: str | None = None) -> None:
        """Record work timer completion timestamp."""
        now = self._now_iso()
        timer_fired_at = fired_at or now
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE work_sessions
                SET timer_fired_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (timer_fired_at, now, session_id),
            )
            conn.commit()

    def mark_work_resumed(self, session_id: int, resumed_at: str | None = None) -> None:
        """Record resume timestamp after break completion."""
        now = self._now_iso()
        work_resumed_at = resumed_at or now
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE work_sessions
                SET work_resumed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (work_resumed_at, now, session_id),
            )
            conn.commit()

    def end_session(self, session_id: int, end_reason: str, ended_at: str | None = None) -> None:
        """Mark session ended with reason."""
        now = self._now_iso()
        work_ended_at = ended_at or now
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE work_sessions
                SET work_ended_at = ?,
                    end_reason = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (work_ended_at, end_reason, now, session_id),
            )
            conn.commit()

    def get_recent_sessions(self, limit: int = 100) -> list[dict[str, int | str | None]]:
        """Fetch recent work sessions ordered by newest first."""
        safe_limit = max(1, int(limit))
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    id,
                    work_started_at,
                    timer_fired_at,
                    work_resumed_at,
                    work_ended_at,
                    end_reason
                FROM work_sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _initialize_database(self) -> None:
        """Create required table if it does not exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS work_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_started_at TEXT,
                    timer_fired_at TEXT,
                    work_resumed_at TEXT,
                    work_ended_at TEXT,
                    end_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Open SQLite connection."""
        return sqlite3.connect(self._db_path)

    @staticmethod
    def _now_iso() -> str:
        """Return local time in ISO8601 format."""
        return datetime.now().isoformat(timespec="seconds")
