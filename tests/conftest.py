"""Test fixtures — isolated temp DB for every test, no TUI."""
import os
import sys
import tempfile

import pytest

# Ensure project root is on sys.path so 'import db' / 'import data.*' work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db  # noqa: E402


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """Provide a fresh, seeded database for every test.

    Sets db._db_path_override to a temp file so all data modules
    automatically use the test DB via get_connection().
    """
    db_file = str(tmp_path / "test_northwind.db")
    db._db_path_override = db_file

    db.create_tables()
    db.seed_data()
    db._seed_settings()
    db._seed_users()

    yield db_file

    db._db_path_override = None
