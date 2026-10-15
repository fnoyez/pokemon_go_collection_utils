"""Each entry's base stats, and the CP multiplier of every level.

They are filled by the next refresh.
"""


def upgrade(conn):
    statements = (
        """
        ALTER TABLE pokemon_entry
        ADD COLUMN base_attack INTEGER
        """,
        """
        ALTER TABLE pokemon_entry
        ADD COLUMN base_defense INTEGER
        """,
        """
        ALTER TABLE pokemon_entry
        ADD COLUMN base_stamina INTEGER
        """,
        """
        CREATE TABLE cp_multiplier (
          level       REAL PRIMARY KEY,
          multiplier  REAL NOT NULL
        )
        """,
    )
    for statement in statements:
        conn.execute(statement)
