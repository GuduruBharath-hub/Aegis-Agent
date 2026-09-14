from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import TypeAlias


DatabaseTarget: TypeAlias = str | Path


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str


_SEED_USERS = (
    (1, "Alice Johnson", "alice@example.test", "cedar-fox"),
    (2, "Alicia Keys", "alicia@example.test", "violet-lake"),
    (3, "Alina Chen", "alina@example.test", "amber-sky"),
    (4, "Bob Singh", "bob@example.test", "quiet-river"),
    (5, "Patrick O'Brien", "patrick@example.test", "silver-pine"),
    (6, "José Álvarez", "jose@example.test", "winter-sun"),
)


def create_database(target: DatabaseTarget = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(str(target))
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )
    connection.executemany(
        "INSERT INTO users (id, name, email, password) VALUES (?, ?, ?, ?)",
        _SEED_USERS,
    )
    connection.commit()
    return connection


def _to_user(row: sqlite3.Row) -> User:
    return User(id=row["id"], name=row["name"], email=row["email"])


def get_user(
    uid: str,
    connection: sqlite3.Connection | None = None,
) -> User | None:
    owns_connection = connection is None
    active_connection = connection or create_database()
    try:
        row = active_connection.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (uid,),
        ).fetchone()
        return _to_user(row) if row is not None else None
    finally:
        if owns_connection:
            active_connection.close()


def search_users(
    term: str,
    connection: sqlite3.Connection | None = None,
) -> list[User]:
    owns_connection = connection is None
    active_connection = connection or create_database()
    try:
        rows = active_connection.execute(
            "SELECT id, name, email FROM users WHERE name LIKE ? ORDER BY id",
            (f"%{term}%",),
        ).fetchall()
        return [_to_user(row) for row in rows]
    finally:
        if owns_connection:
            active_connection.close()
