"""The coordinates of each spawn alerted, when the service revealed them."""


def upgrade(conn):
    conn.execute(
        """
        ALTER TABLE spawn_alert
        ADD COLUMN coordinates TEXT
        """
    )
