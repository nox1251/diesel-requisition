"""Diesel Requisition System — entry point: login gate + role-based navigation."""

import streamlit as st

from auth import current_user, has_role
from db import init_schema, get_user_roles
from views.requisition import new_requisition, my_requests, encode_actual
from views.approvals import approvals
from views.pricing import pricing
from views.confirm import confirm
from views.billing import billing

st.set_page_config(page_title="Diesel Requisition", page_icon="⛽")

# Build the schema and seed once per session, not on every rerun.
if "schema_ready" not in st.session_state:
    init_schema()
    st.session_state.schema_ready = True

email = current_user()
roles = get_user_roles(email)

st.sidebar.write(f"**{email}**")
st.sidebar.caption("Roles: " + (", ".join(roles) if roles else "none"))

# Each page lists the roles that unlock it. Admin unlocks everything via has_role.
PAGES = [
    ("New Requisition", ["user", "manager"]),
    ("My Requests", ["user", "manager"]),
    ("Record Fuel Drawn", ["user"]),
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

st.header(page)
if page == "New Requisition":
    new_requisition(email)
elif page == "My Requests":
    my_requests(email)
elif page == "Record Fuel Drawn":
    encode_actual(email)
elif page == "Approvals":
    approvals(email)
elif page == "Daily Price":
    pricing(email)
elif page == "Confirm Receipts":
    confirm(email)
elif page == "Billing":
    billing(email)
else:
    st.info("This screen is a placeholder — it will be built in a later stage.")
