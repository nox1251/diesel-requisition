"""Admin screen: manage users — their roles and login passwords."""

import streamlit as st
import streamlit_authenticator as stauth

from db import get_all_users, add_or_update_user

ROLES = ["user", "manager", "purchaser", "admin"]


def manage_users():
    users = get_all_users()

    st.subheader("Users")
    if users.empty:
        st.info("No users yet.")
    else:
        show = users.copy()
        show["roles"] = show["roles"].apply(lambda r: ", ".join(r) if len(r) else "—")
        show["has_login"] = show["has_login"].map({True: "yes", False: "no"})
        st.dataframe(
            show,
            hide_index=True,
            use_container_width=True,
            column_config={
                "username": "Username",
                "display_name": "Name",
                "roles": "Roles",
                "has_login": "Can log in",
            },
        )

    st.divider()
    st.subheader("Add or update a user")
    st.caption(
        "Existing username updates that user. Leave the password blank to keep "
        "their current one; set a password to create a login or reset it."
    )
    existing_usernames = set(users["username"]) if not users.empty else set()

    with st.form("manage_user", clear_on_submit=True):
        username = st.text_input("Username")
        display_name = st.text_input("Display name")
        roles = st.multiselect("Roles", ROLES)
        password = st.text_input(
            "Password (blank = keep existing)", type="password"
        )
        submitted = st.form_submit_button("Save user")

    if submitted:
        username = username.strip()
        if not username:
            st.error("Username is required.")
            return
        is_new = username not in existing_usernames
        if is_new and not password:
            st.error("A password is required to create a new user.")
            return
        password_hash = stauth.Hasher.hash(password) if password else None
        add_or_update_user(username, display_name.strip() or None, roles, password_hash)
        st.success(f"Saved user '{username}'.")
        st.rerun()
