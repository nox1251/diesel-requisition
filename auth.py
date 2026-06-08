"""Current user, role checks, and a local-dev role override.

Production gates access behind a username/password login (streamlit-authenticator);
the signed-in user's email is matched against the `users` table for roles. Local
development sets `dev_mode = true` in secrets to skip login and act as any role.
The dev switcher is never available unless `dev_mode` is set, so it cannot appear
on the deployed app.

Secrets layout for the deployed app:

    [authenticator]
    cookie_name = "diesel_auth"
    cookie_key = "<random string>"
    cookie_expiry_days = 30

    [credentials.usernames."denver.so@gmail.com"]
    name = "Denver"
    email = "denver.so@gmail.com"
    password = "<the user's password>"   # auto-hashed at runtime

Each username should be the user's email, matching a row in the `users` table.
"""

import streamlit as st
import streamlit_authenticator as stauth

DEV_ACCOUNTS = ["admin@dev", "user@dev", "manager@dev", "purchaser@dev"]


def _to_plain(obj):
    """Recursively convert Streamlit's secrets mappings to plain dicts."""
    if hasattr(obj, "items"):
        return {k: _to_plain(v) for k, v in obj.items()}
    return obj


def _build_authenticator() -> stauth.Authenticate:
    cfg = st.secrets["authenticator"]
    return stauth.Authenticate(
        _to_plain(st.secrets["credentials"]),
        cfg["cookie_name"],
        cfg["cookie_key"],
        cfg.get("cookie_expiry_days", 30),
    )


def current_user() -> str:
    """Return the current user's email, gating access by login when deployed."""
    # Local development: act as any role without logging in.
    if st.secrets.get("dev_mode", False):
        return st.sidebar.selectbox("Dev: act as", DEV_ACCOUNTS)

    # Deployed: require a username/password login.
    authenticator = _build_authenticator()
    authenticator.login(location="main")
    status = st.session_state.get("authentication_status")
    if status:
        authenticator.logout("Log out", location="sidebar")
        return st.session_state["username"]
    if status is False:
        st.error("Username or password is incorrect.")
    st.stop()


def has_role(roles: list[str], role: str) -> bool:
    """Admin can do anything; otherwise the role must be present."""
    return "admin" in roles or role in roles
