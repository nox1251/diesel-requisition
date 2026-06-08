"""Admin screen: manage users — their roles and login passwords."""

import streamlit as st
import streamlit_authenticator as stauth

from db import get_all_users, add_or_update_user, delete_user

ROLES = ["user", "manager", "purchaser", "admin"]
NEW_USER = "(new user)"


def manage_users(current_username):
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
            width="stretch",
            column_config={
                "username": "Username",
                "display_name": "Name",
                "roles": "Roles",
                "has_login": "Can log in",
            },
        )

    st.divider()
    st.subheader("Add or update a user")

    usernames = list(users["username"]) if not users.empty else []
    choice = st.selectbox("Edit existing or add new", [NEW_USER] + usernames)
    editing = choice != NEW_USER
    if editing:
        row = users[users["username"] == choice].iloc[0]
        default_name = row["display_name"] or ""
        default_roles = list(row["roles"])
    else:
        default_name, default_roles = "", []

    # Key widgets by the selection so they refill when a different user is picked.
    with st.form(f"manage_user_{choice}"):
        username = st.text_input(
            "Username", value=choice if editing else "", disabled=editing
        )
        display_name = st.text_input("Display name", value=default_name)
        roles = st.multiselect("Roles", ROLES, default=default_roles)
        password = st.text_input(
            "Password (blank = keep existing)" if editing else "Password",
            type="password",
        )
        submitted = st.form_submit_button("Save user")

    if submitted:
        target = choice if editing else username.strip()
        if not target:
            st.error("Username is required.")
            return
        if not editing and not password:
            st.error("A password is required to create a new user.")
            return
        password_hash = stauth.Hasher.hash(password) if password else None
        add_or_update_user(target, display_name.strip() or None, roles, password_hash)
        st.success(f"Saved user '{target}'.")
        st.rerun()

    if editing:
        st.divider()
        st.subheader("Delete user")
        admin_count = sum(1 for r in users.itertuples() if "admin" in r.roles)
        target_is_admin = "admin" in default_roles
        if choice == current_username:
            st.caption("You can't delete the account you're logged in as.")
        elif target_is_admin and admin_count <= 1:
            st.caption("You can't delete the last admin.")
        else:
            confirm = st.checkbox(f"Yes, permanently delete '{choice}'")
            if st.button("Delete user", disabled=not confirm):
                delete_user(choice)
                st.success(f"Deleted '{choice}'.")
                st.rerun()
