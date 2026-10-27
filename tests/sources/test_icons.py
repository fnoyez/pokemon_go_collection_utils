import pytest

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.sources import icons as icons_m
from pokemon_go_collection.sources import masterfile as masterfile_m

GAME_NUMBERS = masterfile_m.GameNumbers(
    default_form_numbers={25: 598, 710: 2641},
    form_numbers={
        "PIKACHU_NORMAL": 598,
        "PUMPKABOO_SMALL": 2641,
        "PUMPKABOO_AVERAGE": 2642,
    },
    costume_numbers={},
)


def make_entry(dex_number, form_ids, form_suffixes):
    return catalog_m.CatalogEntry(
        entry_id=form_ids[0],
        dex_number=dex_number,
        name=form_ids[0].capitalize(),
        form_ids=form_ids,
        form_suffixes=form_suffixes,
        region=regions_m.Region.KANTO,
        is_variant=False,
        display_order=0,
        pokemon_class=None,
        base_stats=None,
        temporary_evolutions=(),
        battle_forms=(),
        is_baby=False,
        evolution_target_entry_ids=(),
        is_released=True,
        shiny_release_date=None,
    )


def get_build_icon_candidate_urls_test_data():
    test_cases = [
        {
            "id": "species-normal-form",
            "entry": make_entry(25, ("PIKACHU_NORMAL",), ("NORMAL",)),
            "expected_output": [
                (True, "uicons/25_s.png"),
                (False, "uicons/25.png"),
                (True, "pokeapi/shiny/25.png"),
                (False, "pokeapi/25.png"),
            ],
        },
        {
            "id": "default-form-then-another-form",
            "entry": make_entry(
                710, ("PUMPKABOO_SMALL", "PUMPKABOO_AVERAGE"), ("SMALL", "AVERAGE")
            ),
            "expected_output": [
                (True, "uicons/710_s.png"),
                (True, "uicons/710_f2642_s.png"),
                (False, "uicons/710.png"),
                (False, "uicons/710_f2642.png"),
                (True, "pokeapi/shiny/710.png"),
                (False, "pokeapi/710.png"),
            ],
        },
        {
            "id": "unnumbered-form-left-out",
            "entry": make_entry(
                25, ("PIKACHU_FLYING_5TH_ANNIV",), ("FLYING_5TH_ANNIV",)
            ),
            "expected_output": [
                (True, "pokeapi/shiny/25.png"),
                (False, "pokeapi/25.png"),
            ],
        },
        {
            "id": "unnumbered-form-of-a-species-without-default-form-left-out",
            "entry": make_entry(
                41, ("ZUBAT_HALLOWEEN_2026_01",), ("HALLOWEEN_2026_01",)
            ),
            "expected_output": [
                (True, "pokeapi/shiny/41.png"),
                (False, "pokeapi/41.png"),
            ],
        },
    ]

    return [
        pytest.param(
            test_case["entry"], test_case["expected_output"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "entry,expected_output", get_build_icon_candidate_urls_test_data()
)
def test_build_icon_candidate_urls(entry, expected_output):
    actual_output = icons_m.build_icon_candidate_urls(
        entry, GAME_NUMBERS, "uicons", "pokeapi"
    )
    assert actual_output == expected_output
