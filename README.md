# Diesel Requisition System

A small internal web app for diesel fuel requisitions for company vehicles, generators, and heavy equipment — from request through approval, actualisation, confirmation, and billing. Multi-user, login-gated, not public.

## Roles

Four roles. **Admin has full access.** A user may hold more than one role.

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

## Tech stack

- Python + **Streamlit** (UI)
- **PostgreSQL** (Neon) via `st.connection("postgresql", type="sql")` (SQLAlchemy)
- Deployed on **Streamlit Community Cloud**
- Dependencies: `streamlit`, `pandas`, `sqlalchemy`, `psycopg2-binary`

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure the database connection:
mkdir -p .streamlit
cp secrets-template.toml .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your Neon connection string

streamlit run app.py
```

For local development, set `dev_mode = true` in `.streamlit/secrets.toml` (see
`secrets-template.toml`). This shows a **Dev: act as** switcher in the sidebar so
you can use the app as any role without signing in. `dev_mode` must never be set
in the deployed app's secrets.

## Deployment

Live app: **https://diesel-requisition.streamlit.app** (private — viewers must be invited).

Deployed on **Streamlit Community Cloud**, backed by a **Neon** PostgreSQL database.

The app must be set to **public** in Streamlit Cloud (Share → "Make this app
public"). Community Cloud's auth proxy for private apps is incompatible with
in-app login; access is instead gated by the app's own login (below).

**Secrets** (set in the Streamlit Cloud app's *Secrets* box, never committed):

- `[connections.postgresql] url` — the Neon connection string.
- `[authenticator]` — `cookie_name`, `cookie_key` (random), `cookie_expiry_days`.
- `[credentials.usernames."<email>"]` — one block per user with `name`, `email`,
  and `password` (auto-hashed at runtime). The username key must be the user's
  email and match a row in the `users` table.
- Do **not** set `dev_mode` here.

**Authentication:** the deployed app gates access behind a username/password
login (`streamlit-authenticator`). The signed-in email is matched against the
`users` table to determine roles; an email with no matching row gets no access.
(Native Google sign-in via `st.login()` was attempted but does not work on
Streamlit Community Cloud — its auth proxy breaks the OAuth callback.)

## Database schema (brief)

Five tables, created once in Stage 0 (no migrations between stages):

- **users** — `email` (PK), `display_name`, `roles[]`.
- **assets** — equipment master data; `status` is `pending` → `active` / `rejected`. Only `active` assets appear in the requisition dropdown.
- **daily_prices** — one `price_per_liter` per `price_date`.
- **billings** — a group of confirmed requisitions billed together.
- **requisitions** — the core lifecycle record: request → approval → actualisation (`actual_liters`, `drawn_date`, snapshotted `unit_price`) → confirmation → billing.

## Project structure

```
diesel-requisition/
├── app.py              # entry: login gate + role-based navigation
├── db.py               # connection, schema init, query helpers, seed data
├── auth.py             # current user, role checks, local dev role override
├── views/
│   ├── requisition.py  # User: new request, my requests, record fuel drawn
│   ├── approvals.py    # Manager: approve / reject pending requests
│   ├── pricing.py      # Purchaser: set the daily diesel price
│   ├── confirm.py      # Purchaser: confirm actual vs receipt
│   ├── billing.py      # Purchaser: create billings + bill payment request
│   └── master_data.py  # Propose assets; Admin approves → active
├── requirements.txt
├── secrets-template.toml
├── .gitignore
├── README.md
├── CHANGELOG.md
└── .streamlit/
    └── secrets.toml    # gitignored — local dev only; never committed
```

## Current status

**Stage D — Master data governance: complete. All stages (0, A–D) are built.** Users and Managers can propose new assets, which stay `pending` (not selectable) until an Admin approves them to `active` or rejects them. The full lifecycle is in place: propose/approve assets → request fuel → approve → set daily price → record actual litres drawn → confirm → bill → bill payment request.
