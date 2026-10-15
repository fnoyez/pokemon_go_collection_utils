"""The Mega and Primal evolutions of the entries, with their base stats.

They are filled by the next refresh.
"""


def upgrade(conn):
    conn.execute(
        """
        CREATE TABLE temporary_evolution (
          entry_id                TEXT NOT NULL REFERENCES pokemon_entry(entry_id),
          temporary_evolution_id  TEXT NOT NULL,
          name                    TEXT NOT NULL,
          base_attack             INTEGER NOT NULL,
          base_defense            INTEGER NOT NULL,
          base_stamina            INTEGER NOT NULL,
          PRIMARY KEY (entry_id, temporary_evolution_id)
        )
        """
    )
