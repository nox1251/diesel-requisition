"""Database connection, schema initialisation, and small query helpers."""

import streamlit as st
from sqlalchemy import text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    email        TEXT PRIMARY KEY,
    display_name TEXT,
    roles        TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS assets (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    asset_type  TEXT NOT NULL CHECK (asset_type IN ('vehicle','generator','equipment')),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','active','rejected')),
    proposed_by TEXT,
    proposed_at TIMESTAMPTZ DEFAULT now(),
    approved_by TEXT,
    approved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS daily_prices (
    price_date      DATE PRIMARY KEY,
    price_per_liter NUMERIC NOT NULL CHECK (price_per_liter > 0),
    set_by          TEXT,
    set_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billings (
    id           SERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ DEFAULT now(),
    created_by   TEXT,
    supplier_ref TEXT,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS requisitions (
    id               SERIAL PRIMARY KEY,
    created_at       TIMESTAMPTZ DEFAULT now(),
    request_date     DATE,
    requested_by     TEXT NOT NULL,
    asset_id         INTEGER NOT NULL REFERENCES assets(id),
    requested_liters NUMERIC NOT NULL CHECK (requested_liters > 0),
    purpose          TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','approved','rejected','for_confirmation','confirmed','billed')),
    approved_by      TEXT,
    approved_at      TIMESTAMPTZ,
    reject_reason    TEXT,
    actual_liters    NUMERIC CHECK (actual_liters IS NULL OR actual_liters >= 0),
    drawn_date       DATE,
    receipt_no       TEXT,
    actual_filled_at TIMESTAMPTZ,
    unit_price       NUMERIC,
    confirmed_by     TEXT,
    confirmed_at     TIMESTAMPTZ,
    billing_id       INTEGER REFERENCES billings(id),
    billed_by        TEXT,
    billed_at        TIMESTAMPTZ
);
"""

# Seed users so the dev role switcher has real roles, plus the live admin.
SEED_USERS = [
    ("denver.so+diesel@gmail.com", "Denver", ["admin"]),
    ("admin@dev", "Dev Admin", ["admin"]),
    ("user@dev", "Dev User", ["user"]),
    ("manager@dev", "Dev Manager", ["manager"]),
    ("purchaser@dev", "Dev Purchaser", ["purchaser"]),
]

SEED_ASSETS = [
    ("Toyota Hilux (ABC-123)", "vehicle"),
    ("Isuzu Dump Truck (DEF-456)", "vehicle"),
    ("Cummins 100kVA Generator", "generator"),
    ("CAT 320 Excavator", "equipment"),
]


def get_conn():
    return st.connection("postgresql", type="sql")


def init_schema():
    """Create all tables and seed initial data. Safe to run on every start."""
    conn = get_conn()
    with conn.session as s:
        s.execute(text(SCHEMA_SQL))
        for email, name, roles in SEED_USERS:
            s.execute(
                text(
                    "INSERT INTO users (email, display_name, roles) "
                    "VALUES (:email, :name, :roles) ON CONFLICT (email) DO NOTHING"
                ),
                {"email": email, "name": name, "roles": roles},
            )
        already_seeded = s.execute(text("SELECT COUNT(*) FROM assets")).scalar()
        if not already_seeded:
            for name, asset_type in SEED_ASSETS:
                s.execute(
                    text(
                        "INSERT INTO assets (name, asset_type, status, approved_by, approved_at) "
                        "VALUES (:name, :type, 'active', 'system', now())"
                    ),
                    {"name": name, "type": asset_type},
                )
        s.commit()


def get_user_roles(email: str) -> list[str]:
    """Return the roles for a user, or an empty list if unknown."""
    conn = get_conn()
    rows = conn.query(
        "SELECT roles FROM users WHERE email = :email",
        params={"email": email},
        ttl=0,
    )
    if rows.empty:
        return []
    return list(rows.iloc[0]["roles"])
