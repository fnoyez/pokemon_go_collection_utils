import datetime
import urllib.error

import streamlit as st

from pokemon_go_collection import secret_files as secret_files_m
from pokemon_go_collection.services import (
    pogocoordinates_login as pogocoordinates_login_m,
)
from pokemon_go_collection.services import spawn_watch as spawn_watch_m
from pokemon_go_collection.sources import discord as discord_m


def render_spawn_watch_page(cfg, check_lock):
    st.header("Spawn watch")
    st.caption(
        "While on, the watch searches pogocoordinates.com at the set interval for "
        "spawns that will be shundos for your account and are on the hunt list, and "
        "posts each new one to Discord with its coordinates."
    )
    login_column, discord_column = st.columns(2)
    with login_column:
        _render_login(cfg)
    with discord_column:
        _render_discord_settings(cfg)
    _render_watch_settings(cfg.db_file_path)
    _render_manual_check(cfg, check_lock)
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
    # The widgets show the stored settings, which the watch itself changes when
    # a login is refused, and store a change as soon as it is made.
    config = spawn_watch_m.load_watch_config(db_file_path)
    st.session_state["watch_is_enabled"] = config.is_enabled
    st.session_state["watch_is_costume_search_enabled"] = (
        config.is_costume_search_enabled
    )
    st.session_state["watch_check_interval_minutes_nb"] = int(
        config.check_interval_duration.total_seconds() // 60
    )
    min_interval_minutes_nb = int(
        spawn_watch_m.MIN_CHECK_INTERVAL_DURATION.total_seconds() // 60
    )
    st.toggle(
        "Watch on",
        key="watch_is_enabled",
        on_change=_save_watch_settings,
        args=(db_file_path,),
    )
    st.toggle(
        "Search costumed Pokémon too",
        key="watch_is_costume_search_enabled",
        on_change=_save_watch_settings,
        args=(db_file_path,),
        help=(
            "Adds the costumed shundos of the Costumed shundos tab to the search, "
            "those whose costume spawns now only."
        ),
    )
    st.number_input(
        "Check interval (minutes)",
        min_value=min_interval_minutes_nb,
        step=1,
        key="watch_check_interval_minutes_nb",
        on_change=_save_watch_settings,
        args=(db_file_path,),
    )
    st.caption(
        "A check starts within 30 seconds of turning the watch on, unless the last "
        "one is more recent than the interval."
    )


def _save_watch_settings(db_file_path):
    spawn_watch_m.save_watch_config(
        db_file_path,
        st.session_state["watch_is_enabled"],
        datetime.timedelta(minutes=st.session_state["watch_check_interval_minutes_nb"]),
        st.session_state["watch_is_costume_search_enabled"],
    )


def _render_manual_check(cfg, check_lock):
    if st.button(
        "Check now",
        help=(
            "Checks once, now, whether the watch is on or not and however recent "
            "the last check; the watch's next check then waits an interval after it."
        ),
    ):
        with st.spinner("Checking..."):
            outcome = spawn_watch_m.run_spawn_check_unless_busy(
                cfg, check_lock, datetime.datetime.now(datetime.timezone.utc)
            )
        if outcome is None:
            st.info("A check is already running: its result will show below.")
        elif outcome.status == spawn_watch_m.CheckStatus.SUCCESS:
            st.success("Check done.")
        else:
            st.error(
                f"The check ended with the status {outcome.status.value}: see its "
                "note below."
            )


@st.fragment(run_every=datetime.timedelta(seconds=30))
def _render_watch_records(db_file_path):
    st.subheader("Recent alerts")
    alerts = spawn_watch_m.load_recent_alerts(db_file_path)
    if alerts:
        st.dataframe(
            [
                {
                    **alert,
                    "alert_time": _format_local_time(alert["alert_time"]),
                    "despawn_time": _format_local_time(alert["despawn_time"]),
                }
                for alert in alerts
            ],
            hide_index=True,
            column_config={
                "reveal_url": st.column_config.LinkColumn("reveal", display_text="Open")
            },
        )
    else:
        st.caption("No alert yet.")
    st.subheader("Recent checks")
    checks = spawn_watch_m.load_recent_checks(db_file_path)
    if checks:
        st.dataframe(
            [
                {**check, "check_time": _format_local_time(check["check_time"])}
                for check in checks
            ],
            hide_index=True,
        )
    else:
        st.caption("No check yet.")


def _format_local_time(iso_time_text):
    """Return a stored time in the computer's time zone, to the second, with its offset."""
    return (
        datetime.datetime.fromisoformat(iso_time_text)
        .astimezone()
        .isoformat(sep=" ", timespec="seconds")
    )
