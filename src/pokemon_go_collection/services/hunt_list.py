"""The shundo hunt list, as docs/product_requirements.md, *Shundo hunt list*, defines it."""

import collections
import csv
import io

from pokemon_go_collection import db as db_m
from pokemon_go_collection.services import shundos as shundos_m

# The evolutions between the Pokémon of each board, as (source, target) pairs.
_EVOLUTION_QUERIES = {
    shundos_m.Board.SHUNDOS: """
        SELECT source_entry_id, target_entry_id
        FROM pokemon_evolution
        """,
    shundos_m.Board.COSTUMED_SHUNDOS: """
        SELECT source_costumed_pokemon_id, target_costumed_pokemon_id
        FROM costumed_pokemon_evolution
        """,
}


def select_hunt_entries(board_entries, evolution_edges):
    """Return, in board order, the entries a caught shundo of which fills a missing entry.

    `evolution_edges` maps an entry identifier to the entries it evolves into.
    """
    predecessor_entry_ids = collections.defaultdict(set)
    for source_entry_id, target_entry_ids in evolution_edges.items():
        for target_entry_id in target_entry_ids:
            predecessor_entry_ids[target_entry_id].add(source_entry_id)

    filling_entry_ids = set()
    pending_entry_ids = [
        entry.entry_id
        for entry in board_entries
        if entry.state == shundos_m.EntryState.MISSING
    ]
    while pending_entry_ids:
        entry_id = pending_entry_ids.pop()
        if entry_id not in filling_entry_ids:
            filling_entry_ids.add(entry_id)
            pending_entry_ids.extend(predecessor_entry_ids[entry_id])

    return [
        entry
        for entry in board_entries
        if entry.entry_id in filling_entry_ids
        and entry.state in shundos_m.MARKABLE_ENTRY_STATES
        and entry.pokemon_class is None
        and not entry.is_baby
    ]


def load_evolution_edges(db_file_path, board):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(_EVOLUTION_QUERIES[board]).fetchall()
    evolution_edges = collections.defaultdict(list)
    for source_entry_id, target_entry_id in rows:
        evolution_edges[source_entry_id].append(target_entry_id)
    return dict(evolution_edges)


def build_hunt_list_csv(hunt_entries):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["dex number", "name"])
    writer.writerows((entry.dex_number, entry.name) for entry in hunt_entries)
    return output.getvalue()
