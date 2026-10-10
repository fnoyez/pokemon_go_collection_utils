"""The spawn watch's settings and records, as docs/spawn_watch.md describes them."""


def upgrade(conn):
    statements = (
        """
        CREATE TABLE spawn_watch_config (
          config_id               INTEGER PRIMARY KEY CHECK (config_id = 1),
          is_enabled              INTEGER NOT NULL CHECK (is_enabled IN (0, 1)),
          check_interval_minutes  INTEGER NOT NULL CHECK (check_interval_minutes >= 5)
        )
        """,
        """
        INSERT INTO spawn_watch_config (config_id, is_enabled, check_interval_minutes)
        VALUES (1, 0, 5)
        """,
        """
        CREATE TABLE spawn_check (
          check_id     INTEGER PRIMARY KEY AUTOINCREMENT,
          check_time   TEXT NOT NULL,
          status       TEXT NOT NULL
            CHECK (status IN ('success', 'failure', 'rate_limited', 'unauthorized')),
          spawn_count  INTEGER,
          alert_count  INTEGER,
          note         TEXT
        )
        """,
        """
        CREATE TABLE spawn_alert (
          encounter_id  TEXT PRIMARY KEY,
          entry_id      TEXT NOT NULL,
          name          TEXT NOT NULL,
          raw_iv        TEXT NOT NULL,
          cp            INTEGER NOT NULL,
          level         REAL NOT NULL,
          location      TEXT NOT NULL,
          despawn_time  TEXT NOT NULL,
          reveal_url    TEXT NOT NULL,
          alert_time    TEXT NOT NULL
        )
        """,
        "CREATE INDEX idx_spawn_check_check_time ON spawn_check(check_time)",
        "CREATE INDEX idx_spawn_alert_alert_time ON spawn_alert(alert_time)",
    )
    for statement in statements:
        conn.execute(statement)
