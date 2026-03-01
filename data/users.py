"""data/users.py — CRUD for the AppUsers table + PIN authentication.

Educational patterns:
- hashlib.sha256 for one-way PIN hashing (no plain-text stored)
- Conditional UPDATE (change PIN only when a new one is supplied)
- Standard CRUD pattern matching all other data/*.py modules
- Hierarchical RBAC: admin > manager > user
"""
from __future__ import annotations  # enables X | Y union syntax on Python 3.9

import hashlib
from datetime import datetime
from db import get_connection

# ── Role hierarchy ────────────────────────────────────────────────────────────
_ROLE_HIERARCHY = {"user": 0, "manager": 1, "admin": 2}
VALID_ROLES = tuple(_ROLE_HIERARCHY.keys())


def has_permission(user: dict | None, level: str) -> bool:
    """Hierarchical check: admin > manager > user."""
    if user is None:
        return False
    user_level = _ROLE_HIERARCHY.get(user.get("role", "user"), 0)
    required = _ROLE_HIERARCHY.get(level, 0)
    return user_level >= required


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def authenticate(username: str, pin: str) -> dict | None:
    """Return user dict if credentials match, else None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM AppUsers WHERE username=? AND pin_hash=?",
        (username, hash_pin(pin)),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_admin_pin(pin: str) -> bool:
    """Return True if the given PIN matches any admin-role user."""
    if not pin:
        return False
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM AppUsers WHERE role='admin' AND pin_hash=?",
        (hash_pin(pin),),
    ).fetchone()
    conn.close()
    return row is not None


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, username, display_name, role, created_at "
        "FROM AppUsers ORDER BY user_id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_pk(pk: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM AppUsers WHERE user_id=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO AppUsers (username, display_name, pin_hash, role, created_at) "
        "VALUES (?,?,?,?,?)",
        (
            data["username"],
            data["display_name"],
            hash_pin(data["pin"]),
            data.get("role", "user"),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def update(pk: int, data: dict) -> None:
    conn = get_connection()
    if data.get("pin"):
        # New PIN supplied — update everything including hash
        conn.execute(
            "UPDATE AppUsers SET username=?, display_name=?, pin_hash=?, role=? "
            "WHERE user_id=?",
            (
                data["username"],
                data["display_name"],
                hash_pin(data["pin"]),
                data.get("role", "user"),
                pk,
            ),
        )
    else:
        # No PIN change — keep existing hash
        conn.execute(
            "UPDATE AppUsers SET username=?, display_name=?, role=? WHERE user_id=?",
            (data["username"], data["display_name"], data.get("role", "user"), pk),
        )
    conn.commit()
    conn.close()


def delete(pk: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM AppUsers WHERE user_id=?", (pk,))
    conn.commit()
    conn.close()
