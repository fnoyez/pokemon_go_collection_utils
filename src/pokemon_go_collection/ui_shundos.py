import datetime
import enum

import streamlit as st

from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.components.pokemon_grid import (
    pokemon_grid as pokemon_grid_m,
)
from pokemon_go_collection.services import hunt_list as hunt_list_m
from pokemon_go_collection.services import shundos as shundos_m

# The session state keys of each board's widgets, so the two tabs keep apart.
_GRID_KEYS = {
    shundos_m.Board.SHUNDOS: "shundo_grid",
    shundos_m.Board.COSTUMED_SHUNDOS: "costumed_shundo_grid",
}


class BoardFilter(enum.Enum):
    ALL = "All"
    MISSING = "Missing"
    OWNED = "Owned"


# The entry states each filter shows.
_FILTER_STATES = {
    BoardFilter.ALL: frozenset(shundos_m.EntryState),
    BoardFilter.MISSING: frozenset({shundos_m.EntryState.MISSING}),
    BoardFilter.OWNED: frozenset({shundos_m.EntryState.OWNED}),
}


def render_shundos_page(db_file_path, icons_folder_path):
    st.header("Shundos")
    st.caption(
        "Click a Pokémon to mark or unmark it as owned as a shundo. Silhouettes are "
        "not released in Pokémon GO, greyed-out ones have no shiny released yet."
    )
    _render_shundo_board(db_file_path, icons_folder_path, shundos_m.Board.SHUNDOS)


@st.fragment
def _render_shundo_board(db_file_path, icons_folder_path, board):
    today = datetime.date.today()
    board_entries = shundos_m.load_board_entries(db_file_path, board, today)
    if not board_entries:
        st.info("The catalog is empty: run a refresh from the sidebar.")
        return

    _render_totals(board_entries)
    if board == shundos_m.Board.SHUNDOS:
        _render_hunt_list_download(db_file_path, board_entries)
    filter_column, search_column = st.columns([1, 2])
    with filter_column:
        board_filter = BoardFilter(
            st.segmented_control(
                "Show",
                [board_filter.value for board_filter in BoardFilter],
                default=BoardFilter.ALL.value,
                key=f"{_GRID_KEYS[board]}_filter",
            )
            or BoardFilter.ALL.value
        )
    with search_column:
        search_text = st.text_input("Search", key=f"{_GRID_KEYS[board]}_search")

    groups = build_grid_groups(
        board_entries,
        _find_icon_versions(icons_folder_path),
        _FILTER_STATES[board_filter],
        search_text,
    )
    if not groups:
        st.info("No Pokémon matches.")
        return
    pokemon_grid_m.render_pokemon_grid(
        groups,
        _GRID_KEYS[board],
        lambda: _apply_grid_changes(db_file_path, board, today),
    )


def _render_totals(board_entries):
    owned_nb = sum(entry.state == shundos_m.EntryState.OWNED for entry in board_entries)
    markable_nb = sum(
        entry.state in shundos_m.MARKABLE_ENTRY_STATES for entry in board_entries
    )
    columns = st.columns(3)
    columns[0].metric("Shundos owned", owned_nb)
    columns[1].metric("Shundos missing", markable_nb - owned_nb)
    columns[2].metric(
        "Completion", f"{owned_nb / markable_nb:.1%}" if markable_nb else "-"
    )


def _render_hunt_list_download(db_file_path, board_entries):
    hunt_entries = hunt_list_m.select_hunt_entries(
        board_entries,
        hunt_list_m.load_evolution_edges(db_file_path, shundos_m.Board.SHUNDOS),
    )
    st.download_button(
        f"Download the hunt list ({len(hunt_entries)} Pokémon)",
        hunt_list_m.build_hunt_list_csv(hunt_entries),
        file_name="pokemons_to_shundo_hunt.csv",
        mime="text/csv",
        on_click="ignore",
        help=(
            "The Pokémon whose shundo, caught and evolved if needed, fills a missing "
            "shundo; legendary, mythical, ultra beast and baby Pokémon left out."
        ),
    )


def build_grid_groups(board_entries, icon_versions, shown_states, search_text):
    """Group the entries shown by region, each region's variant block in a section of its own.

    `icon_versions` maps each icon file name to its version, from
    `_find_icon_versions`. The unreleasable entries make a last group of their
    own, after the regions.

    Each region's summary counts its owned and markable entries over the whole
    board, whatever the filter shows.
    """
    normalized_search_text = search_text.strip().lower()

    def is_shown(entry):
        return (
            entry.state in shown_states and normalized_search_text in entry.name.lower()
        )

    groups = []
    for region in regions_m.Region:
        region_entries = [
            entry
            for entry in board_entries
            if entry.region == region and not entry.is_unreleasable
        ]
        shown_entries = [entry for entry in region_entries if is_shown(entry)]
        if not shown_entries:
            continue
        sections = [
            {
                "title": title,
                "entries": [
                    _build_grid_entry(entry, icon_versions)
                    for entry in shown_entries
                    if entry.is_variant == is_variant
                ],
            }
            for title, is_variant in ((None, False), ("Regional variants", True))
        ]
        groups.append(
            {
                "title": region.value,
                "summary": _build_region_summary(region_entries),
                "sections": [section for section in sections if section["entries"]],
            }
        )
    unreleasable_entries = [
        entry for entry in board_entries if entry.is_unreleasable and is_shown(entry)
    ]
    if unreleasable_entries:
        groups.append(
            {
                "title": "Unreleasable",
                "summary": f"{len(unreleasable_entries)} Pokémon",
                "sections": [
                    {
                        "title": None,
                        "entries": [
                            _build_grid_entry(entry, icon_versions)
                            for entry in unreleasable_entries
                        ],
                    }
                ],
            }
        )
    return groups


def _build_grid_entry(board_entry, icon_versions):
    icon_file_name = board_entry.icon_file_name
    return {
        "id": board_entry.entry_id,
        "name": board_entry.name,
        "dex": board_entry.dex_number,
        # The version in the URL makes the browser fetch an icon downloaded
        # again under the same file name, rather than show the one it cached.
        "icon": (
            None
            if icon_file_name is None
            else f"{icon_file_name}?v={icon_versions[icon_file_name]}"
        ),
        "state": board_entry.state.value,
    }


def _build_region_summary(region_entries):
    owned_nb = sum(
        entry.state == shundos_m.EntryState.OWNED for entry in region_entries
    )
    markable_nb = sum(
        entry.state in shundos_m.MARKABLE_ENTRY_STATES for entry in region_entries
    )
    return f"{owned_nb} / {markable_nb} shundos"


def _find_icon_versions(icons_folder_path):
    """Map each icon file name to its modification time, which changes when it is downloaded again."""
    return {
        icon_file_path.name: icon_file_path.stat().st_mtime_ns
        for icon_file_path in icons_folder_path.iterdir()
    }


def _apply_grid_changes(db_file_path, board, today):
    desired_ownership = st.session_state[_GRID_KEYS[board]]["desired_ownership"]
    shundos_m.apply_desired_ownership(db_file_path, board, desired_ownership, today)


def render_costumed_shundos_page(db_file_path, icons_folder_path):
    st.header("Costumed shundos")
    st.caption(
        "Click a costumed Pokémon to mark or unmark it as owned as a shundo. "
        "Silhouettes are not released in Pokémon GO, greyed-out ones have no shiny "
        "released yet. The unreleasable ones, at the bottom, are in the game's files "
        "but in no event, with a costume of a past year."
    )
    _render_shundo_board(
        db_file_path, icons_folder_path, shundos_m.Board.COSTUMED_SHUNDOS
    )
