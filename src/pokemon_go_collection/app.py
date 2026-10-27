import datetime
import logging
import threading

import streamlit as st

from pokemon_go_collection import config as config_m
from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection import ui_pvp_ranks as ui_pvp_ranks_m
from pokemon_go_collection import ui_shundos as ui_shundos_m
from pokemon_go_collection import ui_spawn_watch as ui_spawn_watch_m
from pokemon_go_collection.services import backups as backups_m
from pokemon_go_collection.services import refresh as refresh_m
from pokemon_go_collection.services import spawn_watch as spawn_watch_m

logger = logging.getLogger(__name__)


def main():
    st.set_page_config(page_title="Pokémon GO Collection", layout="wide")

    try:
        cfg = config_m.load_config(
            config_m.DEFAULT_APP_HOME_FOLDER_PATH,
            config_m.DEFAULT_BACKUP_FOLDER_PATH,
            config_m.REPOSITORY_FOLDER_PATH,
        )
        migrate_m.init_db(cfg.db_file_path, backup_folder_path=cfg.backup_folder_path)
    except Exception as error:
        st.error(f"Startup error: {error}")
        return

    backups_m.run_auto_backup(cfg.db_file_path, cfg.backup_folder_path)
    check_lock = _start_spawn_watch(cfg)
    if refresh_m.is_refresh_due(
        cfg.db_file_path,
        cfg.refresh_period_duration,
        datetime.datetime.now(datetime.timezone.utc),
    ):
        _run_refresh(cfg)

    with st.sidebar:
        _render_sidebar(cfg)

    st.title("Pokémon GO Collection")
    shundos_tab, costumed_shundos_tab, spawn_watch_tab, pvp_ranks_tab = st.tabs(
        ["Shundos", "Costumed shundos", "Spawn watch", "PvP ranks"]
    )
    with shundos_tab:
        ui_shundos_m.render_shundos_page(cfg.db_file_path, cfg.icons_folder_path)
    with costumed_shundos_tab:
        ui_shundos_m.render_costumed_shundos_page(
            cfg.db_file_path, cfg.icons_folder_path
        )
    with spawn_watch_tab:
        ui_spawn_watch_m.render_spawn_watch_page(cfg, check_lock)
    with pvp_ranks_tab:
        ui_pvp_ranks_m.render_pvp_ranks_page(cfg.db_file_path)


# Cached as a resource, the watch starts once per server process and runs as
# long as it does. The leading underscore keeps the argument out of the cache key.
# The lock it returns is held by the check running, from the watch or the tab.
@st.cache_resource
def _start_spawn_watch(_cfg):
    check_lock = threading.Lock()
    stop_event = threading.Event()
    threading.Thread(
        target=spawn_watch_m.run_spawn_watch_loop,
        args=(_cfg, check_lock, stop_event),
        name="spawn-watch",
        daemon=True,
    ).start()
    logger.info("Spawn watch started")
    return check_lock


def _run_refresh(cfg):
    with st.spinner("Refreshing the catalog from its sources..."):
        try:
            outcome = refresh_m.run_refresh(
                cfg, datetime.datetime.now(datetime.timezone.utc)
            )
        except Exception as error:
            logger.exception("Catalog refresh failed")
            st.error(f"Catalog refresh failed: {error}")
            return
    for warning in outcome.warnings:
        st.warning(warning)


def _render_sidebar(cfg):
    st.subheader("Catalog")
    last_refresh = refresh_m.load_last_refresh(cfg.db_file_path)
    if last_refresh is None:
        st.caption("Never refreshed.")
    else:
        caption_parts = [
            f"Last refresh: {_format_utc_time(last_refresh['end_time'])}, {last_refresh['status']}."
        ]
        if last_refresh["game_master_timestamp"] is not None:
            caption_parts.append(
                f"Game master of {_format_utc_time(last_refresh['game_master_timestamp'])}."
            )
        st.caption(" ".join(caption_parts))
    if st.button("Refresh now"):
        _run_refresh(cfg)
        st.rerun()

    st.subheader("Backups")
    if st.button("Backup now"):
        backup_file_path = backups_m.create_sqlite_backup(
            cfg.db_file_path, cfg.backup_folder_path
        )
        backups_m.record_backup_event(
            cfg.db_file_path, backup_file_path, "daily", "success", "manual"
        )
        st.success(f"Backup created: {backup_file_path.name}")
    with st.expander("Recent backups"):
        st.dataframe(
            backups_m.load_recent_backup_events(cfg.db_file_path),
            hide_index=True,
        )


def _format_utc_time(iso_time):
    return f"{iso_time[:16].replace('T', ' ')} UTC"
