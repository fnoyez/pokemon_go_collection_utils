"""Each entry's Pokémon class and baby flag, and the evolutions between entries.

They are filled by the next refresh.
"""


def upgrade(conn):
    statements = (
        """
        ALTER TABLE pokemon_entry
        ADD COLUMN pokemon_class TEXT
          CHECK (pokemon_class IN ('legendary', 'mythical', 'ultra_beast'))
        """,
        """
        ALTER TABLE pokemon_entry
        ADD COLUMN is_baby INTEGER NOT NULL DEFAULT 0 CHECK (is_baby IN (0, 1))
        """,
        """
        CREATE TABLE pokemon_evolution (
          source_entry_id  TEXT NOT NULL REFERENCES pokemon_entry(entry_id),
          target_entry_id  TEXT NOT NULL REFERENCES pokemon_entry(entry_id),
          PRIMARY KEY (source_entry_id, target_entry_id)
        )
        """,
    )
    for statement in statements:
        conn.execute(statement)
