"""The data of the PvP ranks tab, as docs/pvp_ranks.md, *Pokémon*, describes it."""

import dataclasses

from pokemon_go_collection import db as db_m


@dataclasses.dataclass(frozen=True)
class RankablePokemon:
    entry_id: str
    name: str
    # (attack, defense, stamina)
    base_stats: tuple[int, int, int]


def load_rankable_pokemons(db_file_path):
    """Return the catalog entries having base stats, by National Pokédex number.

    The entries of one species follow the catalog order: the base form, then its
    other forms.
    """
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT entry_id, name, base_attack, base_defense, base_stamina
            FROM pokemon_entry
            WHERE base_attack IS NOT NULL
            ORDER BY dex_number, display_order
            """
        ).fetchall()
    return [
        RankablePokemon(entry_id, name, (base_attack, base_defense, base_stamina))
        for entry_id, name, base_attack, base_defense, base_stamina in rows
    ]


def load_cp_multipliers(db_file_path):
    """Return the CP multiplier of every level, keyed by level."""
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT level, multiplier
            FROM cp_multiplier
            ORDER BY level
            """
        ).fetchall()
    return dict(rows)
