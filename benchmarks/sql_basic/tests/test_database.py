from dataclasses import FrozenInstanceError, fields
import sqlite3

import pytest

from app.database import User, get_user


def test_schema_has_expected_columns(connection: sqlite3.Connection) -> None:
    columns = connection.execute("PRAGMA table_info(users)").fetchall()
    assert [column["name"] for column in columns] == [
        "id",
        "name",
        "email",
        "password",
    ]


def test_database_contains_five_seed_users(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    assert count["count"] == 5


@pytest.mark.parametrize(
    ("uid", "expected_name"),
    [
        ("1", "Alice Johnson"),
        ("2", "Bob Singh"),
        ("3", "Charlie Chen"),
        ("4", "Patrick O'Brien"),
        ("5", "José Álvarez"),
    ],
)
def test_get_user_returns_each_seeded_user(
    connection: sqlite3.Connection,
    uid: str,
    expected_name: str,
) -> None:
    user = get_user(uid, connection)
    assert user is not None
    assert user.name == expected_name


@pytest.mark.parametrize("uid", ["0", "99", "not-a-number"])
def test_get_user_returns_none_for_unknown_ids(
    connection: sqlite3.Connection,
    uid: str,
) -> None:
    assert get_user(uid, connection) is None


def test_user_is_an_immutable_value(connection: sqlite3.Connection) -> None:
    user = get_user("1", connection)
    assert user is not None
    with pytest.raises(FrozenInstanceError):
        user.name = "Changed"  # type: ignore[misc]


def test_user_exposes_only_public_fields(connection: sqlite3.Connection) -> None:
    user = get_user("1", connection)
    assert user is not None
    assert [field.name for field in fields(user)] == ["id", "name", "email"]


def test_lookup_does_not_return_password(connection: sqlite3.Connection) -> None:
    user = get_user("2", connection)
    assert user is not None
    assert not hasattr(user, "password")


def test_apostrophe_in_stored_name_is_preserved(
    connection: sqlite3.Connection,
) -> None:
    user = get_user("4", connection)
    assert user is not None
    assert user.name == "Patrick O'Brien"


def test_unicode_in_stored_user_is_preserved(
    connection: sqlite3.Connection,
) -> None:
    user = get_user("5", connection)
    assert user is not None
    assert user.name == "José Álvarez"


def test_connection_remains_usable_after_lookup(
    connection: sqlite3.Connection,
) -> None:
    assert get_user("1", connection) is not None
    assert connection.execute("SELECT 1").fetchone()[0] == 1


def test_get_user_works_without_an_explicit_connection() -> None:
    assert get_user("3") == User(
        id=3,
        name="Charlie Chen",
        email="charlie@example.test",
    )


def test_repeated_lookups_return_independent_values(
    connection: sqlite3.Connection,
) -> None:
    first = get_user("1", connection)
    second = get_user("1", connection)
    assert first == second
    assert first is not second
