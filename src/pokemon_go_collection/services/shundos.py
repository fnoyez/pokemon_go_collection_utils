import collections
import dataclasses
import datetime
import enum
import logging

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import costumes as costumes_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.sources import game_master as game_master_m

logger = logging.getLogger(__name__)


class Board(enum.Enum):
    """The shundo boards: the catalog's entries, and the costumed Pokémon."""

    SHUNDOS = "shundos"
    COSTUMED_SHUNDOS = "costumed_shundos"


# The table recording the shundos owned on each board, and its column naming
# what is owned.
_OWNERSHIP_TABLES = {
    Board.SHUNDOS: ("shundo", "entry_id"),
    Board.COSTUMED_SHUNDOS: ("costumed_shundo", "costumed_pokemon_id"),
}
# Each board's Pokémon with their statuses, in display order. The release date
# and the costume's year are a costumed Pokémon's only.
_BOARD_ENTRIES_QUERIES = {
    Board.SHUNDOS: """
        SELECT
          e.entry_id, e.dex_number, e.name, e.region, e.is_variant,
          e.icon_file_name, e.pokemon_class, e.is_baby, e.is_released,
          e.shiny_release_date, s.entry_id IS NOT NULL, NULL, NULL
        FROM pokemon_entry AS e
        LEFT JOIN shundo AS s ON s.entry_id = e.entry_id
        ORDER BY e.display_order
        """,
    Board.COSTUMED_SHUNDOS: """
        SELECT
          c.costumed_pokemon_id, c.dex_number, c.name, c.region, 0,
          c.icon_file_name, c.pokemon_class, c.is_baby, NULL,
          c.shiny_release_date, s.costumed_pokemon_id IS NOT NULL,
          c.release_date, c.costume_year
        FROM costumed_pokemon AS c
        LEFT JOIN costumed_shundo AS s
          ON s.costumed_pokemon_id = c.costumed_pokemon_id
        ORDER BY c.display_order
        """,
}


class EntryState(enum.Enum):
    """How an entry is shown on the shundo board, as docs/catalog.md tabulates."""

    UNRELEASED = "unreleased"
    NO_SHINY = "no_shiny"
    MISSING = "missing"
    OWNED = "owned"


# The states whose entries a click marks or unmarks.
MARKABLE_ENTRY_STATES = frozenset({EntryState.MISSING, EntryState.OWNED})


@dataclasses.dataclass(frozen=True)
class BoardEntry:
    entry_id: str
    dex_number: int
    name: str
    region: regions_m.Region
    is_variant: bool
    icon_file_name: str | None
    pokemon_class: game_master_m.PokemonClass | None
    is_baby: bool
    state: EntryState
    # A costumed Pokémon nothing suggests will be released, as docs/costumes.md
    # defines it.
    is_unreleasable: bool = False


def apply_desired_ownership(db_file_path, board, desired_ownership, today):
    """Make the collection match `desired_ownership` (entry identifier -> owned).

    The mapping holds every entry clicked since the board was opened, and is
    applied in full each time, which is what makes it safe against clicks
    whose individual events were coalesced. Entries that cannot be marked are
    left alone. Returns the number of entries changed.
    """
    board_entries = {
        entry.entry_id: entry
        for entry in load_board_entries(db_file_path, board, today)
    }
    marked_entry_ids = []
    unmarked_entry_ids = []
    for entry_id, is_owned in desired_ownership.items():
        entry = board_entries.get(entry_id)
        if entry is None or entry.state not in MARKABLE_ENTRY_STATES:
            logger.warning(
                f"Ignoring a change to entry {entry_id}, which cannot be marked"
            )
            continue
        if is_owned and entry.state == EntryState.MISSING:
            marked_entry_ids.append(entry_id)
        elif not is_owned and entry.state == EntryState.OWNED:
            unmarked_entry_ids.append(entry_id)

    table_name, column_name = _OWNERSHIP_TABLES[board]
    with db_m.db_conn(db_file_path) as conn:
        conn.executemany(
            f"""
            INSERT INTO {table_name} ({column_name})
            VALUES (?)
            """,
            [(entry_id,) for entry_id in marked_entry_ids],
        )
        conn.executemany(
            f"""
            DELETE FROM {table_name}
            WHERE {column_name} = ?
            """,
            [(entry_id,) for entry_id in unmarked_entry_ids],
        )
    if marked_entry_ids or unmarked_entry_ids:
        logger.info(
            f"Shundos marked: {marked_entry_ids}; unmarked: {unmarked_entry_ids}"
        )
    return len(marked_entry_ids) + len(unmarked_entry_ids)


def load_board_entries(db_file_path, board, today):
    """Return every Pokémon of the board, in display order, with its state.

    A costumed Pokémon is released once its release date has come.
    """
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(_BOARD_ENTRIES_QUERIES[board]).fetchall()
    board_entries = []
    for row in rows:
        shiny_release_date = _parse_date(row[9])
        release_date = _parse_date(row[11])
        is_released = (
            bool(row[8])
            if board == Board.SHUNDOS
            else release_date is not None and release_date <= today
        )
        board_entries.append(
            BoardEntry(
                entry_id=row[0],
                dex_number=row[1],
                name=row[2],
                region=regions_m.Region(row[3]),
                is_variant=bool(row[4]),
                icon_file_name=row[5],
                pokemon_class=game_master_m.PokemonClass(row[6]) if row[6] else None,
                is_baby=bool(row[7]),
                state=find_entry_state(
                    is_released, shiny_release_date, bool(row[10]), today
                ),
                is_unreleasable=board == Board.COSTUMED_SHUNDOS
                and costumes_m.is_unreleasable(release_date, row[12], today),
            )
        )
    return board_entries


def _parse_date(date_text):
    return datetime.date.fromisoformat(date_text) if date_text else None


def find_entry_state(is_released, shiny_release_date, is_owned, today):
    """Return how an entry is shown; an owned entry stays owned whatever its statuses say."""
    if is_owned:
        return EntryState.OWNED
    if catalog_m.is_shiny_released(shiny_release_date, today):
        return EntryState.MISSING
    if catalog_m.is_entry_released(is_released, shiny_release_date, today):
        return EntryState.NO_SHINY
    return EntryState.UNRELEASED


def collect_evolution_lines(evolution_edges, entry_ids):
    """Return the identifiers of every entry in the evolutionary line of one of `entry_ids`.

    `evolution_edges` maps an entry identifier to the entries it evolves into.
    A line holds every entry an evolution links to another of the line, in
    either direction: Vaporeon's holds Eevee and all its other evolutions.
    """
    linked_entry_ids = collections.defaultdict(set)
    for source_entry_id, target_entry_ids in evolution_edges.items():
        for target_entry_id in target_entry_ids:
            linked_entry_ids[source_entry_id].add(target_entry_id)
            linked_entry_ids[target_entry_id].add(source_entry_id)

    line_entry_ids = set()
    pending_entry_ids = list(entry_ids)
    while pending_entry_ids:
        entry_id = pending_entry_ids.pop()
        if entry_id not in line_entry_ids:
            line_entry_ids.add(entry_id)
            pending_entry_ids.extend(linked_entry_ids[entry_id])
    return line_entry_ids
