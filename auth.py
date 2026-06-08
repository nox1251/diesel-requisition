"""Current user, role checks, and a local-dev role override.

Production gates access behind a username/password login (streamlit-authenticator);
the signed-in username is matched against the `users` table for roles. Local
development sets `dev_mode = true` in secrets to skip login and act as any role.
The dev switcher is never available unless `dev_mode` is set, so it cannot appear
on the deployed app.

Users (usernames, passwords, roles) live in the `users` table and are managed
in-app via Admin -> Manage Users. Secrets only need the cookie config:

    [authenticator]
    cookie_name = "diesel_auth"
    cookie_key = "<random string>"
    cookie_expiry_days = 30
"""

import streamlit as st
import streamlit_authenticator as stauth

from db import get_login_credentials

DEV_ACCOUNTS = ["admin@dev", "user@dev", "manager@dev", "purchaser@dev"]


def current_user() -> str:
    """Return the current user's username, gating access by login when deployed."""
    # Local development: act as any role without logging in.
    if st.secrets.get("dev_mode", False):
        return st.sidebar.selectbox("Dev: act as", DEV_ACCOUNTS)

    # Deployed: require a username/password login. Credentials live in the
    # database (managed via Admin -> Manage Users); passwords are pre-hashed.
    cfg = st.secrets["authenticator"]
    authenticator = stauth.Authenticate(
        get_login_credentials(),
        cfg["cookie_name"],
        cfg["cookie_key"],
        cfg.get("cookie_expiry_days", 30),
        auto_hash=False,
    )
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
