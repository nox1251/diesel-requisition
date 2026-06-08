"""Purchaser screens: group confirmed requests into a billing and view the
bill payment request."""

import streamlit as st

from db import (
    get_billable_requisitions,
    create_billing,
    get_billings,
    get_billing_lines,
)


def billing(username):
    create_tab, view_tab = st.tabs(["Create billing", "Bill payment request"])
    with create_tab:
        _create_billing(username)
    with view_tab:
        _view_billings()


def _create_billing(username):
    rows = get_billable_requisitions()
    if rows.empty:
        st.info("No confirmed requests are awaiting billing.")
        return

    display = rows.copy()
    display["amount"] = display["amount"].astype(float)
    st.caption("Confirmed requests not yet billed:")
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": "ID",
            "request_date": "Requested",
            "requested_by": "By",
            "asset": "Asset",
            "drawn_date": "Drawn",
            "actual_liters": "Actual",
            "unit_price": st.column_config.NumberColumn("Unit price", format="%.2f"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        },
    )

    labels = {
        int(r.id): f"#{int(r.id)} · {r.asset} · {float(r.amount):,.2f}"
        for r in rows.itertuples()
    }
    selected = st.multiselect(
        "Select requests to include in this billing",
        options=list(labels),
        format_func=lambda i: labels[i],
    )
    supplier_ref = st.text_input("Supplier invoice reference (optional)")
    note = st.text_area("Note (optional)")
    if st.button("Create billing", type="primary"):
        if not selected:
            st.error("Select at least one request.")
            return
        billing_id = create_billing(
            username, selected, supplier_ref.strip() or None, note.strip() or None
        )
        st.success(f"Billing #{billing_id} created with {len(selected)} request(s).")
        st.rerun()


def _view_billings():
    billings = get_billings()
    if billings.empty:
        st.info("No billings yet.")
        return

    labels = {
        int(b.id): f"#{int(b.id)} · {b.created_at:%Y-%m-%d} · {float(b.total):,.2f}"
        for b in billings.itertuples()
    }
    billing_id = st.selectbox(
        "Select a billing", options=list(labels), format_func=lambda i: labels[i]
    )
    header = billings[billings["id"] == billing_id].iloc[0]

    st.subheader(f"Bill Payment Request — Billing #{billing_id}")
    st.write(f"**Created:** {header['created_at']:%Y-%m-%d %H:%M} by {header['created_by']}")
    if header["supplier_ref"]:
        st.write(f"**Supplier reference:** {header['supplier_ref']}")
    if header["note"]:
        st.write(f"**Note:** {header['note']}")

    lines = get_billing_lines(billing_id).copy()
    lines["amount"] = lines["amount"].astype(float)
    st.dataframe(
        lines,
        hide_index=True,
        use_container_width=True,
        column_config={
            "drawn_date": "Drawn",
            "asset": "Asset",
            "requested_by": "By",
            "receipt_no": "Receipt no.",
            "actual_liters": "Litres",
            "unit_price": st.column_config.NumberColumn("Unit price", format="%.2f"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        },
    )
    st.metric("Total", f"{lines['amount'].sum():,.2f}")
