from collections.abc import Iterator
import sqlite3

import pytest

from app.database import create_database


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    database = create_database()
    try:
        yield database
    finally:
        database.close()
