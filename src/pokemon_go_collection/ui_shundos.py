import datetime
import enum

import streamlit as st

from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.components.pokemon_grid import (
    pokemon_grid as pokemon_grid_m,
)
from pokemon_go_collection.services import hunt_list as hunt_list_m
from pokemon_go_collection.services import shundos as shundos_m

_GRID_KEY = "shundo_grid"


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


def render_shundos_page(db_file_path):
    st.header("Shundos")
    st.caption(
        "Click a Pokémon to mark or unmark it as owned as a shundo. Silhouettes are "
        "not released in Pokémon GO, greyed-out ones have no shiny released yet."
    )
    _render_shundo_board(db_file_path)


@st.fragment
def _render_shundo_board(db_file_path):
    today = datetime.date.today()
    board_entries = shundos_m.load_board_entries(db_file_path, today)
    if not board_entries:
        st.info("The catalog is empty: run a refresh from the sidebar.")
        return

    _render_totals(board_entries)
    _render_hunt_list_download(db_file_path, board_entries)
    filter_column, search_column = st.columns([1, 2])
    with filter_column:
        board_filter = BoardFilter(
            st.segmented_control(
                "Show",
                [board_filter.value for board_filter in BoardFilter],
                default=BoardFilter.ALL.value,
                key="shundo_board_filter",
            )
            or BoardFilter.ALL.value
        )
    with search_column:
        search_text = st.text_input("Search", key="shundo_board_search")

    groups = build_grid_groups(board_entries, _FILTER_STATES[board_filter], search_text)
    if not groups:
        st.info("No Pokémon matches.")
        return
    pokemon_grid_m.render_pokemon_grid(
        groups,
        _GRID_KEY,
        lambda: _apply_grid_changes(db_file_path, today),
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
        board_entries, hunt_list_m.load_evolution_edges(db_file_path)
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


def build_grid_groups(board_entries, shown_states, search_text):
    """Group the entries shown by region, each region's variant block in a section of its own.

    Each region's summary counts its owned and markable entries over the whole
    board, whatever the filter shows.
    """
    normalized_search_text = search_text.strip().lower()
    groups = []
    for region in regions_m.Region:
        region_entries = [entry for entry in board_entries if entry.region == region]
        shown_entries = [
            entry
            for entry in region_entries
            if entry.state in shown_states
            and normalized_search_text in entry.name.lower()
        ]
        if not shown_entries:
            continue
        sections = [
            {
                "title": title,
                "entries": [
                    _build_grid_entry(entry)
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
    return groups


def _build_grid_entry(board_entry):
    return {
        "id": board_entry.entry_id,
        "name": board_entry.name,
        "dex": board_entry.dex_number,
        "icon": board_entry.icon_file_name,
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


def _apply_grid_changes(db_file_path, today):
    desired_ownership = st.session_state[_GRID_KEY]["desired_ownership"]
    shundos_m.apply_desired_ownership(db_file_path, desired_ownership, today)
