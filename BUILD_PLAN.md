# Diesel Requisition System — Build Plan (v2)

> **For Cursor:** This is the authoritative spec. Build it in the order below, **one stage at a time**. At the end of each stage, run the stage's Acceptance Checklist, update `CHANGELOG.md` and `README.md`, then stop and report before starting the next stage. Obey `CLAUDE.md` (the project rules) at all times.

---

## 1. What we're building
A small internal web app for diesel fuel requisitions for company vehicles, generators, and heavy equipment, through to billing. Multi-user, login-gated, not public.

**Tech stack (fixed — do not add frameworks):**
- Python + **Streamlit** (UI)
- **PostgreSQL** (Neon) via `st.connection("postgresql", type="sql")` (SQLAlchemy)
- Deployed on **Streamlit Community Cloud**
- Dependencies kept minimal: `streamlit`, `pandas`, `sqlalchemy`, `psycopg2-binary`

**Design values:** simple, elegant, readable. Small functions, clear names, no premature abstraction. Get the foundation right and verify before adding features.

---

## 2. The full lifecycle (the heart of the app)
1. **User** submits a request (asset, requested litres, purpose) → `pending`
2. **Manager** approves → `approved`  *(or rejects → `rejected`)*
3. Fuel is drawn. **User** encodes the **actual litres** and the **date drawn**, then hands the physical receipt to the Purchaser → `for_confirmation`
4. **Purchaser** matches the physical receipt to the encoded actual and confirms → `confirmed` (closed, awaiting billing)
5. When the supplier billing arrives, **Purchaser** selects confirmed requests and tags them **billed** (grouped into one billing). Billed requests drop out of future billing lists. → `billed`
6. **Purchaser** generates a **Bill Payment Request** from that billing → done

**Pricing:** the **Purchaser sets one diesel price per day** (once, at the start of the day). When a User encodes the actual litres, they also set the **date the fuel was drawn**, and the app snapshots the price for *that drawn date* onto the requisition as `unit_price`. Amount = `actual_litres × unit_price`. The snapshot makes each request's cost permanent even if the price changes later.
> The price is keyed to the **date the fuel was drawn** — not the request date, and not the date it was typed in (entry can lag the draw by a day or more). The User sets the drawn date; the price lookup uses it.

**Deferred / future ideas (not in v1):**
- Receipt number entered by the **Purchaser** at confirmation, to prove she is physically holding the receipt.
- PDF / export of the bill payment request.
- Per-asset budgets, odometer/running-hours tracking, email notifications, tagging assets by business.

---

## 3. Roles & permissions
Four roles. **Admin has full access.** Roles are stored per user; a user may hold more than one.

| Action | User | Manager | Purchaser | Admin |
|---|:---:|:---:|:---:|:---:|
| Create a requisition | ✓ | ✓ | | ✓ |
| Approve / reject a requisition | | ✓ | | ✓ |
| Encode actual litres + receipt no. (own request) | ✓ | | | ✓ |
| Set the daily diesel price | | | ✓ | ✓ |
| Confirm actual vs. physical receipt | | | ✓ | ✓ |
| Tag confirmed requests as billed / create a billing | | | ✓ | ✓ |
| Generate the bill payment request | | | ✓ | ✓ |
| Propose a new asset (master data) | ✓ | ✓ | | ✓ |
| Approve a new asset → make it live | | | | ✓ |
| View reports / full history | own only | ✓ | ✓ | ✓ |

---

## 4. State machines
**Requisition:** `pending` → `approved` → `for_confirmation` → `confirmed` → `billed`
Rejection: `pending` → `rejected`.

**Asset (master data):** `pending` → `active` (Admin approves) | `rejected`. Only `active` assets appear in the requisition dropdown.

---

## 5. Database schema — BUILD THIS ONCE, IN STAGE 0
Create the complete schema up front, including columns later stages use. No migrations between stages.

```sql
CREATE TABLE IF NOT EXISTS users (
    email        TEXT PRIMARY KEY,
    display_name TEXT,
    roles        TEXT[] NOT NULL DEFAULT '{}'        -- e.g. {'user'} or {'admin'}
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
    price_date      DATE PRIMARY KEY,                -- one price per calendar day
    price_per_liter NUMERIC NOT NULL CHECK (price_per_liter > 0),
    set_by          TEXT,
    set_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billings (
    id           SERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ DEFAULT now(),
    created_by   TEXT,
    supplier_ref TEXT,                               -- supplier invoice reference, optional
    note         TEXT
    -- total is derived: SUM(amount) of the requisitions in this billing
);

CREATE TABLE IF NOT EXISTS requisitions (
    id               SERIAL PRIMARY KEY,
    created_at       TIMESTAMPTZ DEFAULT now(),   -- system audit stamp; never edited
    request_date     DATE,                        -- user-facing date; defaults to today, editable
    requested_by     TEXT NOT NULL,
    asset_id         INTEGER NOT NULL REFERENCES assets(id),
    requested_liters NUMERIC NOT NULL CHECK (requested_liters > 0),
    purpose          TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','approved','rejected','for_confirmation','confirmed','billed')),
    -- approval (Manager)
    approved_by      TEXT,
    approved_at      TIMESTAMPTZ,
    reject_reason    TEXT,
    -- actualisation (User)
    actual_liters    NUMERIC CHECK (actual_liters IS NULL OR actual_liters >= 0),
    drawn_date       DATE,           -- the day the fuel was actually drawn; drives the price
    receipt_no       TEXT,           -- optional in v1 (see deferred ideas in §2)
    actual_filled_at TIMESTAMPTZ,
    unit_price       NUMERIC,        -- snapshot of daily_prices for drawn_date
    -- amount is derived in queries: actual_liters * unit_price
    -- confirmation (Purchaser)
    confirmed_by     TEXT,
    confirmed_at     TIMESTAMPTZ,
    -- billing (Purchaser)
    billing_id       INTEGER REFERENCES billings(id),
    billed_by        TEXT,
    billed_at        TIMESTAMPTZ
);
```

---

## 6. Recommended file structure
```
diesel-requisition/
├── app.py              # entry: login gate + role-based navigation only
├── db.py               # connection, schema init, small query helpers
├── auth.py             # current user, role checks, local dev role override
├── views/
│   ├── requisition.py  # User: new request, my requests, encode actual + receipt
│   ├── approvals.py    # Manager: pending queue (approve/reject)
│   ├── pricing.py      # Purchaser: set today's diesel price          (Stage B)
│   ├── confirm.py      # Purchaser: confirm actual vs receipt          (Stage B)
│   ├── billing.py      # Purchaser: tag billed + bill payment request  (Stage C)
│   └── master_data.py  # Admin: approve proposed assets; propose form  (Stage D)
├── requirements.txt
├── .gitignore          # MUST include .venv/ , __pycache__/ , .streamlit/secrets.toml
├── .cursorrules
├── README.md
├── CHANGELOG.md
└── .streamlit/
    └── secrets.toml    # gitignored — local dev only; never committed
```

---

## 7. Foundation patterns (keep them this simple)

**Connection + schema init (`db.py`):**
```python
import streamlit as st
from sqlalchemy import text

def get_conn():
    return st.connection("postgresql", type="sql")

def init_schema():
    conn = get_conn()
    with conn.session as s:
        s.execute(text(SCHEMA_SQL))   # all CREATE TABLE statements from §5
        s.commit()
```

**Auth + role check (`auth.py`):**
```python
import streamlit as st

def current_user():
    try:
        email = st.experimental_user.email          # logged-in viewer on Streamlit Cloud
    except Exception:
        email = None
    if not email:                                    # local dev: act as any role
        email = st.sidebar.selectbox("Dev: act as",
                 ["admin@dev", "user@dev", "manager@dev", "purchaser@dev"])
    return email

def has_role(roles: list[str], role: str) -> bool:
    return "admin" in roles or role in roles         # admin can do anything
```

**Day-price lookup when encoding actual litres:**
```python
# Price is keyed to drawn_date (the day fuel was drawn), which the User sets.
# Snapshot it onto the requisition. If no price exists for that date, block and
# tell them to ask the Purchaser to set the price for that day.
price = conn.query("SELECT price_per_liter FROM daily_prices WHERE price_date = :d",
                   params={"d": drawn_date}, ttl=0)
```

Seed `users` (your email as `{'admin'}`) and a few `active` assets in Stage 0 so the app is usable immediately.

---

## 8. Staged build

### Stage 0 — Foundation (do this first, completely)
**Tasks**
1. Create `README.md` and `CHANGELOG.md` in the formats in §9. (Cursor's first task.)
2. Create `.gitignore`, `requirements.txt`, `secrets-template.toml`.
3. `db.py` with the **complete** schema (§5) and `init_schema()`.
4. `auth.py` with `current_user()`, `has_role()`, dev role override.
5. `app.py`: run `init_schema()` once, get the user, show role-based navigation (empty placeholder screens are fine).
6. Seed the `users` table (your email as admin) and 3–4 `active` assets.

**Acceptance checklist**
- [ ] Runs locally with `streamlit run app.py`, no errors.
- [ ] All five tables exist in Neon.
- [ ] Dev switcher loads the app as each of the four roles.
- [ ] Navigation shows the correct sections per role (§3).
- [ ] `.gitignore` contains `.streamlit/secrets.toml`; no secret committed.

### Stage A — Requisition core (User + Manager) → first deploy
**Tasks**
1. **User** (`requisition.py`): form to create a requisition (request date defaulting to today but editable, dropdown of `active` assets, litres, purpose) → `pending`; plus a "My requests" table with statuses.
2. **Manager** (`approvals.py`): table of `pending` requisitions; Approve → `approved`; Reject (asks reason) → `rejected`, stamping who/when.

**Acceptance checklist**
- [ ] User submits → appears `pending`.
- [ ] Manager can approve and reject (with reason); User sees the status change.
- [ ] Empty states render cleanly (friendly message, not an error).
- [ ] CHANGELOG + README updated; committed, pushed, **deployed and opened on your phone.**

### Stage B — Actualisation, daily price, confirmation
**Tasks**
1. **Purchaser** (`pricing.py`): set the diesel price for a given date (insert/update `daily_prices`; defaults to today). Show the price already set for that date.
2. **User** (`requisition.py`): on own `approved` requests, encode `actual_liters` and the **`drawn_date`** (defaults to today, editable); `receipt_no` optional. On save, look up `daily_prices` for the `drawn_date`, snapshot it as `unit_price`, and set `for_confirmation`. If no price exists for that drawn date, block with a clear message ("ask the Purchaser to set the price for that day").
3. **Purchaser** (`confirm.py`): list `for_confirmation` requests showing requested vs actual, drawn date, and computed amount; a Confirm action → `confirmed`, stamping who/when.

**Acceptance checklist**
- [ ] Purchaser sets a price for a date once; re-opening that date shows it.
- [ ] User can encode actual + drawn date only on their own `approved` requests; status → `for_confirmation`; `unit_price` snapshotted from the **drawn date's** price.
- [ ] A back-dated draw uses that earlier date's price, not today's.
- [ ] Encoding actual is blocked if no price is set for the drawn date.
- [ ] Purchaser confirms → `confirmed`; amount = actual_liters × unit_price is correct.
- [ ] CHANGELOG + README updated; committed, pushed, redeployed.

### Stage C — Billing
**Tasks**
1. **Purchaser** (`billing.py`): list `confirmed` requests not yet billed; multi-select them, create a `billings` row, set each selected requisition's `billing_id` + `billed_by/at` → `billed`. Billed requests no longer appear in this list.
2. Generate a **Bill Payment Request** view for a billing: line items (date, asset, actual litres, unit price, amount), plus the total. Printable on-screen summary (PDF/export can come later).

**Acceptance checklist**
- [ ] Only `confirmed`, not-yet-billed requests appear for billing.
- [ ] Tagging billed assigns a billing, sets `billed`, and removes them from the list.
- [ ] Bill payment request totals = sum of line amounts; figures match the requests.
- [ ] CHANGELOG + README updated; committed, pushed, redeployed.

### Stage D — Master data governance (Admin)
**Tasks**
1. **Propose asset** (`master_data.py`): Users and Managers propose a new asset → `pending`; it is NOT selectable in a requisition.
2. **Admin** (`master_data.py`): queue of `pending` assets; Approve → `active`, Reject → `rejected`, stamping who/when.

**Acceptance checklist**
- [ ] A proposed asset is `pending` and not selectable.
- [ ] After Admin approval it becomes `active` and selectable; rejected never becomes selectable.
- [ ] Admin can see and do everything across all screens.
- [ ] CHANGELOG + README updated; committed, pushed, redeployed.

---

## 9. Required formats for the maintained docs

**`README.md`** — keep current at every stage:
1. Overview  2. Roles (table from §3)  3. Tech stack  4. Local setup (venv, install, secrets, run)  5. Deployment (Streamlit Cloud + Neon, how secrets are set)  6. Database schema (brief)  7. Project structure (tree from §6)  8. Current status (which stage is complete).

**`CHANGELOG.md`** — *Keep a Changelog* style, dated section per stage, newest on top, entries under **Added / Changed / Fixed**:
```
# Changelog
All notable changes to this project are documented here.

## [Unreleased]

## [Stage A] - YYYY-MM-DD
### Added
- User requisition form and "My requests" view.
- Manager approval queue (approve / reject with reason).
```

---

## 10. Guardrails (do not violate)
- Never hardcode the database URL or any secret. Always read from Streamlit secrets.
- Never run destructive SQL (`DROP`, `DELETE`, `TRUNCATE`) without an explicit instruction in chat.
- Do not add dependencies or restructure files without asking first.
- Do not start the next stage until the current stage's Acceptance Checklist passes.
- When unsure, stop and ask rather than guess.
