"""The battle forms of the entries, with their base stats.

They are filled by the next refresh.
"""


def upgrade(conn):
    conn.execute(
        """
        CREATE TABLE battle_form (
          form_id       TEXT PRIMARY KEY,
          entry_id      TEXT NOT NULL REFERENCES pokemon_entry(entry_id),
          name          TEXT NOT NULL,
          form_order    INTEGER NOT NULL,
          base_attack   INTEGER NOT NULL,
          base_defense  INTEGER NOT NULL,
          base_stamina  INTEGER NOT NULL
        )
        """
    )
