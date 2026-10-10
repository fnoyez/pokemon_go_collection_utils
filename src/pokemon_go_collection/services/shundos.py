import dataclasses
import datetime
import enum
import logging

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import regions as regions_m

logger = logging.getLogger(__name__)


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
    state: EntryState


def apply_desired_ownership(db_file_path, desired_ownership, today):
    """Make the collection match `desired_ownership` (entry identifier -> owned).

    The mapping holds every entry clicked since the board was opened, and is
    applied in full each time, which is what makes it safe against clicks
    whose individual events were coalesced. Entries that cannot be marked are
    left alone. Returns the number of entries changed.
    """
    board_entries = {
        entry.entry_id: entry for entry in load_board_entries(db_file_path, today)
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

    with db_m.db_conn(db_file_path) as conn:
        conn.executemany(
            """
            INSERT INTO shundo (entry_id)
            VALUES (?)
            """,
            [(entry_id,) for entry_id in marked_entry_ids],
        )
        conn.executemany(
            """
            DELETE FROM shundo
            WHERE entry_id = ?
            """,
            [(entry_id,) for entry_id in unmarked_entry_ids],
        )
    if marked_entry_ids or unmarked_entry_ids:
        logger.info(
            f"Shundos marked: {marked_entry_ids}; unmarked: {unmarked_entry_ids}"
        )
    return len(marked_entry_ids) + len(unmarked_entry_ids)


def load_board_entries(db_file_path, today):
    """Return every catalog entry, in display order, with its state."""
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT
              e.entry_id, e.dex_number, e.name, e.region, e.is_variant,
              e.icon_file_name, e.is_released, e.shiny_release_date,
              s.entry_id IS NOT NULL
            FROM pokemon_entry AS e
            LEFT JOIN shundo AS s ON s.entry_id = e.entry_id
            ORDER BY e.display_order
            """
        ).fetchall()
    return [
        BoardEntry(
            entry_id=row[0],
            dex_number=row[1],
            name=row[2],
            region=regions_m.Region(row[3]),
            is_variant=bool(row[4]),
            icon_file_name=row[5],
            state=find_entry_state(
                bool(row[6]),
                datetime.date.fromisoformat(row[7]) if row[7] else None,
                bool(row[8]),
                today,
            ),
        )
        for row in rows
    ]


def find_entry_state(is_released, shiny_release_date, is_owned, today):
    """Return how an entry is shown; an owned entry stays owned whatever its statuses say."""
    if is_owned:
        return EntryState.OWNED
    if catalog_m.is_shiny_released(shiny_release_date, today):
        return EntryState.MISSING
    if catalog_m.is_entry_released(is_released, shiny_release_date, today):
        return EntryState.NO_SHINY
    return EntryState.UNRELEASED
