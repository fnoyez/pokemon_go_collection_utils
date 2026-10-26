"""The status of a check whose search failed before reaching the service.

SQLite cannot change a CHECK constraint in place, so the table is rebuilt.
"""


def upgrade(conn):
    statements = (
        """
        CREATE TABLE spawn_check_new (
          check_id     INTEGER PRIMARY KEY AUTOINCREMENT,
          check_time   TEXT NOT NULL,
          status       TEXT NOT NULL
            CHECK (
              status IN (
                'success', 'failure', 'rate_limited', 'unauthorized',
                'network_unavailable'
              )
            ),
          spawn_count  INTEGER,
          alert_count  INTEGER,
          note         TEXT
        )
        """,
        """
        INSERT INTO spawn_check_new
          (check_id, check_time, status, spawn_count, alert_count, note)
        SELECT check_id, check_time, status, spawn_count, alert_count, note
        FROM spawn_check
        """,
        "DROP TABLE spawn_check",
        "ALTER TABLE spawn_check_new RENAME TO spawn_check",
        "CREATE INDEX idx_spawn_check_check_time ON spawn_check(check_time)",
    )
    for statement in statements:
        conn.execute(statement)
