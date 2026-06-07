"""User screens: create a requisition and review my requests."""

import datetime as dt

import streamlit as st

from db import get_active_assets, create_requisition, get_my_requisitions

STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
    "for_confirmation": "For confirmation",
    "confirmed": "Confirmed",
    "billed": "Billed",
}


def new_requisition(email):
    assets = get_active_assets()
    if assets.empty:
        st.info("No active assets yet. Ask an admin to add one before requesting fuel.")
        return

    names = dict(zip(assets["id"], assets["name"]))
    with st.form("new_requisition", clear_on_submit=True):
        request_date = st.date_input("Request date", value=dt.date.today())
        asset_id = st.selectbox(
            "Asset", options=list(names), format_func=lambda i: names[i]
        )
        liters = st.number_input("Requested litres", min_value=0.0, step=1.0)
        purpose = st.text_area("Purpose")
        submitted = st.form_submit_button("Submit requisition")

    if submitted:
        if liters <= 0:
            st.error("Requested litres must be greater than zero.")
            return
        create_requisition(email, asset_id, liters, purpose.strip() or None, request_date)
        st.success("Requisition submitted and is now pending approval.")


def my_requests(email):
    rows = get_my_requisitions(email)
    if rows.empty:
        st.info("You haven't submitted any requisitions yet.")
        return

    rows = rows.copy()
    rows["status"] = rows["status"].map(STATUS_LABELS).fillna(rows["status"])
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        column_config={
            "request_date": "Date",
            "asset": "Asset",
            "requested_liters": "Litres",
            "purpose": "Purpose",
            "status": "Status",
            "reject_reason": "Reject reason",
        },
    )
