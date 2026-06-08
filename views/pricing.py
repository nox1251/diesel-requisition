"""Purchaser screen: set the diesel price for a date."""

import datetime as dt

import streamlit as st

from db import get_price_for_date, set_daily_price


def pricing(username):
    price_date = st.date_input("Price date", value=dt.date.today())
    existing = get_price_for_date(price_date)
    if existing is not None:
        st.info(f"Price already set for {price_date}: {float(existing):.2f} per litre.")
    else:
        st.caption(f"No price set for {price_date} yet.")

    # Key by date so the field resets to the stored price when the date changes.
    price = st.number_input(
        "Price per litre",
        min_value=0.0,
        step=0.01,
        value=float(existing) if existing is not None else 0.0,
        key=f"price_{price_date}",
    )
    if st.button("Save price", type="primary"):
        if price <= 0:
            st.error("Price must be greater than zero.")
            return
        set_daily_price(price_date, price, username)
        st.success(f"Price for {price_date} set to {price:.2f} per litre.")
        st.rerun()
