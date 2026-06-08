"""Manager screen: approve or reject pending requisitions."""

import streamlit as st

from db import get_pending_requisitions, approve_requisition, reject_requisition


def approvals(username):
    rows = get_pending_requisitions()
    if rows.empty:
        st.info("No requisitions are awaiting approval.")
        return

    for r in rows.itertuples():
        liters = f"{float(r.requested_liters):g}"
        with st.expander(f"#{r.id} · {r.asset} · {liters} L · {r.requested_by}"):
            st.write(f"**Request date:** {r.request_date}")
            st.write(f"**Requested by:** {r.requested_by}")
            st.write(f"**Asset:** {r.asset}")
            st.write(f"**Requested litres:** {liters}")
            st.write(f"**Purpose:** {r.purpose or '—'}")

            reason = st.text_input("Rejection reason", key=f"reason_{r.id}")
            approve_col, reject_col = st.columns(2)
            if approve_col.button("Approve", key=f"approve_{r.id}", type="primary"):
                approve_requisition(r.id, username)
                st.success(f"Requisition #{r.id} approved.")
                st.rerun()
            if reject_col.button("Reject", key=f"reject_{r.id}"):
                if not reason.strip():
                    st.error("Please enter a reason before rejecting.")
                else:
                    reject_requisition(r.id, username, reason.strip())
                    st.warning(f"Requisition #{r.id} rejected.")
                    st.rerun()
