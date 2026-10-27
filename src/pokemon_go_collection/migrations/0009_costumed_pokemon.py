"""The costumed Pokémon, their evolutions, and the costumed shundos owned.

The costumed Pokémon are filled by the next refresh.
"""


def upgrade(conn):
    statements = (
        """
        CREATE TABLE costumed_pokemon (
          costumed_pokemon_id  TEXT PRIMARY KEY,
          dex_number           INTEGER NOT NULL,
          name                 TEXT NOT NULL,
          region               TEXT NOT NULL,
          display_order        INTEGER NOT NULL,
          form_suffix          TEXT,
          costume              TEXT,
          bulbapedia_code      TEXT,
          release_date         TEXT,
          shiny_release_date   TEXT,
          costume_year         INTEGER,
          pokemon_class        TEXT,
          is_baby              INTEGER NOT NULL CHECK (is_baby IN (0, 1)),
          icon_file_name       TEXT
        )
        """,
        """
        CREATE TABLE costumed_pokemon_evolution (
          source_costumed_pokemon_id  TEXT NOT NULL
            REFERENCES costumed_pokemon(costumed_pokemon_id),
          target_costumed_pokemon_id  TEXT NOT NULL
            REFERENCES costumed_pokemon(costumed_pokemon_id),
          PRIMARY KEY (source_costumed_pokemon_id, target_costumed_pokemon_id)
        )
        """,
        """
        CREATE TABLE costumed_shundo (
          costumed_pokemon_id  TEXT PRIMARY KEY
            REFERENCES costumed_pokemon(costumed_pokemon_id),
          registration_time    TEXT NOT NULL
            DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'))
        )
        """,
    )
    for statement in statements:
        conn.execute(statement)
