"""Current user, role checks, and a local-dev role override.

Production (Streamlit Community Cloud) gates access behind Google sign-in via
`st.login()`; the signed-in email is matched against the `users` table for
roles. Local development sets `dev_mode = true` in secrets to skip login and
act as any role. The dev switcher is never available unless `dev_mode` is set,
so it cannot appear on the deployed app.
"""

import streamlit as st

DEV_ACCOUNTS = ["admin@dev", "user@dev", "manager@dev", "purchaser@dev"]


def current_user() -> str:
    """Return the current user's email, gating access by login when deployed."""
    # Local development: act as any role without logging in.
    if st.secrets.get("dev_mode", False):
        return st.sidebar.selectbox("Dev: act as", DEV_ACCOUNTS)

    # Deployed: require a real Google sign-in.
    try:
        logged_in = st.user.is_logged_in
    except Exception:
        st.title("Diesel Requisition System")
        st.error("Sign-in is not configured yet. Please contact the administrator.")
        st.stop()

    if not logged_in:
        st.title("Diesel Requisition System")
        st.write("Please sign in with your Google account to continue.")
        st.button("Sign in with Google", on_click=st.login, type="primary")
        st.stop()

    return st.user.email


def has_role(roles: list[str], role: str) -> bool:
    """Admin can do anything; otherwise the role must be present."""
    return "admin" in roles or role in roles
