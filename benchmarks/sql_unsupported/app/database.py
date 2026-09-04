from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    name: str


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    connection.executemany(
        "INSERT INTO items (id, name) VALUES (?, ?)",
        ((2, "Beta"), (1, "Gamma"), (3, "Alpha")),
    )
    return connection


def order_items(column: str) -> list[Item]:
    connection = create_database()
    try:
        rows = connection.execute(
            "SELECT id, name FROM items ORDER BY " + column
        ).fetchall()
        return [Item(row["id"], row["name"]) for row in rows]
    finally:
        connection.close()
