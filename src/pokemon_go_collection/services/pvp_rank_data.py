"""The data of the PvP ranks tab, as docs/pvp_ranks.md, *Pokémon*, describes it."""

import dataclasses
import json
import re
import unicodedata

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
    # None for the entry itself, else that of one of its battle forms
    # (MINIOR_BLUE).
    battle_form_id: str | None
    dex_number: int
    name: str
    # (attack, defense, stamina)
    base_stats: tuple[int, int, int]


def load_rankable_pokemons(db_file_path):
    """Return the catalog entries having base stats, by National Pokédex number.

    The entries of one species follow the catalog order: the base form, then its
    other forms. Each entry is followed by its battle forms, then by its Mega and
    Primal evolutions.
    """
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT
              entry_id, NULL AS temporary_evolution_id, NULL AS battle_form_id,
              dex_number, name, base_attack, base_defense, base_stamina,
              display_order, 0 AS kind_order, 0 AS order_within_kind
            FROM pokemon_entry
            WHERE base_attack IS NOT NULL
            UNION ALL
            SELECT
              battle_form.entry_id, NULL, battle_form.form_id,
              pokemon_entry.dex_number, battle_form.name,
              battle_form.base_attack, battle_form.base_defense,
              battle_form.base_stamina,
              pokemon_entry.display_order, 1, battle_form.form_order
            FROM battle_form
            JOIN pokemon_entry USING (entry_id)
            UNION ALL
            SELECT
              temporary_evolution.entry_id,
              temporary_evolution.temporary_evolution_id, NULL,
              pokemon_entry.dex_number, temporary_evolution.name,
              temporary_evolution.base_attack, temporary_evolution.base_defense,
              temporary_evolution.base_stamina,
              pokemon_entry.display_order, 2, temporary_evolution.temporary_evolution_id
            FROM temporary_evolution
            JOIN pokemon_entry USING (entry_id)
            ORDER BY dex_number, display_order, kind_order, order_within_kind
            """
        ).fetchall()
    return [
        RankablePokemon(
            entry_id,
            temporary_evolution_id,
            battle_form_id,
            dex_number,
            name,
            (base_attack, base_defense, base_stamina),
        )
        for (
            entry_id,
            temporary_evolution_id,
            battle_form_id,
            dex_number,
            name,
            base_attack,
            base_defense,
            base_stamina,
            *_,
        ) in rows
    ]


def find_pokemons_by_name(pokemons, name_part):
    """Return the Pokémon whose name contains `name_part`, ignoring case and accents."""
    normalized_name_part = _normalize_name(name_part.strip())
    return [
        pokemon
        for pokemon in pokemons
        if normalized_name_part in _normalize_name(pokemon.name)
    ]


def _normalize_name(name):
    decomposed_name = unicodedata.normalize("NFKD", name.casefold())
    return "".join(
        character
        for character in decomposed_name
        if not unicodedata.combining(character)
    )


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
