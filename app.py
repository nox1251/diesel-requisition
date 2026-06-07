"""Diesel Requisition System — entry point: login gate + role-based navigation."""

import streamlit as st

from auth import current_user, has_role
from db import init_schema, get_user_roles

st.set_page_config(page_title="Diesel Requisition", page_icon="⛽")

init_schema()

email = current_user()
roles = get_user_roles(email)

st.sidebar.write(f"**{email}**")
st.sidebar.caption("Roles: " + (", ".join(roles) if roles else "none"))

# Each page lists the roles that unlock it. Admin unlocks everything via has_role.
PAGES = [
    ("New Requisition", ["user", "manager"]),
    ("My Requests", ["user", "manager"]),
    ("Approvals", ["manager"]),
    ("Daily Price", ["purchaser"]),
    ("Confirm Receipts", ["purchaser"]),
    ("Billing", ["purchaser"]),
    ("Master Data", ["user", "manager"]),
]

available = [
    label
    for label, allowed in PAGES
    if any(has_role(roles, role) for role in allowed)
]

st.sidebar.divider()
if not available:
    st.title("Diesel Requisition System")
    st.warning("Your account has no roles assigned yet. Ask an admin to grant access.")
    st.stop()

page = st.sidebar.radio("Go to", available)

st.title(page)
st.info("This screen is a placeholder — it will be built in a later stage.")
