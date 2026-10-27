"""Whether the spawn watch searches for the costumed shundos too, off at first."""


def upgrade(conn):
    conn.execute(
        """
        ALTER TABLE spawn_watch_config
        ADD COLUMN is_costume_search_enabled INTEGER NOT NULL DEFAULT 0
          CHECK (is_costume_search_enabled IN (0, 1))
        """
    )
