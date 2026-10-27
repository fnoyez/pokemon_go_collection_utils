"""Bulbapedia's list of event Pokémon, as docs/data_sources.md describes it."""

import dataclasses
import datetime
import re

EVENT_POKEMON_URL = (
    "https://bulbapedia.bulbagarden.net/w/index.php"
    "?title=Event_Pok%C3%A9mon_(GO)&action=raw"
)

# `{{MSP/GO|size=80|0025Holiday2016|Pikachu}}`, the sprite of a costumed
# Pokémon: its National Pokédex number on four digits, then Bulbapedia's code
# of the costume, then the Pokémon's name. Other parameters may come first.
_SPRITE_REGEX = re.compile(
    r"\{\{MSP/GO\|(?:[a-z]+=[^|}]*\|)*(?P<dex_number>\d{4})(?P<code>[^|}]*)"
    r"\|(?P<name>[^|}]*)\}\}"
)
_COMMENT_REGEX = re.compile(r"<!--.*?-->", flags=re.DOTALL)
# `{{Shinystar/GO|Shiny possible}}`, on an event where a shiny was possible.
_SHINY_MARK_REGEX = re.compile(r"\{\{Shinystar/GO[^}]*\}\}")
# A sprite whose image is not uploaded yet has its code commented out:
# `0025<!--0025Anniversary2026Thailand01-->`.
_COMMENTED_CODE_REGEX = re.compile(
    r"(?P<dex_number>\d{4})<!--(?P=dex_number)(?P<code>[^|}<]*)-->"
)
_MONTH_NUMBERS = {
    month_name: month_index + 1
    for month_index, month_name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    )
}
# The start of an event's dates, which give the year once, at the end of the
# range when both ends share it: `October 21 - November 2, 2025`,
# `December 31, 2022 - January 4, 2023`, `July 1, 2025`.
_START_DATE_REGEX = re.compile(
    r"(?P<month>[A-Z][a-z]+) (?P<day>\d{1,2})(?:, (?P<year>\d{4}))?"
    r"(?:\s*[-–]\s*(?:(?P<end_month>[A-Z][a-z]+) )?\d{1,2}(?:, (?P<end_year>\d{4}))?)?"
)


@dataclasses.dataclass(frozen=True)
class Sprite:
    dex_number: int
    # Bulbapedia's own code of the costume, such as `Holiday2016`; it may stand
    # for different costumes on different species.
    code: str
    name: str


@dataclasses.dataclass(frozen=True)
class Event:
    title: str
    # None when the event gives no date, such as a reward without an end.
    start_date: datetime.date | None
    is_shiny_possible: bool
    # The sub-items under the event, such as `Pikachu only` or
    # `Festive Pichu debut`.
    notes: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class EventPokemonRow:
    """A row of the list: a costume, on the Pokémon of one or more families."""

    label: str
    caught_sprites: tuple[Sprite, ...]
    evolution_only_sprites: tuple[Sprite, ...]
    events: tuple[Event, ...]


def parse_event_pokemon(text):
    """Return the rows of the list in the page's wikitext, in the page's order.

    A row whose label spans several rows lends it to each.
    """
    list_text = text[text.index("==List of Event Pokémon==") : text.index("==Trivia==")]
    rows = []
    label = None
    # The first two parts are the table's opening and its header row.
    for row_text in list_text.split("\n|-")[2:]:
        cells = _split_cells(row_text.partition("\n")[2])
        if len(cells) == 4:
            label = _clean_wikitext(cells[0])
            cells = cells[1:]
        if len(cells) != 3:
            continue
        caught_cell, evolution_only_cell, events_cell = cells
        rows.append(
            EventPokemonRow(
                label=label,
                caught_sprites=_parse_sprites(caught_cell),
                evolution_only_sprites=_parse_sprites(evolution_only_cell),
                events=_parse_events(events_cell),
            )
        )
    return rows


def _split_cells(row_text):
    """Return the cells of a table row, each starting with `|` on a line of its own."""
    cells = []
    for line in row_text.split("\n"):
        if line.startswith("|") and not line.startswith("|}"):
            cells.append(line[1:])
        elif cells:
            cells[-1] = f"{cells[-1]}\n{line}"
    return cells


def _clean_wikitext(text):
    """Return the text a reader of the page sees, for a label or a title."""
    text = re.sub(r'^\s*rowspan="\d+"\s*\|', "", text)
    # `[[target|text]]` and `[[text]]` show their text.
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    # `{{anchor|...}}` shows nothing; other templates show their first argument.
    text = re.sub(r"\{\{anchor\|[^}]*\}\}", "", text)
    text = re.sub(r"\{\{[^|}]*\|([^}|]*)(?:\|[^}]*)?\}\}", r"\1", text)
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()


def _parse_sprites(cell):
    cell = _COMMENT_REGEX.sub(
        "", _COMMENTED_CODE_REGEX.sub(r"\g<dex_number>\g<code>", cell)
    )
    return tuple(
        Sprite(int(match["dex_number"]), match["code"], match["name"])
        for match in _SPRITE_REGEX.finditer(cell)
    )


def _parse_events(cell):
    events = []
    for line in _COMMENT_REGEX.sub("", cell).split("\n"):
        if line.startswith("**") and events:
            note = _clean_wikitext(line.lstrip("* "))
            events[-1] = dataclasses.replace(
                events[-1], notes=(*events[-1].notes, note)
            )
        elif line.startswith("*"):
            text = _SHINY_MARK_REGEX.sub("", line.lstrip("* ")).strip()
            title, separator, dates = text.rpartition(":")
            if not separator:
                title, dates = text, ""
            events.append(
                Event(
                    title=_clean_wikitext(title),
                    # An event without an end gives its date in its text:
                    # `Since February 28, 2020, Pikachu Libre has served...`.
                    start_date=_parse_start_date(dates) or _parse_start_date(text),
                    is_shiny_possible=_SHINY_MARK_REGEX.search(line) is not None,
                    notes=(),
                )
            )
    return tuple(events)


def _parse_start_date(dates_text):
    match = _START_DATE_REGEX.search(dates_text)
    if match is None or match["month"] not in _MONTH_NUMBERS:
        return None
    year_text = match["year"] or match["end_year"]
    if year_text is None:
        return None
    month = _MONTH_NUMBERS[match["month"]]
    year = int(year_text)
    # `December 28 - January 3, 2024` starts the year before it ends.
    if (
        match["year"] is None
        and match["end_month"] in _MONTH_NUMBERS
        and _MONTH_NUMBERS[match["end_month"]] < month
    ):
        year -= 1
    return datetime.date(year, month, int(match["day"]))
