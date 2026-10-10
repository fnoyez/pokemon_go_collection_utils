import datetime
import urllib.error

import streamlit as st

from pokemon_go_collection import secret_files as secret_files_m
from pokemon_go_collection.services import (
    pogocoordinates_login as pogocoordinates_login_m,
)
from pokemon_go_collection.services import spawn_watch as spawn_watch_m
from pokemon_go_collection.sources import discord as discord_m


def render_spawn_watch_page(cfg):
    st.header("Spawn watch")
    st.caption(
        "While on, the watch searches pogocoordinates.com at the set interval for "
        "spawns that will be shundos for your account and are on the hunt list, and "
        "posts each new one to Discord with its coordinates link."
    )
    login_column, discord_column = st.columns(2)
    with login_column:
        _render_login(cfg)
    with discord_column:
        _render_discord_settings(cfg)
    _render_watch_settings(cfg.db_file_path)
    _render_watch_records(cfg.db_file_path)


def _render_login(cfg):
    st.subheader("pogocoordinates.com login")
    token = secret_files_m.read_secret(cfg.pogocoordinates_token_file_path)
    last_checks = spawn_watch_m.load_recent_checks(cfg.db_file_path, checks_nb=1)
    is_refused = (
        bool(last_checks)
        and last_checks[0]["status"] == spawn_watch_m.CheckStatus.UNAUTHORIZED.value
    )
    if token is None:
        st.caption("Not logged in.")
    elif is_refused:
        st.caption("The last check was refused for its login: log in again.")
    else:
        st.caption("Logged in.")
    if st.button("Log in"):
        with st.spinner(
            "Waiting for the login in the Chrome window: log in with Discord there."
        ):
            try:
                account_name = pogocoordinates_login_m.log_in_with_browser(
                    cfg.login_browser_profile_folder_path,
                    cfg.pogocoordinates_token_file_path,
                )
            except TimeoutError as error:
                st.error(str(error))
            else:
                st.success(f"Logged in as {account_name}.")


def _render_discord_settings(cfg):
    st.subheader("Discord")
    webhook_url = secret_files_m.read_secret(cfg.discord_webhook_url_file_path)
    st.caption("Webhook set." if webhook_url else "No webhook set.")
    with st.form("discord_webhook_form", clear_on_submit=True):
        new_webhook_url = st.text_input("New webhook URL", type="password")
        if st.form_submit_button("Save") and new_webhook_url.strip():
            secret_files_m.write_secret(
                cfg.discord_webhook_url_file_path, new_webhook_url.strip()
            )
            st.success("Webhook saved.")
            webhook_url = new_webhook_url.strip()
    if st.button("Send a test message", disabled=webhook_url is None):
        try:
            discord_m.post_webhook_message(
                webhook_url, "Test message from the spawn watch."
            )
        except urllib.error.URLError as error:
            st.error(f"The message was not sent: {error}")
        else:
            st.success("Test message sent.")


def _render_watch_settings(db_file_path):
    st.subheader("Watch")
    config = spawn_watch_m.load_watch_config(db_file_path)
    min_interval_minutes_nb = int(
        spawn_watch_m.MIN_CHECK_INTERVAL_DURATION.total_seconds() // 60
    )
    is_enabled = st.toggle("Watch on", value=config.is_enabled)
    check_interval_minutes_nb = st.number_input(
        "Check interval (minutes)",
        min_value=min_interval_minutes_nb,
        value=int(config.check_interval_duration.total_seconds() // 60),
        step=1,
    )
    check_interval_duration = datetime.timedelta(minutes=check_interval_minutes_nb)
    if (is_enabled, check_interval_duration) != (
        config.is_enabled,
        config.check_interval_duration,
    ):
        spawn_watch_m.save_watch_config(
            db_file_path, is_enabled, check_interval_duration
        )
    st.caption(
        "A check starts within 30 seconds of turning the watch on, unless the last "
        "one is more recent than the interval."
    )


@st.fragment(run_every=datetime.timedelta(seconds=30))
def _render_watch_records(db_file_path):
    st.subheader("Recent alerts")
    alerts = spawn_watch_m.load_recent_alerts(db_file_path)
    if alerts:
        st.dataframe(
            alerts,
            hide_index=True,
            column_config={
                "coordinates": st.column_config.LinkColumn(display_text="Open")
            },
        )
    else:
        st.caption("No alert yet.")
    st.subheader("Recent checks")
    checks = spawn_watch_m.load_recent_checks(db_file_path)
    if checks:
        st.dataframe(checks, hide_index=True)
    else:
        st.caption("No check yet.")
