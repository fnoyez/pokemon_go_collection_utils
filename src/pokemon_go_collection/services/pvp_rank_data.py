"""The data of the PvP ranks tab, as docs/pvp_ranks.md, *Pokémon*, describes it."""

import dataclasses

from pokemon_go_collection import db as db_m


@dataclasses.dataclass(frozen=True)
class RankablePokemon:
    entry_id: str
    # None for the entry itself, else that of one of its Mega or Primal
    # evolutions (MEGA_X).
    temporary_evolution_id: str | None
    name: str
    # (attack, defense, stamina)
    base_stats: tuple[int, int, int]


def load_rankable_pokemons(db_file_path):
    """Return the catalog entries having base stats, by National Pokédex number.

    The entries of one species follow the catalog order: the base form, then its
    other forms. Each entry is followed by its Mega and Primal evolutions.
    """
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT
              entry_id, NULL AS temporary_evolution_id, name,
              base_attack, base_defense, base_stamina,
              dex_number, display_order
            FROM pokemon_entry
            WHERE base_attack IS NOT NULL
            UNION ALL
            SELECT
              temporary_evolution.entry_id,
              temporary_evolution.temporary_evolution_id,
              temporary_evolution.name,
              temporary_evolution.base_attack,
              temporary_evolution.base_defense,
              temporary_evolution.base_stamina,
              pokemon_entry.dex_number,
              pokemon_entry.display_order
            FROM temporary_evolution
            JOIN pokemon_entry USING (entry_id)
            ORDER BY dex_number, display_order, temporary_evolution_id NULLS FIRST
            """
        ).fetchall()
    return [
        RankablePokemon(
            entry_id,
            temporary_evolution_id,
            name,
            (base_attack, base_defense, base_stamina),
        )
        for (
            entry_id,
            temporary_evolution_id,
            name,
            base_attack,
            base_defense,
            base_stamina,
            _,
            _,
        ) in rows
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
