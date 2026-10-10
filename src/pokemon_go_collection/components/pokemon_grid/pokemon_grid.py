import functools
import pathlib

import streamlit as st

# Relative to the page, where Streamlit serves the `static/` folder.
_ICON_BASE_URL = "app/static/icons"


def render_pokemon_grid(groups, key, on_desired_ownership_change):
    """Mount the grid and return its result.

    `groups` is a list of {"title", "summary", "sections"}, each section a
    {"title", "entries"}, each entry an {"id", "name", "dex", "icon", "state"}.
    The result's `desired_ownership` maps every entry clicked since the page
    was loaded to the ownership asked for.
    """
    component = _register_component()
    return component(
        key=key,
        data={"groups": groups, "icon_base_url": _ICON_BASE_URL},
        default={"desired_ownership": {}},
        on_desired_ownership_change=on_desired_ownership_change,
    )


@functools.cache
def _register_component():
    folder_path = pathlib.Path(__file__).parent
    return st.components.v2.component(
        "pokemon_grid",
        css=(folder_path / "pokemon_grid.css").read_text(),
        js=(folder_path / "pokemon_grid.js").read_text(),
    )
