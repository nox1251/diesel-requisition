"""User screens: create a requisition and review my requests."""

import datetime as dt

import streamlit as st

from db import (
    get_active_assets,
    create_requisition,
    get_my_requisitions,
    get_my_approved_requisitions,
    get_price_for_date,
    update_actual,
)

STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
    "for_confirmation": "For confirmation",
    "confirmed": "Confirmed",
    "billed": "Billed",
}


def new_requisition(username):
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
        create_requisition(username, asset_id, liters, purpose.strip() or None, request_date)
        st.success("Requisition submitted and is now pending approval.")


def my_requests(username):
    rows = get_my_requisitions(username)
    if rows.empty:
        st.info("You haven't submitted any requisitions yet.")
        return

    rows = rows.copy()
    rows["status"] = rows["status"].map(STATUS_LABELS).fillna(rows["status"])
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "request_date": "Date",
            "asset": "Asset",
            "requested_liters": "Litres",
            "purpose": "Purpose",
            "status": "Status",
            "actual_liters": "Actual",
            "drawn_date": "Drawn",
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            "reject_reason": "Reject reason",
        },
    )


def encode_actual(username):
    rows = get_my_approved_requisitions(username)
    if rows.empty:
        st.info("You have no approved requests awaiting actual litres.")
        return

    for r in rows.itertuples():
        title = f"#{r.id} · {r.asset} · requested {float(r.requested_liters):g} L"
        with st.expander(title):
            st.write(f"**Request date:** {r.request_date}")
            st.write(f"**Purpose:** {r.purpose or '—'}")
            with st.form(f"actual_{r.id}", clear_on_submit=True):
                actual = st.number_input(
                    "Actual litres drawn", min_value=0.0, step=1.0, key=f"al_{r.id}"
                )
                drawn = st.date_input(
                    "Date drawn", value=dt.date.today(), key=f"dd_{r.id}"
                )
                receipt = st.text_input("Receipt no. (optional)", key=f"rn_{r.id}")
                submitted = st.form_submit_button("Submit actual")
            if submitted:
                if actual <= 0:
                    st.error("Actual litres must be greater than zero.")
                    continue
                price = get_price_for_date(drawn)
                if price is None:
                    st.error(
                        f"No diesel price is set for {drawn}. Ask the Purchaser to "
                        "set the price for that day, then try again."
                    )
                    continue
                update_actual(r.id, username, actual, drawn, receipt.strip() or None, price)
                st.success(
                    f"Recorded {float(actual):g} L at {float(price):.2f}/L "
                    "— sent for confirmation."
                )
                st.rerun()
