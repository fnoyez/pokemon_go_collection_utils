"""The data of the PvP ranks tab, as docs/pvp_ranks.md, *Pokémon*, describes it."""

import dataclasses
import json
import re

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import rank_names as rank_names_m

# How the catalog names an entry of a form: `Lycanroc (Midnight)`.
_FORM_ENTRY_NAME_REGEX = re.compile(r"^(?P<species_name>.*) \((?P<form_label>.*)\)$")


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


def load_evolution_tree_data(db_file_path):
    """Return the catalog entries having base stats, in catalog order, as
    `rank_names.TreeEntry`, and the evolutions, as (source, target) pairs."""
    with db_m.db_conn(db_file_path) as conn:
        entry_rows = conn.execute(
            """
            SELECT
              entry_id, dex_number, name, form_ids, is_variant, is_baby,
              base_attack, base_defense, base_stamina
            FROM pokemon_entry
            WHERE base_attack IS NOT NULL
            ORDER BY dex_number, display_order
            """
        ).fetchall()
        evolution_edges = conn.execute(
            """
            SELECT source_entry_id, target_entry_id
            FROM pokemon_evolution
            """
        ).fetchall()
    entries = [
        rank_names_m.TreeEntry(
            entry_id,
            dex_number,
            name,
            *_split_entry_name(entry_id, name, json.loads(form_ids_json)),
            bool(is_variant),
            bool(is_baby),
            (base_attack, base_defense, base_stamina),
        )
        for (
            entry_id,
            dex_number,
            name,
            form_ids_json,
            is_variant,
            is_baby,
            base_attack,
            base_defense,
            base_stamina,
        ) in entry_rows
    ]
    return entries, [tuple(evolution_edge) for evolution_edge in evolution_edges]


def _split_entry_name(entry_id, name, form_ids):
    """Return the species name and the form label of an entry."""
    match = _FORM_ENTRY_NAME_REGEX.match(name)
    if match is not None:
        return match["species_name"], match["form_label"]
    # An entry named after its species alone is a base entry, whose identifier
    # is the species identifier: its form label is that of its first form
    # having one, such as LYCANROC_MIDDAY.
    form_label = next(
        (
            catalog_m.build_form_label(form_id, entry_id)
            for form_id in form_ids
            if form_id != entry_id
        ),
        None,
    )
    return name, form_label


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
