"""The WatWowMap wwm-uicons repository, as docs/data_sources.md describes it."""

import dataclasses
import json
import re

UICONS_INDEX_URL = (
    "https://raw.githubusercontent.com/WatWowMap/wwm-uicons/main/index.json"
)
UICONS_POKEMON_BASE_URL = (
    "https://raw.githubusercontent.com/WatWowMap/wwm-uicons/main/pokemon"
)

# `<dex number>`, then `_f<form number>`, `_c<costume number>`, `_g2` for the
# female icon and `_s` for the shiny, each optional, then `.png`. The icons
# with other parts, such as `_a1` for a Shadow Pokémon, are not matched.
_ICON_FILE_NAME_REGEX = re.compile(
    r"^(?P<dex_number>\d+)"
    r"(?:_f(?P<form_number>\d+))?"
    r"(?:_c(?P<costume_number>\d+))?"
    r"(?P<female>_g2)?"
    r"(?P<shiny>_s)?"
    r"\.png$"
)


@dataclasses.dataclass(frozen=True)
class Icon:
    file_name: str
    dex_number: int
    # The game's form identifier: `PIKACHU_NORMAL` for `25.png`, whose number
    # names no form, the species' default form being meant; None for a species
    # without forms.
    form_id: str | None
    # The game's costume name; None without a costume.
    costume: str | None
    is_female: bool
    is_shiny: bool


def parse_index(content, game_numbers):
    """Return the Pokémon icons of the index, by file name.

    An icon of a form or costume the masterfile does not number is left out.
    """
    form_names = {number: name for name, number in game_numbers.form_numbers.items()}
    costume_names = {
        number: name for name, number in game_numbers.costume_numbers.items()
    }
    icons = (
        _parse_icon_file_name(
            file_name,
            game_numbers.default_form_numbers,
            form_names,
            costume_names,
        )
        for file_name in json.loads(content)["pokemon"]
    )
    return sorted(
        (icon for icon in icons if icon is not None),
        key=lambda icon: icon.file_name,
    )


def _parse_icon_file_name(file_name, default_form_numbers, form_names, costume_names):
    match = _ICON_FILE_NAME_REGEX.match(file_name)
    if match is None:
        return None
    dex_number = int(match["dex_number"])
    form_number = (
        int(match["form_number"])
        if match["form_number"] is not None
        else default_form_numbers.get(dex_number)
    )
    costume_number = (
        int(match["costume_number"]) if match["costume_number"] is not None else None
    )
    if (form_number is not None and form_number not in form_names) or (
        costume_number is not None and costume_number not in costume_names
    ):
        return None
    return Icon(
        file_name=file_name,
        dex_number=dex_number,
        form_id=form_names[form_number] if form_number is not None else None,
        costume=costume_names[costume_number] if costume_number is not None else None,
        is_female=match["female"] is not None,
        is_shiny=match["shiny"] is not None,
    )


def build_icon_file_name(dex_number, form_number, costume_number, is_shiny):
    """Return the file name of an icon; `form_number` is None for the species' default form."""
    parts = [str(dex_number)]
    if form_number is not None:
        parts.append(f"f{form_number}")
    if costume_number is not None:
        parts.append(f"c{costume_number}")
    if is_shiny:
        parts.append("s")
    return f"{'_'.join(parts)}.png"
