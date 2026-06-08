"""Purchaser screen: confirm actual litres against the physical receipt."""

import streamlit as st

from db import get_for_confirmation_requisitions, confirm_requisition


def confirm(email):
    rows = get_for_confirmation_requisitions()
    if rows.empty:
        st.info("No requests are awaiting confirmation.")
        return

    for r in rows.itertuples():
        amount = float(r.amount) if r.amount is not None else 0.0
        with st.expander(f"#{r.id} · {r.asset} · {amount:,.2f}"):
            st.write(f"**Requested by:** {r.requested_by}")
            st.write(f"**Request date:** {r.request_date}")
            st.write(f"**Requested litres:** {float(r.requested_liters):g}")
            st.write(f"**Actual litres:** {float(r.actual_liters):g}")
            st.write(f"**Date drawn:** {r.drawn_date}")
            st.write(f"**Unit price:** {float(r.unit_price):.2f}")
            st.write(f"**Amount:** {amount:,.2f}")
            st.write(f"**Receipt no.:** {r.receipt_no or '—'}")
            if st.button("Confirm", key=f"confirm_{r.id}", type="primary"):
                confirm_requisition(r.id, email)
                st.success(f"Requisition #{r.id} confirmed.")
                st.rerun()
