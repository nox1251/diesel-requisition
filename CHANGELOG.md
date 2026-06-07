# Changelog
All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); newest on top.

## [Unreleased]

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
