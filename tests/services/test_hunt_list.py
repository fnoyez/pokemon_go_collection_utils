import textwrap

import pytest

from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.services import hunt_list as hunt_list_m
from pokemon_go_collection.services import shundos as shundos_m
from pokemon_go_collection.sources import game_master as game_master_m

MISSING = shundos_m.EntryState.MISSING
OWNED = shundos_m.EntryState.OWNED
NO_SHINY = shundos_m.EntryState.NO_SHINY

# Pichu -> Pikachu -> Raichu, Magikarp -> Gyarados, Eevee -> Vaporeon or
# Jolteon, and Mewtwo, which does not evolve.
EVOLUTION_EDGES = {
    "PICHU": ["PIKACHU"],
    "PIKACHU": ["RAICHU"],
    "MAGIKARP": ["GYARADOS"],
    "EEVEE": ["VAPOREON", "JOLTEON"],
}


def make_board_entry(entry_id, state, pokemon_class=None, is_baby=False):
    return shundos_m.BoardEntry(
        entry_id=entry_id,
        dex_number=0,
        name=entry_id.capitalize(),
        region=regions_m.Region.KANTO,
        is_variant=False,
        icon_file_name=None,
        pokemon_class=pokemon_class,
        is_baby=is_baby,
        state=state,
    )


def get_select_hunt_entries_test_data():
    test_cases = [
        {
            "id": "missing-evolution-lists-its-line",
            "board_entries": [
                make_board_entry("MAGIKARP", OWNED),
                make_board_entry("GYARADOS", MISSING),
            ],
            "expected_entry_ids": ["MAGIKARP", "GYARADOS"],
        },
        {
            "id": "missing-first-stage-lists-it-alone",
            "board_entries": [
                make_board_entry("MAGIKARP", MISSING),
                make_board_entry("GYARADOS", OWNED),
            ],
            "expected_entry_ids": ["MAGIKARP"],
        },
        {
            "id": "complete-line-not-listed",
            "board_entries": [
                make_board_entry("MAGIKARP", OWNED),
                make_board_entry("GYARADOS", OWNED),
            ],
            "expected_entry_ids": [],
        },
        {
            "id": "every-earlier-stage-listed",
            "board_entries": [
                make_board_entry("PICHU", OWNED),
                make_board_entry("PIKACHU", OWNED),
                make_board_entry("RAICHU", MISSING),
            ],
            "expected_entry_ids": ["PICHU", "PIKACHU", "RAICHU"],
        },
        {
            "id": "earlier-stage-without-shiny-left-out",
            "board_entries": [
                make_board_entry("PICHU", NO_SHINY),
                make_board_entry("PIKACHU", OWNED),
                make_board_entry("RAICHU", MISSING),
            ],
            "expected_entry_ids": ["PIKACHU", "RAICHU"],
        },
        {
            "id": "baby-left-out",
            "board_entries": [
                make_board_entry("PICHU", OWNED, is_baby=True),
                make_board_entry("PIKACHU", OWNED),
                make_board_entry("RAICHU", MISSING),
            ],
            "expected_entry_ids": ["PIKACHU", "RAICHU"],
        },
        {
            "id": "other-branch-not-listed",
            "board_entries": [
                make_board_entry("EEVEE", OWNED),
                make_board_entry("VAPOREON", MISSING),
                make_board_entry("JOLTEON", OWNED),
            ],
            "expected_entry_ids": ["EEVEE", "VAPOREON"],
        },
        {
            "id": "legendary-left-out",
            "board_entries": [
                make_board_entry(
                    "MEWTWO",
                    MISSING,
                    pokemon_class=game_master_m.PokemonClass.LEGENDARY,
                ),
            ],
            "expected_entry_ids": [],
        },
    ]

    return [
        pytest.param(
            test_case["board_entries"],
            test_case["expected_entry_ids"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "board_entries,expected_entry_ids",
    get_select_hunt_entries_test_data(),
)
def test_select_hunt_entries(board_entries, expected_entry_ids):
    hunt_entries = hunt_list_m.select_hunt_entries(board_entries, EVOLUTION_EDGES)

    assert [entry.entry_id for entry in hunt_entries] == expected_entry_ids


def test_build_hunt_list_csv():
    hunt_entries = [
        shundos_m.BoardEntry(
            entry_id="FARFETCHD_GALARIAN",
            dex_number=83,
            name="Farfetch'd (Galarian)",
            region=regions_m.Region.GALAR,
            is_variant=True,
            icon_file_name=None,
            pokemon_class=None,
            is_baby=False,
            state=MISSING,
        ),
        make_board_entry("MAGIKARP", OWNED),
    ]

    csv_text = hunt_list_m.build_hunt_list_csv(hunt_entries)

    assert csv_text == textwrap.dedent(
        """\
        dex number,name
        83,Farfetch'd (Galarian)
        0,Magikarp
        """
    )
