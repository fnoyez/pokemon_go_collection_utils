import datetime

import pytest

from pokemon_go_collection import costumes as costumes_m
from pokemon_go_collection.sources import bulbapedia as bulbapedia_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import leekduck as leekduck_m
from pokemon_go_collection.sources import national_dex as national_dex_m
from pokemon_go_collection.sources import overrides as overrides_m
from pokemon_go_collection.sources import pogo_assets as pogo_assets_m

HOLIDAY_2017 = bulbapedia_m.Event(
    title="Holiday 2017",
    start_date=datetime.date(2017, 12, 21),
    is_shiny_possible=False,
    notes=(),
)
HOLIDAY_2018 = bulbapedia_m.Event(
    title="Holiday 2018",
    start_date=datetime.date(2018, 12, 18),
    is_shiny_possible=True,
    notes=(),
)


def make_row(caught_sprites, evolution_only_sprites, events, label="Festive hat"):
    return bulbapedia_m.EventPokemonRow(
        label=label,
        caught_sprites=tuple(caught_sprites),
        evolution_only_sprites=tuple(evolution_only_sprites),
        events=tuple(events),
    )


def make_event(event, notes):
    return bulbapedia_m.Event(
        title=event.title,
        start_date=event.start_date,
        is_shiny_possible=event.is_shiny_possible,
        notes=tuple(notes),
    )


def get_find_sprite_release_dates_test_data():
    pichu = bulbapedia_m.Sprite(172, "Holiday2016", "Pichu")
    pikachu = bulbapedia_m.Sprite(25, "Holiday2016", "Pikachu")
    raichu = bulbapedia_m.Sprite(26, "Holiday2016", "Raichu")
    test_cases = [
        {
            "id": "first-event",
            "event_pokemon_rows": [
                make_row([pikachu], [raichu], [HOLIDAY_2017, HOLIDAY_2018])
            ],
            "expected_release_dates": {
                (25, "Holiday2016"): datetime.date(2017, 12, 21),
                (26, "Holiday2016"): datetime.date(2017, 12, 21),
            },
        },
        {
            "id": "only-note-leaves-out-the-other-species",
            "event_pokemon_rows": [
                make_row(
                    [pichu, pikachu],
                    [],
                    [make_event(HOLIDAY_2017, ["Pikachu only"]), HOLIDAY_2018],
                )
            ],
            "expected_release_dates": {
                (172, "Holiday2016"): datetime.date(2018, 12, 18),
                (25, "Holiday2016"): datetime.date(2017, 12, 21),
            },
        },
        {
            "id": "debut-note-leaves-out-the-events-before",
            "event_pokemon_rows": [
                make_row(
                    [pichu, pikachu],
                    [raichu],
                    [HOLIDAY_2017, make_event(HOLIDAY_2018, ["Festive Pichu debut"])],
                )
            ],
            "expected_release_dates": {
                (172, "Holiday2016"): datetime.date(2018, 12, 18),
                (25, "Holiday2016"): datetime.date(2017, 12, 21),
                (26, "Holiday2016"): datetime.date(2017, 12, 21),
            },
        },
        {
            "id": "debut-note-dates-an-evolution",
            "event_pokemon_rows": [
                make_row(
                    [pikachu],
                    [raichu],
                    [
                        HOLIDAY_2017,
                        make_event(HOLIDAY_2018, ["Festive Raichu debut"]),
                    ],
                )
            ],
            "expected_release_dates": {
                (25, "Holiday2016"): datetime.date(2017, 12, 21),
                (26, "Holiday2016"): datetime.date(2018, 12, 18),
            },
        },
        {
            "id": "earliest-of-two-rows",
            "event_pokemon_rows": [
                make_row([pikachu], [], [HOLIDAY_2018]),
                make_row([pikachu], [], [HOLIDAY_2017]),
            ],
            "expected_release_dates": {
                (25, "Holiday2016"): datetime.date(2017, 12, 21),
            },
        },
        {
            "id": "no-dated-event",
            "event_pokemon_rows": [
                make_row(
                    [pikachu],
                    [raichu],
                    [
                        bulbapedia_m.Event(
                            title="To be announced",
                            start_date=None,
                            is_shiny_possible=False,
                            notes=(),
                        )
                    ],
                )
            ],
            "expected_release_dates": {
                (25, "Holiday2016"): None,
                (26, "Holiday2016"): None,
            },
        },
    ]

    return [
        pytest.param(
            test_case["event_pokemon_rows"],
            test_case["expected_release_dates"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "event_pokemon_rows,expected_release_dates",
    get_find_sprite_release_dates_test_data(),
)
def test_find_sprite_release_dates(event_pokemon_rows, expected_release_dates):
    assert (
        costumes_m.find_sprite_release_dates(event_pokemon_rows)
        == expected_release_dates
    )


def get_find_costume_labels_test_data():
    test_cases = [
        {
            "id": "label-of-one-costume",
            "event_pokemon_rows": [
                make_row(
                    [bulbapedia_m.Sprite(25, "Holiday2016", "Pikachu")],
                    [],
                    [HOLIDAY_2017],
                )
            ],
            "expected_labels": {(25, "Holiday2016"): "Festive hat"},
        },
        {
            "id": "label-naming-a-pokemon-keeps-its-costume",
            "event_pokemon_rows": [
                make_row(
                    [bulbapedia_m.Sprite(4, "Friede", "Charmander")],
                    [bulbapedia_m.Sprite(5, "Friede", "Charmeleon")],
                    [HOLIDAY_2017],
                    label="Charmander wearing Friede's goggles",
                )
            ],
            "expected_labels": {
                (4, "Friede"): "Friede's goggles",
                (5, "Friede"): "Friede's goggles",
            },
        },
        {
            "id": "label-of-several-costumes-left-out",
            "event_pokemon_rows": [
                make_row(
                    [bulbapedia_m.Sprite(25, "Li", "Pikachu")],
                    [],
                    [HOLIDAY_2017],
                    label="Cosplay Pikachu",
                ),
                make_row(
                    [bulbapedia_m.Sprite(25, "Po", "Pikachu")],
                    [],
                    [HOLIDAY_2017],
                    label="Cosplay Pikachu",
                ),
            ],
            "expected_labels": {},
        },
    ]

    return [
        pytest.param(
            test_case["event_pokemon_rows"],
            test_case["expected_labels"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "event_pokemon_rows,expected_labels", get_find_costume_labels_test_data()
)
def test_find_costume_labels(event_pokemon_rows, expected_labels):
    assert costumes_m.find_costume_labels(event_pokemon_rows) == expected_labels


def test_build_costume_catalog_merges_the_sources():
    national_dex_species = [
        national_dex_m.Species(25, "pikachu", "Pikachu", 172, False),
        national_dex_m.Species(41, "zubat", "Zubat", None, False),
        national_dex_m.Species(150, "mewtwo", "Mewtwo", None, False),
    ]
    game_master = game_master_m.GameMaster(
        forms=(
            make_form("PIKACHU", "PIKACHU", 25),
            make_form("PIKACHU_FALL_2019", "PIKACHU", 25),
            make_form("PIKACHU_COPY_2019", "PIKACHU", 25),
            make_form("ZUBAT", "ZUBAT", 41),
            make_form("MEWTWO", "MEWTWO", 150),
            make_form("MEWTWO_A", "MEWTWO", 150),
        ),
        costume_form_ids=frozenset({"PIKACHU_FALL_2019", "MEWTWO_A"}),
        cp_multipliers=(),
        timestamp=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )
    icons = [
        pogo_assets_m.parse_icon_file_name(file_name)
        for file_name in [
            "pm25.icon.png",
            "pm25.cHOLIDAY_2016.icon.png",
            "pm25.cHOLIDAY_2016.s.icon.png",
            "pm25.cHOLIDAY_2016.g2.icon.png",
            "pm25.fCOPY_2019.icon.png",
            "pm25.cFEB_2019.icon.png",
            "pm25.cFEB_2019.s.icon.png",
        ]
    ]
    shiny_releases = [
        leekduck_m.ShinyRelease(
            dex_number=25,
            form_suffix=None,
            costume="HOLIDAY_2016",
            release_date=datetime.date(2016, 12, 25),
            asset_name="pm25.cHOLIDAY_2016",
            label="Holiday Hat",
        ),
        leekduck_m.ShinyRelease(
            dex_number=25,
            form_suffix="FALL_2019",
            costume=None,
            release_date=datetime.date(2019, 10, 17),
            asset_name="pm25.fFALL_2019",
            label="Mimikyu Costume",
        ),
    ]
    event_pokemon_rows = [
        make_row(
            [bulbapedia_m.Sprite(25, "Holiday2016", "Pikachu")],
            [],
            [
                bulbapedia_m.Event(
                    title="Holiday 2016",
                    start_date=datetime.date(2016, 12, 12),
                    is_shiny_possible=False,
                    notes=(),
                ),
                HOLIDAY_2018,
            ],
        ),
        make_row(
            [bulbapedia_m.Sprite(25, "Copy2019", "Pikachu")],
            [],
            [
                bulbapedia_m.Event(
                    title="Pokémon Day 2020",
                    start_date=datetime.date(2020, 2, 25),
                    is_shiny_possible=False,
                    notes=(),
                )
            ],
            label="Clone",
        ),
        make_row(
            [bulbapedia_m.Sprite(41, "TopHat", "Zubat")],
            [],
            [
                bulbapedia_m.Event(
                    title="Halloween 2026",
                    start_date=datetime.date(2026, 10, 27),
                    is_shiny_possible=False,
                    notes=(),
                )
            ],
            label="Top hat",
        ),
        make_row(
            [bulbapedia_m.Sprite(150, "A", "Mewtwo")],
            [],
            [HOLIDAY_2018],
            label="Armored Mewtwo",
        ),
        make_row(
            [bulbapedia_m.Sprite(25, "Unmatched", "Pikachu")],
            [],
            [HOLIDAY_2017],
            label="Unmatched",
        ),
    ]
    costume_matches = [
        make_match(25, "Holiday2016", None, "HOLIDAY_2016"),
        # A costume form the game master does not flag.
        make_match(25, "Copy2019", "COPY_2019", None),
        make_match(41, "TopHat", None, None),
        make_match(25, "Gone", None, "GONE"),
        # A costume form an override makes a catalog entry.
        make_match(150, "A", "A", None),
    ]
    form_overrides = {
        "MEWTWO_A": overrides_m.FormOverride(
            form_id="MEWTWO_A",
            decision=overrides_m.FormDecision.DISTINCT,
            target_form_id=None,
            variant_region=None,
        )
    }

    costume_catalog = costumes_m.build_costume_catalog(
        national_dex_species,
        game_master,
        form_overrides,
        icons,
        shiny_releases,
        event_pokemon_rows,
        costume_matches,
    )

    assert costume_catalog.costumed_pokemons == (
        costumes_m.CostumedPokemon(
            costumed_pokemon_id="PIKACHU.HOLIDAY_2016",
            key=costumes_m.CostumedPokemonKey(25, None, "HOLIDAY_2016"),
            name="Pikachu (Holiday Hat)",
            release_date=datetime.date(2016, 12, 12),
            shiny_release_date=datetime.date(2016, 12, 25),
            pogo_assets_icon_file_names=(
                "pm25.cHOLIDAY_2016.icon.png",
                "pm25.cHOLIDAY_2016.s.icon.png",
            ),
            leekduck_asset_name="pm25.cHOLIDAY_2016",
            bulbapedia_codes=("Holiday2016",),
            costume_year=2016,
        ),
        costumes_m.CostumedPokemon(
            costumed_pokemon_id="PIKACHU_COPY_2019",
            key=costumes_m.CostumedPokemonKey(25, "COPY_2019", None),
            name="Pikachu (Clone)",
            release_date=datetime.date(2020, 2, 25),
            shiny_release_date=None,
            pogo_assets_icon_file_names=("pm25.fCOPY_2019.icon.png", None),
            leekduck_asset_name=None,
            bulbapedia_codes=("Copy2019",),
            costume_year=2019,
        ),
        costumes_m.CostumedPokemon(
            costumed_pokemon_id="PIKACHU.FEB_2019",
            key=costumes_m.CostumedPokemonKey(25, None, "FEB_2019"),
            name="Pikachu (Feb 2019)",
            release_date=None,
            shiny_release_date=None,
            pogo_assets_icon_file_names=(
                "pm25.cFEB_2019.icon.png",
                "pm25.cFEB_2019.s.icon.png",
            ),
            leekduck_asset_name=None,
            bulbapedia_codes=(),
            costume_year=2019,
        ),
        costumes_m.CostumedPokemon(
            costumed_pokemon_id="PIKACHU_FALL_2019",
            key=costumes_m.CostumedPokemonKey(25, "FALL_2019", None),
            name="Pikachu (Mimikyu Costume)",
            release_date=None,
            shiny_release_date=datetime.date(2019, 10, 17),
            pogo_assets_icon_file_names=None,
            leekduck_asset_name="pm25.fFALL_2019",
            bulbapedia_codes=(),
            costume_year=2019,
        ),
        costumes_m.CostumedPokemon(
            costumed_pokemon_id="ZUBAT.TopHat",
            key=costumes_m.CostumedPokemonKey(41, None, None, "TopHat"),
            name="Zubat (Top hat)",
            release_date=datetime.date(2026, 10, 27),
            shiny_release_date=None,
            pogo_assets_icon_file_names=None,
            leekduck_asset_name=None,
            bulbapedia_codes=("TopHat",),
            costume_year=None,
        ),
    )
    assert costume_catalog.unmatched_sprites == (
        bulbapedia_m.Sprite(25, "Unmatched", "Pikachu"),
    )
    assert costume_catalog.unused_matches == (make_match(25, "Gone", None, "GONE"),)


def make_form(form_id, species_id, dex_number):
    return game_master_m.PokemonForm(
        form_id=form_id,
        species_id=species_id,
        dex_number=dex_number,
        stats=(100, 100, 100),
        types=("POKEMON_TYPE_NORMAL",),
        evolutions=(),
        pokemon_class=None,
        temporary_evolutions=(),
    )


def make_match(dex_number, bulbapedia_code, form_suffix, costume):
    return overrides_m.CostumeMatch(
        dex_number=dex_number,
        bulbapedia_code=bulbapedia_code,
        form_suffix=form_suffix,
        costume=costume,
        release_date=None,
    )


def get_is_unreleasable_test_data():
    today = datetime.date(2026, 10, 27)
    test_cases = [
        {
            "id": "costume-of-a-past-year-in-no-event",
            "release_date": None,
            "costume_year": 2018,
            "today": today,
            "expected_output": True,
        },
        {
            "id": "costume-of-this-year-in-no-event",
            "release_date": None,
            "costume_year": 2026,
            "today": today,
            "expected_output": False,
        },
        {
            "id": "costume-of-no-known-year",
            "release_date": None,
            "costume_year": None,
            "today": today,
            "expected_output": False,
        },
        {
            "id": "announced",
            "release_date": datetime.date(2027, 2, 13),
            "costume_year": 2018,
            "today": today,
            "expected_output": False,
        },
    ]

    return [
        pytest.param(
            test_case["release_date"],
            test_case["costume_year"],
            test_case["today"],
            test_case["expected_output"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "release_date,costume_year,today,expected_output",
    get_is_unreleasable_test_data(),
)
def test_is_unreleasable(release_date, costume_year, today, expected_output):
    costumed_pokemon = costumes_m.CostumedPokemon(
        costumed_pokemon_id="PICHU.FALL_2018",
        key=costumes_m.CostumedPokemonKey(172, None, "FALL_2018"),
        name="Pichu (Fall 2018)",
        release_date=release_date,
        shiny_release_date=None,
        pogo_assets_icon_file_names=None,
        leekduck_asset_name=None,
        bulbapedia_codes=(),
        costume_year=costume_year,
    )

    assert costumes_m.is_unreleasable(costumed_pokemon, today) == expected_output
