"""Master data: propose a new asset; admins approve or reject proposals."""

import streamlit as st

from db import propose_asset, get_pending_assets, approve_asset, reject_asset

ASSET_TYPES = ["vehicle", "generator", "equipment"]


def master_data(username, is_admin):
    st.subheader("Propose a new asset")
    with st.form("propose_asset", clear_on_submit=True):
        name = st.text_input("Asset name")
        asset_type = st.selectbox("Type", ASSET_TYPES)
        submitted = st.form_submit_button("Propose asset")
    if submitted:
        if not name.strip():
            st.error("Asset name is required.")
        else:
            propose_asset(name.strip(), asset_type, username)
            st.success(
                f"Proposed '{name.strip()}'. It awaits admin approval before it "
                "can be used in a requisition."
            )

    st.divider()
    pending = get_pending_assets()

    if is_admin:
        st.subheader("Assets awaiting approval")
        if pending.empty:
            st.info("No assets are awaiting approval.")
            return
        for a in pending.itertuples():
            with st.expander(f"#{int(a.id)} · {a.name} · {a.asset_type}"):
                st.write(f"**Proposed by:** {a.proposed_by}")
                st.write(f"**Proposed at:** {a.proposed_at:%Y-%m-%d %H:%M}")
                approve_col, reject_col = st.columns(2)
                if approve_col.button("Approve", key=f"appr_{a.id}", type="primary"):
                    approve_asset(a.id, username)
                    st.success(f"'{a.name}' is now active.")
                    st.rerun()
                if reject_col.button("Reject", key=f"rej_{a.id}"):
                    reject_asset(a.id, username)
                    st.warning(f"'{a.name}' was rejected.")
                    st.rerun()
    elif not pending.empty:
        st.subheader("Pending assets (awaiting admin approval)")
        st.dataframe(
            pending[["name", "asset_type", "proposed_by"]],
            hide_index=True,
            width="stretch",
            column_config={
                "name": "Name",
                "asset_type": "Type",
                "proposed_by": "Proposed by",
            },
        )
