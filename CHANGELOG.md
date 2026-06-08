# Changelog
All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); newest on top.

## [Unreleased]
### Added
- Username/password login for the deployed app (`streamlit-authenticator`); the signed-in email is matched against the `users` table for roles. Credentials and cookie key live in secrets.
- `dev_mode` secret flag that enables the local "Dev: act as" role switcher; without it the switcher cannot appear (so it is never available on the deployed app).

### Changed
- `auth.py` no longer relies on Streamlit Community Cloud exposing the viewer's email (which it stopped doing in Streamlit 1.42+); production now requires an explicit login.
- Database connection is more resilient to Neon's serverless idle/wake cycle: `pool_pre_ping` + `pool_recycle` replace stale connections, and `init_schema()` retries transient disconnects.

### Removed
- Google OIDC sign-in (`st.login()` / `Authlib` / `httpx`): native Streamlit OAuth does not work on Streamlit Community Cloud, whose auth proxy breaks the OAuth callback. Replaced with username/password login.

## [Stage D] - 2026-06-08
### Added
- "Master Data" screen: Users and Managers propose a new asset (→ `pending`, not selectable in a requisition); Admins get a queue of pending assets to Approve (→ `active`, selectable) or Reject (→ `rejected`), stamping who/when. Non-admins see the pending list read-only.
- `db.py` helpers: `propose_asset`, `get_pending_assets`, `approve_asset`, `reject_asset`.

## [Stage C] - 2026-06-08
### Added
- Purchaser "Billing" screen with two tabs: *Create billing* (multi-select confirmed, not-yet-billed requests → create a billing and tag them `billed`, removing them from the list) and *Bill payment request* (pick a billing → line items with the total).
- `db.py` helpers: `get_billable_requisitions`, `create_billing`, `get_billings`, `get_billing_lines`.

## [Stage B] - 2026-06-08
### Added
- Purchaser "Daily Price" screen: set/update the diesel price for a date; shows the price already set for that date.
- User "Record Fuel Drawn" screen: encode actual litres + drawn date (+ optional receipt no.) on own approved requests. Snapshots the drawn date's price as `unit_price` and moves the request to `for_confirmation`. Blocks with a clear message if no price is set for that drawn date.
- Purchaser "Confirm Receipts" screen: lists `for_confirmation` requests with requested vs actual, drawn date, and computed amount; Confirm → `confirmed`, stamping who/when.
- `db.py` helpers: `get_price_for_date`, `set_daily_price`, `get_my_approved_requisitions`, `update_actual`, `get_for_confirmation_requisitions`, `confirm_requisition`.

### Changed
- "My Requests" now also shows actual litres, drawn date, and amount once encoded.

### Fixed
- Encoding actual litres crashed with a `ProgrammingError` (psycopg2 can't adapt numpy types). DB write helpers now coerce ids/litres/price from numpy/pandas types to native Python (`int`, `float`, `Decimal`) before binding.

## [Stage A] - 2026-06-08
### Added
- User requisition form (request date, active-asset dropdown, litres, purpose) creating a `pending` requisition, plus a "My Requests" table showing each request's status.
- Manager approval queue: approve a pending requisition (→ `approved`) or reject it with a required reason (→ `rejected`), stamping who and when.
- `db.py` query helpers: `get_active_assets`, `create_requisition`, `get_my_requisitions`, `get_pending_requisitions`, `approve_requisition`, `reject_requisition`.
- `views/requisition.py` and `views/approvals.py`, wired into the role-based navigation.

### Changed
- Schema init now runs once per session instead of on every rerun.

## [Stage 0] - 2026-06-07
### Changed
- `auth.py` now reads identity from `st.user.email` (the current API) instead of the deprecated `st.experimental_user.email`.

### Added
- Project scaffolding: `.gitignore`, `requirements.txt`, `secrets-template.toml`.
- `db.py`: complete database schema (users, assets, daily_prices, billings, requisitions), `init_schema()`, and a `get_user_roles()` helper.
- Idempotent seed data: live admin user, four dev role accounts, and four active assets.
- `auth.py`: `current_user()`, `has_role()`, and a local-dev role switcher.
- `app.py`: schema init on start, login gate, and role-based navigation with placeholder screens.
- `README.md` and this changelog.
