# Changelog
All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); newest on top.

## [Unreleased]
### Added
- Google sign-in (OIDC via `st.login()`) for the deployed app; the signed-in email is matched against the `users` table for roles. Added `Authlib` dependency.
- `dev_mode` secret flag that enables the local "Dev: act as" role switcher; without it the switcher cannot appear (so it is never available on the deployed app).

### Changed
- `auth.py` no longer relies on Streamlit Community Cloud exposing the viewer's email (which it stopped doing in Streamlit 1.42+); production now requires explicit Google sign-in.

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
