"""The schema in full: every table the application reads."""


def upgrade(conn):
    statements = (
        """
        CREATE TABLE pokemon_entry (
          entry_id            TEXT PRIMARY KEY,
          dex_number          INTEGER NOT NULL,
          name                TEXT NOT NULL,
          form_ids            TEXT NOT NULL,
          region              TEXT NOT NULL,
          is_variant          INTEGER NOT NULL CHECK (is_variant IN (0, 1)),
          display_order       INTEGER NOT NULL,
          is_released         INTEGER NOT NULL CHECK (is_released IN (0, 1)),
          shiny_release_date  TEXT,
          icon_file_name      TEXT
        )
        """,
        """
        CREATE TABLE shundo (
          entry_id           TEXT PRIMARY KEY REFERENCES pokemon_entry(entry_id),
          registration_time  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'))
        )
        """,
        """
        CREATE TABLE catalog_refresh (
          refresh_id             INTEGER PRIMARY KEY AUTOINCREMENT,
          start_time             TEXT NOT NULL,
          end_time               TEXT NOT NULL,
          status                 TEXT NOT NULL CHECK (status IN ('success', 'failure')),
          game_master_timestamp  TEXT,
          entry_count            INTEGER,
          note                   TEXT
        )
        """,
        """
        CREATE TABLE backup_event (
          backup_event_id  INTEGER PRIMARY KEY AUTOINCREMENT,
          run_time         TEXT NOT NULL,
          backup_path      TEXT NOT NULL,
          size             INTEGER,
          retention        TEXT NOT NULL CHECK (retention IN ('daily', 'monthly', 'yearly')),
          status           TEXT NOT NULL CHECK (status IN ('success', 'failure')),
          source           TEXT NOT NULL CHECK (source IN ('auto', 'manual', 'migration')),
          note             TEXT
        )
        """,
        "CREATE INDEX idx_pokemon_entry_display_order ON pokemon_entry(display_order)",
    )
    for statement in statements:
        conn.execute(statement)
