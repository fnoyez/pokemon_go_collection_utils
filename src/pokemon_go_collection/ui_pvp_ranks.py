import streamlit as st

from pokemon_go_collection import pvp_ranks as pvp_ranks_m
from pokemon_go_collection.services import pvp_rank_data as pvp_rank_data_m

# The labels the tab shows for each choice, part of what the tab is.
_LEAGUE_LABELS = {
    pvp_ranks_m.League.LITTLE_CUP: "Little Cup (500)",
    pvp_ranks_m.League.GREAT_LEAGUE: "Great League (1500)",
    pvp_ranks_m.League.ULTRA_LEAGUE: "Ultra League (2500)",
}
_MIN_IV_LABELS = {
    0: "0 (Wild)",
    2: "2 (Purified)",
    6: "6 (Shadow legendaries)",
    10: "10 (Raid, eggs, quests)",
}
_LEVEL_BONUS_LABELS = {
    0: "+0 (No bonus)",
    1: "+1 (Best buddy)",
    2: "+2 (Mega Evolution 'Super Max Level')",
    3: "+3 (Best buddy + Mega Evolution 'Super Max Level')",
}


def render_pvp_ranks_page(db_file_path):
    st.header("PvP ranks")
    st.caption(
        "The IV spreads of a Pokémon ranked by their stat product under a league's CP "
        "cap, each at the highest level it can reach under the cap."
    )
    pokemons = pvp_rank_data_m.load_rankable_pokemons(db_file_path)
    cp_multipliers = pvp_rank_data_m.load_cp_multipliers(db_file_path)
    if not cp_multipliers:
        st.caption("No base stats yet: refresh the catalog from the sidebar.")
        return

    settings = _render_shared_settings()
    (best_ranks_tab,) = st.tabs(["Best ranks"])
    with best_ranks_tab:
        _render_best_ranks(pokemons, cp_multipliers, settings)


def _render_shared_settings():
    min_iv_column, max_iv_column, level_bonus_column, half_levels_column = st.columns(4)
    with min_iv_column:
        min_iv = st.selectbox(
            "Minimum IV", list(_MIN_IV_LABELS), format_func=_MIN_IV_LABELS.get
        )
    with max_iv_column:
        max_iv = st.number_input("Maximum IV", min_value=min_iv, max_value=15, value=15)
    with level_bonus_column:
        level_bonus = st.selectbox(
            "Level bonus",
            list(_LEVEL_BONUS_LABELS),
            format_func=_LEVEL_BONUS_LABELS.get,
        )
    with half_levels_column:
        includes_half_levels_above_50 = st.checkbox(
            "Include half levels above 50", value=True
        )
    return {
        "min_iv": min_iv,
        "max_iv": max_iv,
        "levels": tuple(
            pvp_ranks_m.find_reachable_levels(
                level_bonus,
                includes_half_levels_above_50=includes_half_levels_above_50,
            )
        ),
    }


def _render_best_ranks(pokemons, cp_multipliers, settings):
    pokemon_column, league_column = st.columns(2)
    with pokemon_column:
        pokemon = st.selectbox(
            "Pokémon",
            pokemons,
            index=None,
            format_func=lambda pokemon: pokemon.name,
            placeholder="Type a name",
        )
    with league_column:
        league = st.selectbox(
            "League",
            list(_LEAGUE_LABELS),
            index=None,
            format_func=_LEAGUE_LABELS.get,
            placeholder="Choose a league",
        )
    if pokemon is None or league is None:
        return
    with st.spinner("Ranking the IV spreads..."):
        ranks_df = _rank_iv_spreads(
            pokemon.base_stats, cp_multipliers, league.value, settings
        )
    st.dataframe(ranks_df, height=600)


@st.cache_data(max_entries=32)
def _rank_iv_spreads(base_stats, cp_multipliers, max_cp, settings):
    return pvp_ranks_m.rank_iv_spreads(
        base_stats,
        cp_multipliers,
        max_cp,
        settings["levels"],
        min_iv=settings["min_iv"],
        max_iv=settings["max_iv"],
    )
