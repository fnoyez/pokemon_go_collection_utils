"""The PokeMiners pogo_assets repository, as docs/data_sources.md describes it."""

import dataclasses
import os
import re

# Where the repository keeps the icons named after the game's identifiers.
ICONS_FOLDER_RELATIVE_PATH = "Images/Pokemon/Addressable Assets"

# `pm<dex number>`, then `.f<form>`, `.c<costume>`, `.g2` for the female icon
# and `.s` for the shiny, each optional, then `.icon.png`.
_ICON_FILE_NAME_REGEX = re.compile(
    r"^pm(?P<dex_number>\d+)"
    r"(?:\.f(?P<form_suffix>[A-Za-z0-9_]+))?"
    r"(?:\.c(?P<costume>[A-Za-z0-9_]+))?"
    r"(?P<female>\.g2)?"
    r"(?P<shiny>\.s)?"
    r"\.icon\.png$"
)


@dataclasses.dataclass(frozen=True)
class Icon:
    file_name: str
    dex_number: int
    # The form identifier without its species prefix, as the file names write
    # it; None for the species itself.
    form_suffix: str | None
    # The game's costume name, as the file names write it; None without a costume.
    costume: str | None
    is_female: bool
    is_shiny: bool


def list_icons(repository_folder_path):
    """Return the icons of the repository, by file name."""
    icons_folder_path = repository_folder_path / ICONS_FOLDER_RELATIVE_PATH
    return sorted(
        (
            icon
            for icon in map(parse_icon_file_name, os.listdir(icons_folder_path))
            if icon is not None
        ),
        key=lambda icon: icon.file_name,
    )


def parse_icon_file_name(file_name):
    """Return the icon a file name stands for, or None for another kind of file."""
    match = _ICON_FILE_NAME_REGEX.match(file_name)
    if match is None:
        return None
    return Icon(
        file_name=file_name,
        dex_number=int(match["dex_number"]),
        form_suffix=match["form_suffix"],
        costume=match["costume"],
        is_female=match["female"] is not None,
        is_shiny=match["shiny"] is not None,
    )
