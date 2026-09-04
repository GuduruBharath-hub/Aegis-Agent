from dataclasses import fields
import sqlite3

import pytest

from app.database import User, get_user, search_users


def test_schema_has_expected_columns(connection: sqlite3.Connection) -> None:
    columns = connection.execute("PRAGMA table_info(users)").fetchall()
    assert [column["name"] for column in columns] == [
        "id",
        "name",
        "email",
        "password",
    ]


def test_database_contains_six_seed_users(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    assert count["count"] == 6


@pytest.mark.parametrize(
    ("uid", "expected_name"),
    [("1", "Alice Johnson"), ("4", "Bob Singh"), ("6", "José Álvarez")],
)
def test_get_user_returns_seeded_users(
    connection: sqlite3.Connection,
    uid: str,
    expected_name: str,
) -> None:
    user = get_user(uid, connection)
    assert user is not None
    assert user.name == expected_name


@pytest.mark.parametrize("uid", ["0", "99"])
def test_get_user_returns_none_for_unknown_ids(
    connection: sqlite3.Connection,
    uid: str,
) -> None:
    assert get_user(uid, connection) is None


def test_get_user_does_not_expose_password(connection: sqlite3.Connection) -> None:
    user = get_user("1", connection)
    assert user is not None
    assert [field.name for field in fields(user)] == ["id", "name", "email"]


def test_search_partial_match(connection: sqlite3.Connection) -> None:
    results = search_users("ali", connection)
    assert [user.name for user in results] == [
        "Alice Johnson",
        "Alicia Keys",
        "Alina Chen",
    ]


@pytest.mark.parametrize(
    ("term", "expected_id"),
    [("Alice Johnson", 1), ("Bob Singh", 4), ("José Álvarez", 6)],
)
def test_search_exact_name(
    connection: sqlite3.Connection,
    term: str,
    expected_id: int,
) -> None:
    assert [user.id for user in search_users(term, connection)] == [expected_id]


@pytest.mark.parametrize("term", ["Nobody Here", "Zelda Example"])
def test_search_unknown_name_returns_empty(
    connection: sqlite3.Connection,
    term: str,
) -> None:
    assert search_users(term, connection) == []


def test_search_exact_name_is_case_insensitive(
    connection: sqlite3.Connection,
) -> None:
    assert [user.id for user in search_users("ALICE JOHNSON", connection)] == [1]


def test_search_returns_user_values(connection: sqlite3.Connection) -> None:
    assert search_users("Bob Singh", connection) == [
        User(id=4, name="Bob Singh", email="bob@example.test")
    ]


def test_connection_remains_usable_after_search(
    connection: sqlite3.Connection,
) -> None:
    assert search_users("Bob Singh", connection)
    assert connection.execute("SELECT 1").fetchone()[0] == 1


def test_search_works_without_an_explicit_connection() -> None:
    assert [user.id for user in search_users("Bob Singh")] == [4]
