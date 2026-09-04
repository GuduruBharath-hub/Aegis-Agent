from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.storage.repositories import (
    ArtifactRepo,
    AttemptRepo,
    EventRepo,
    FindingRepo,
    JobRepo,
    apply_pragmas,
    get_journal_mode,
    is_foreign_keys_enabled,
    run_migrations,
)


class Database:
    """Manages SQLite database connection lifecycle, PRAGMAs, and schema migrations.

    All SQL statements are strictly confined to backend/storage/repositories.py.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection with WAL mode and foreign keys enabled."""
        # FastAPI's test/server boundaries may create the app and serve it on
        # different threads; repository writes remain serialized by the runtime.
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        apply_pragmas(conn)
        return conn

    def init_db(self) -> sqlite3.Connection:
        """Connect to the database and run all pending schema migrations."""
        conn = self.connect()
        run_migrations(conn)
        return conn

    def check_wal(self, conn: sqlite3.Connection) -> str:
        """Query the active journal mode via repository helper."""
        return get_journal_mode(conn)

    def check_foreign_keys(self, conn: sqlite3.Connection) -> bool:
        """Query foreign keys enforcement status via repository helper."""
        return is_foreign_keys_enabled(conn)

    def jobs(self, conn: sqlite3.Connection) -> JobRepo:
        """Return a JobRepo bound to the given connection."""
        return JobRepo(conn)

    def attempts(self, conn: sqlite3.Connection) -> AttemptRepo:
        """Return an AttemptRepo bound to the given connection."""
        return AttemptRepo(conn)

    def events(self, conn: sqlite3.Connection) -> EventRepo:
        """Return an EventRepo bound to the given connection."""
        return EventRepo(conn)

    def artifacts(self, conn: sqlite3.Connection) -> ArtifactRepo:
        """Return an ArtifactRepo bound to the given connection."""
        return ArtifactRepo(conn)

    def findings(self, conn: sqlite3.Connection) -> FindingRepo:
        """Return a FindingRepo bound to the given connection."""
        return FindingRepo(conn)
