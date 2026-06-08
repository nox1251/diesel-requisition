"""Database connection, schema initialisation, and small query helpers."""

import time
from decimal import Decimal

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

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
    ("denver.so@gmail.com", "Denver", ["admin"]),
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
    # pool_pre_ping replaces connections Neon has dropped while idle; pool_recycle
    # avoids reusing long-lived sockets the serverless endpoint may have closed.
    return st.connection(
        "postgresql", type="sql", pool_pre_ping=True, pool_recycle=300
    )


def init_schema():
    """Create all tables and seed initial data. Safe to run on every start.

    Retries transient disconnects: Neon's serverless compute can drop the first
    connection while it wakes from idle.
    """
    conn = get_conn()
    for attempt in range(3):
        try:
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
            return
        except OperationalError:
            if attempt == 2:
                raise
            time.sleep(1.5)


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


def get_active_assets():
    """Active assets for the requisition dropdown, as a DataFrame of id + name."""
    conn = get_conn()
    return conn.query(
        "SELECT id, name FROM assets WHERE status = 'active' ORDER BY name",
        ttl=0,
    )


def create_requisition(requested_by, asset_id, requested_liters, purpose, request_date):
    """Insert a new requisition in 'pending' status."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "INSERT INTO requisitions "
                "(request_date, requested_by, asset_id, requested_liters, purpose) "
                "VALUES (:date, :by, :asset_id, :liters, :purpose)"
            ),
            {
                "date": request_date,
                "by": requested_by,
                "asset_id": int(asset_id),
                "liters": float(requested_liters),
                "purpose": purpose,
            },
        )
        s.commit()


def get_my_requisitions(email):
    """All requisitions raised by this user, newest first, with the asset name."""
    conn = get_conn()
    return conn.query(
        "SELECT r.request_date, a.name AS asset, r.requested_liters, r.purpose, "
        "       r.status, r.actual_liters, r.drawn_date, "
        "       r.actual_liters * r.unit_price AS amount, r.reject_reason "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.requested_by = :email "
        "ORDER BY r.created_at DESC",
        params={"email": email},
        ttl=0,
    )


def get_pending_requisitions():
    """Requisitions awaiting a manager's decision, oldest first."""
    conn = get_conn()
    return conn.query(
        "SELECT r.id, r.request_date, r.requested_by, a.name AS asset, "
        "       r.requested_liters, r.purpose "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.status = 'pending' "
        "ORDER BY r.created_at",
        ttl=0,
    )


def approve_requisition(req_id, approver):
    """Approve a pending requisition, stamping who and when."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "UPDATE requisitions "
                "SET status = 'approved', approved_by = :by, approved_at = now() "
                "WHERE id = :id AND status = 'pending'"
            ),
            {"by": approver, "id": int(req_id)},
        )
        s.commit()


def reject_requisition(req_id, approver, reason):
    """Reject a pending requisition with a reason, stamping who and when."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "UPDATE requisitions "
                "SET status = 'rejected', approved_by = :by, approved_at = now(), "
                "    reject_reason = :reason "
                "WHERE id = :id AND status = 'pending'"
            ),
            {"by": approver, "id": int(req_id), "reason": reason},
        )
        s.commit()


def get_price_for_date(price_date):
    """The diesel price set for a given date, or None if none is set."""
    conn = get_conn()
    rows = conn.query(
        "SELECT price_per_liter FROM daily_prices WHERE price_date = :d",
        params={"d": price_date},
        ttl=0,
    )
    if rows.empty:
        return None
    # Convert away from numpy/pandas types so psycopg2 can bind it as a parameter.
    return Decimal(str(rows.iloc[0]["price_per_liter"]))


def set_daily_price(price_date, price, set_by):
    """Insert or update the diesel price for a date."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "INSERT INTO daily_prices (price_date, price_per_liter, set_by, set_at) "
                "VALUES (:d, :p, :by, now()) "
                "ON CONFLICT (price_date) DO UPDATE "
                "SET price_per_liter = EXCLUDED.price_per_liter, "
                "    set_by = EXCLUDED.set_by, set_at = now()"
            ),
            {"d": price_date, "p": price, "by": set_by},
        )
        s.commit()


def get_my_approved_requisitions(email):
    """This user's approved requests awaiting actual litres, oldest first."""
    conn = get_conn()
    return conn.query(
        "SELECT r.id, r.request_date, a.name AS asset, r.requested_liters, r.purpose "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.requested_by = :email AND r.status = 'approved' "
        "ORDER BY r.created_at",
        params={"email": email},
        ttl=0,
    )


def update_actual(req_id, email, actual_liters, drawn_date, receipt_no, unit_price):
    """Record actual litres + drawn date on an approved request, snapshotting the
    drawn date's price, and move it to 'for_confirmation'."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "UPDATE requisitions "
                "SET actual_liters = :al, drawn_date = :dd, receipt_no = :rn, "
                "    unit_price = :up, actual_filled_at = now(), "
                "    status = 'for_confirmation' "
                "WHERE id = :id AND requested_by = :email AND status = 'approved'"
            ),
            {
                "al": float(actual_liters),
                "dd": drawn_date,
                "rn": receipt_no,
                "up": Decimal(str(unit_price)),
                "id": int(req_id),
                "email": email,
            },
        )
        s.commit()


def get_for_confirmation_requisitions():
    """Requests awaiting the Purchaser's confirmation, with computed amount."""
    conn = get_conn()
    return conn.query(
        "SELECT r.id, r.request_date, r.requested_by, a.name AS asset, "
        "       r.requested_liters, r.actual_liters, r.drawn_date, r.unit_price, "
        "       r.actual_liters * r.unit_price AS amount, r.receipt_no "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.status = 'for_confirmation' "
        "ORDER BY r.created_at",
        ttl=0,
    )


def confirm_requisition(req_id, confirmer):
    """Confirm actual vs receipt, stamping who and when."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "UPDATE requisitions "
                "SET status = 'confirmed', confirmed_by = :by, confirmed_at = now() "
                "WHERE id = :id AND status = 'for_confirmation'"
            ),
            {"by": confirmer, "id": int(req_id)},
        )
        s.commit()


def get_billable_requisitions():
    """Confirmed requests not yet assigned to a billing, with computed amount."""
    conn = get_conn()
    return conn.query(
        "SELECT r.id, r.request_date, r.requested_by, a.name AS asset, "
        "       r.drawn_date, r.actual_liters, r.unit_price, "
        "       r.actual_liters * r.unit_price AS amount "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.status = 'confirmed' AND r.billing_id IS NULL "
        "ORDER BY r.confirmed_at",
        ttl=0,
    )


def create_billing(created_by, req_ids, supplier_ref, note):
    """Create a billing and tag the selected confirmed requests as billed."""
    conn = get_conn()
    with conn.session as s:
        billing_id = s.execute(
            text(
                "INSERT INTO billings (created_by, supplier_ref, note) "
                "VALUES (:by, :ref, :note) RETURNING id"
            ),
            {"by": created_by, "ref": supplier_ref, "note": note},
        ).scalar()
        for req_id in req_ids:
            s.execute(
                text(
                    "UPDATE requisitions "
                    "SET billing_id = :bid, billed_by = :by, billed_at = now(), "
                    "    status = 'billed' "
                    "WHERE id = :id AND status = 'confirmed' AND billing_id IS NULL"
                ),
                {"bid": int(billing_id), "by": created_by, "id": int(req_id)},
            )
        s.commit()
        return billing_id


def get_billings():
    """All billings, newest first, with line count and total amount."""
    conn = get_conn()
    return conn.query(
        "SELECT b.id, b.created_at, b.created_by, b.supplier_ref, b.note, "
        "       COUNT(r.id) AS line_count, "
        "       COALESCE(SUM(r.actual_liters * r.unit_price), 0) AS total "
        "FROM billings b LEFT JOIN requisitions r ON r.billing_id = b.id "
        "GROUP BY b.id ORDER BY b.created_at DESC",
        ttl=0,
    )


def get_billing_lines(billing_id):
    """Line items for a billing's bill payment request."""
    conn = get_conn()
    return conn.query(
        "SELECT r.drawn_date, a.name AS asset, r.requested_by, r.receipt_no, "
        "       r.actual_liters, r.unit_price, "
        "       r.actual_liters * r.unit_price AS amount "
        "FROM requisitions r JOIN assets a ON a.id = r.asset_id "
        "WHERE r.billing_id = :bid "
        "ORDER BY r.drawn_date",
        params={"bid": int(billing_id)},
        ttl=0,
    )
