"""Current user, role checks, and a local-dev role override."""

import streamlit as st

DEV_ACCOUNTS = ["admin@dev", "user@dev", "manager@dev", "purchaser@dev"]


def current_user() -> str:
    """The logged-in viewer's email on Streamlit Cloud, or a dev account locally."""
    try:
        email = st.user.email
    except Exception:
        email = None
    if not email:
        email = st.sidebar.selectbox("Dev: act as", DEV_ACCOUNTS)
    return email


def has_role(roles: list[str], role: str) -> bool:
    """Admin can do anything; otherwise the role must be present."""
    return "admin" in roles or role in roles
