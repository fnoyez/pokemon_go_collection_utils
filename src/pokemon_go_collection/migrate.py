import importlib
import logging
import pathlib
import sqlite3

from pokemon_go_collection.services import backups as backups_m

logger = logging.getLogger(__name__)

# None of the three below is a parameter: each is a declaration a caller must
# not be able to substitute -- the folder the migrations sit in, the table that
# proves a database is populated, and a column value SQLite's own CHECK constrains.

_MIGRATIONS_PACKAGE_NAME = "migrations"

# The table whose presence tells a populated database from an empty file.
_POPULATED_WITNESS_TABLE_NAME = "pokemon_entry"

# `backup_event.retention` accepts only the auto-backup classes, and retention
# reads it for `source = 'auto'` rows alone, so the class recorded here is inert.
_MIGRATION_BACKUP_RETENTION = "daily"


def init_db(db_file_path, backup_folder_path=None):
    """Bring the database at `db_file_path` to the schema the migrations describe.

    Creates the file when it is absent, and applies every migration it has not
    already recorded. When `backup_folder_path` is given and a populated
    database has work pending, a backup is taken first and logged with source
    'migration', which retention never prunes: that backup is the revert path
    for a migration that goes wrong.

    Runs on every page render, so the settled case costs one SELECT.
    """
    migration_names = _discover_migration_names()

    conn = sqlite3.connect(db_file_path, isolation_level=None)
    try:
        _ensure_schema_migration_table(conn)

        # Read once outside the lock to keep the settled case cheap; the
        # authoritative read happens under BEGIN IMMEDIATE below, so two
        # processes arriving together still apply each migration once.
        if not _find_pending_migration_names(conn, migration_names):
            return

        if backup_folder_path is not None and _table_exists(
            conn, _POPULATED_WITNESS_TABLE_NAME
        ):
            _back_up_before_migrating(db_file_path, backup_folder_path)

        _apply_pending_migrations(conn, migration_names)
    finally:
        conn.close()


def _discover_migration_names():
    """Return the migration module names, sorted, which is their apply order."""
    migrations_folder_path = pathlib.Path(__file__).parent / _MIGRATIONS_PACKAGE_NAME
    return sorted(
        file_path.stem
        for file_path in migrations_folder_path.glob("*.py")
        if file_path.name != "__init__.py"
    )


def _ensure_schema_migration_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
          name          TEXT PRIMARY KEY,
          applied_time  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'))
        )
        """
    )


def _find_pending_migration_names(conn, migration_names):
    """Return the migrations, in order, whose name the database has not recorded."""
    rows = conn.execute(
        """
        SELECT name
        FROM schema_migration
        """
    )
    applied_names = {row[0] for row in rows}
    return [name for name in migration_names if name not in applied_names]


def _table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _back_up_before_migrating(db_file_path, backup_folder_path):
    backup_file_path = backups_m.create_sqlite_backup(db_file_path, backup_folder_path)
    backups_m.record_backup_event(
        db_file_path,
        backup_file_path,
        _MIGRATION_BACKUP_RETENTION,
        "success",
        "migration",
        note="Taken before applying pending migrations",
    )
    logger.info(f"Pre-migration backup created: {backup_file_path}")


def _apply_pending_migrations(conn, migration_names):
    """Apply every unrecorded migration, in order, in one transaction.

    Foreign keys are disabled around the transaction because a migration may
    rebuild a table, and SQLite ignores the pragma while a transaction is open.
    `foreign_key_check` before the commit replaces the enforcement the pragma
    would have given.
    """
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN IMMEDIATE")
    try:
        for name in _find_pending_migration_names(conn, migration_names):
            logger.info(f"Applying migration {name}")
            module = importlib.import_module(
                f".{_MIGRATIONS_PACKAGE_NAME}.{name}", __package__
            )
            module.upgrade(conn)
            conn.execute(
                """
                INSERT INTO schema_migration (name)
                VALUES (?)
                """,
                (name,),
            )
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(
                f"Migrations left {len(violations)} foreign key violation(s): "
                f"{violations[:5]}"
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
