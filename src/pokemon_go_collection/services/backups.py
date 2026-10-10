import datetime
import logging
import pathlib
import sqlite3

from pokemon_go_collection import db as db_m

logger = logging.getLogger(__name__)


def run_auto_backup(
    db_file_path,
    backup_folder_path,
    kept_daily_backups_nb=30,
    kept_monthly_backups_nb=12,
    kept_yearly_backups_nb=5,
):
    """Create one auto backup per day (idempotent), then enforce retention."""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    with db_m.db_conn(db_file_path) as conn:
        already_done = conn.execute(
            """
            SELECT 1 FROM backup_event
            WHERE source = 'auto' AND status = 'success' AND run_time LIKE ?
            LIMIT 1
            """,
            (f"{today}%",),
        ).fetchone()
    if already_done:
        return

    backup_file_path = create_sqlite_backup(db_file_path, backup_folder_path)
    record_backup_event(db_file_path, backup_file_path, "daily", "success", "auto")
    enforce_retention(
        db_file_path,
        kept_daily_backups_nb=kept_daily_backups_nb,
        kept_monthly_backups_nb=kept_monthly_backups_nb,
        kept_yearly_backups_nb=kept_yearly_backups_nb,
    )
    logger.info(f"Auto backup created: {backup_file_path}")


def create_sqlite_backup(db_file_path, backup_folder_path):
    """Copy the database with SQLite's backup API, which is safe while it is in use."""
    backup_folder_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = backup_folder_path / f"pokemon_go_collection_{timestamp}.sqlite"

    source_conn = sqlite3.connect(db_file_path)
    try:
        backup_conn = sqlite3.connect(backup_file_path)
        try:
            source_conn.backup(backup_conn)
        finally:
            backup_conn.close()
    finally:
        source_conn.close()

    return backup_file_path


def record_backup_event(
    db_file_path,
    backup_file_path,
    retention,
    status,
    source,
    note=None,
):
    size = backup_file_path.stat().st_size if backup_file_path.exists() else None
    run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            INSERT INTO backup_event (run_time, backup_path, size, retention, status, source, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_time, str(backup_file_path), size, retention, status, source, note),
        )


def enforce_retention(
    db_file_path,
    kept_daily_backups_nb=30,
    kept_monthly_backups_nb=12,
    kept_yearly_backups_nb=5,
):
    """Delete auto backups beyond the retention policy; other backups are never touched."""
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT backup_path, run_time FROM backup_event
            WHERE source = 'auto' AND status = 'success'
            ORDER BY run_time ASC
            """
        ).fetchall()
    auto_backups = [(pathlib.Path(row[0]), row[1]) for row in rows]

    kept_file_paths = {
        file_path for file_path, _ in auto_backups[-kept_daily_backups_nb:]
    }
    # The first auto backup of each month, and of each year, for the most recent ones.
    for period_length, kept_periods_nb in (
        (len("YYYY-MM"), kept_monthly_backups_nb),
        (len("YYYY"), kept_yearly_backups_nb),
    ):
        first_file_paths_by_period = {}
        for file_path, run_time in auto_backups:
            first_file_paths_by_period.setdefault(run_time[:period_length], file_path)
        for period in sorted(first_file_paths_by_period)[-kept_periods_nb:]:
            kept_file_paths.add(first_file_paths_by_period[period])

    for file_path, _ in auto_backups:
        if file_path not in kept_file_paths and file_path.exists():
            logger.info(f"Retention: deleting {file_path}")
            file_path.unlink()


def load_recent_backup_events(db_file_path, events_nb=20):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT run_time, backup_path, size, source, status
            FROM backup_event
            ORDER BY run_time DESC
            LIMIT ?
            """,
            (events_nb,),
        ).fetchall()
    return [
        {
            "run_time": row[0],
            "backup_path": row[1],
            "size": row[2],
            "source": row[3],
            "status": row[4],
        }
        for row in rows
    ]
