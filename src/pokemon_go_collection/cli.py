import argparse
import datetime
import logging
import pathlib

from pokemon_go_collection import config as config_m
from pokemon_go_collection import logging_setup as logging_setup_m
from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection.services import backups as backups_m
from pokemon_go_collection.services import refresh as refresh_m


def main_init():
    args = _parse_args(
        "pgcollection-init", "Initialize the application folders and database"
    )
    cfg = _load_config(args)
    migrate_m.init_db(cfg.db_file_path, backup_folder_path=cfg.backup_folder_path)
    print(f"Initialized DB at {cfg.db_file_path}")


def _parse_args(program_name, description):
    parser = argparse.ArgumentParser(
        prog=program_name, description=description, allow_abbrev=False
    )
    parser.add_argument(
        "--app-home-folder-path", default=str(config_m.DEFAULT_APP_HOME_FOLDER_PATH)
    )
    parser.add_argument(
        "--backup-folder-path", default=str(config_m.DEFAULT_BACKUP_FOLDER_PATH)
    )
    args = parser.parse_args()
    logging_setup_m.setup_logging(logging_level=logging.INFO)
    return args


def _load_config(args):
    return config_m.load_config(
        pathlib.Path(args.app_home_folder_path),
        pathlib.Path(args.backup_folder_path),
        config_m.REPOSITORY_FOLDER_PATH,
    )


def main_backup():
    args = _parse_args("pgcollection-backup", "Take a backup and enforce retention")
    cfg = _load_config(args)
    backup_file_path = backups_m.create_sqlite_backup(
        cfg.db_file_path, cfg.backup_folder_path
    )
    backups_m.record_backup_event(
        cfg.db_file_path, backup_file_path, "daily", "success", "manual"
    )
    backups_m.enforce_retention(cfg.db_file_path)
    print(f"Backup created at {backup_file_path}")


def main_refresh():
    args = _parse_args("pgcollection-refresh", "Refresh the catalog from its sources")
    cfg = _load_config(args)
    migrate_m.init_db(cfg.db_file_path, backup_folder_path=cfg.backup_folder_path)
    outcome = refresh_m.run_refresh(cfg, datetime.datetime.now(datetime.timezone.utc))
    print(f"Catalog refreshed: {outcome.entries_nb} entries")
