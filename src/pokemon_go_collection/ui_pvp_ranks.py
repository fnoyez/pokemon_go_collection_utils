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
# The session state keys holding each section's last ranking, with the inputs
# it was made from.
_BEST_RANKS_KEY = "pvp_best_ranks"
_IV_SPREAD_RANKS_KEY = "pvp_iv_spread_ranks"


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
    best_ranks_tab, iv_spread_ranks_tab = st.tabs(["Best ranks", "Ranks of IV spreads"])
    with best_ranks_tab:
        _render_best_ranks(pokemons, cp_multipliers, settings)
    with iv_spread_ranks_tab:
        _render_iv_spread_ranks(pokemons, cp_multipliers, settings)


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
    request = {"pokemon": pokemon, "league": league, "settings": settings}
    if st.button("Rank", key="best_ranks_button"):
        missing_inputs = _find_missing_inputs(
            {"a Pokémon": pokemon, "a league": league}
        )
        if missing_inputs:
            st.error(f"Missing: {', '.join(missing_inputs)}.")
        else:
            with st.spinner("Ranking the IV spreads..."):
                ranks_df = _rank_iv_spreads(
                    pokemon.base_stats, cp_multipliers, league.value, settings
                )
            st.session_state[_BEST_RANKS_KEY] = {
                "request": request,
                "ranks_df": ranks_df,
            }
    result = st.session_state.get(_BEST_RANKS_KEY)
    if result is not None and result["request"] == request:
        st.dataframe(result["ranks_df"], height=600, hide_index=True)


def _find_missing_inputs(inputs_by_description):
    return [
        description
        for description, input_value in inputs_by_description.items()
        if not input_value
    ]


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


def _render_iv_spread_ranks(pokemons, cp_multipliers, settings):
    pokemon_column, league_column = st.columns(2)
    with pokemon_column:
        selected_pokemons = st.multiselect(
            "Pokémon",
            pokemons,
            format_func=lambda pokemon: pokemon.name,
            placeholder="Type names",
        )
    with league_column:
        leagues = st.multiselect(
            "Leagues",
            list(_LEAGUE_LABELS),
            format_func=_LEAGUE_LABELS.get,
            placeholder="Choose leagues",
        )
    iv_spreads_text = st.text_area(
        "IV spreads, one per line, as attack defense stamina", placeholder="10 13 14"
    )
    request = {
        "pokemons": selected_pokemons,
        "leagues": leagues,
        "iv_spreads_text": iv_spreads_text,
        "settings": settings,
    }
    if st.button("Rank", key="iv_spread_ranks_button"):
        missing_inputs = _find_missing_inputs(
            {
                "at least one Pokémon": selected_pokemons,
                "at least one league": leagues,
                "at least one IV spread": iv_spreads_text.strip(),
            }
        )
        if missing_inputs:
            st.error(f"Missing: {', '.join(missing_inputs)}.")
        else:
            try:
                iv_spreads = pvp_ranks_m.parse_iv_spreads(iv_spreads_text)
            except ValueError as error:
                st.error(str(error))
            else:
                with st.spinner("Ranking the IV spreads..."):
                    iv_spread_ranks = _rank_given_iv_spreads(
                        _sort_like(pokemons, selected_pokemons),
                        _sort_like(list(_LEAGUE_LABELS), leagues),
                        iv_spreads,
                        cp_multipliers,
                        settings,
                    )
                st.session_state[_IV_SPREAD_RANKS_KEY] = {
                    "request": request,
                    "iv_spread_ranks": iv_spread_ranks,
                }
    result = st.session_state.get(_IV_SPREAD_RANKS_KEY)
    if result is not None and result["request"] == request:
        for title, iv_spread_ranks_df in result["iv_spread_ranks"]:
            st.markdown(f"**{title}**")
            if iv_spread_ranks_df.empty:
                st.caption("None of the IV spreads is within the IV range.")
            else:
                st.dataframe(iv_spread_ranks_df, hide_index=True)


def _rank_given_iv_spreads(pokemons, leagues, iv_spreads, cp_multipliers, settings):
    """Return the ranks of `iv_spreads`, as (title, ranks) per Pokémon and league."""
    iv_spread_ranks = []
    for pokemon in pokemons:
        for league in leagues:
            ranks_df = _rank_iv_spreads(
                pokemon.base_stats, cp_multipliers, league.value, settings
            )
            iv_spread_ranks.append(
                (
                    f"{pokemon.name} · {_LEAGUE_LABELS[league]}",
                    pvp_ranks_m.select_iv_spread_ranks(ranks_df, iv_spreads),
                )
            )
    return iv_spread_ranks


def _sort_like(ordered_items, items):
    return sorted(items, key=ordered_items.index)
