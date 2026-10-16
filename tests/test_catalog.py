import datetime

import pytest

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import leekduck as leekduck_m
from pokemon_go_collection.sources import national_dex as national_dex_m
from pokemon_go_collection.sources import overrides as overrides_m
from pokemon_go_collection.sources import pvpoke as pvpoke_m

# A small world exercising each catalog rule: a regional form with an
# exclusive evolution (Farfetch'd), an evolution the base form reaches
# (Scyther -> Kleavor), forms distinct by their types (Wormadam) or by their
# evolutions only (Burmy), a costume (Pikachu), cosmetic forms (Unown), and a
# form an override makes distinct, evolving into a species the game master
# does not hold yet (white-striped Basculin -> Basculegion).

NATIONAL_DEX_SPECIES = [
    national_dex_m.Species(
        dex_number=25,
        identifier="pikachu",
        name="Pikachu",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=83,
        identifier="farfetchd",
        name="Farfetch'd",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=123,
        identifier="scyther",
        name="Scyther",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=201,
        identifier="unown",
        name="Unown",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=412,
        identifier="burmy",
        name="Burmy",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=413,
        identifier="wormadam",
        name="Wormadam",
        evolves_from_dex_number=412,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=550,
        identifier="basculin",
        name="Basculin",
        evolves_from_dex_number=None,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=865,
        identifier="sirfetchd",
        name="Sirfetch'd",
        evolves_from_dex_number=83,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=900,
        identifier="kleavor",
        name="Kleavor",
        evolves_from_dex_number=123,
        is_baby=False,
    ),
    national_dex_m.Species(
        dex_number=902,
        identifier="basculegion",
        name="Basculegion",
        evolves_from_dex_number=550,
        is_baby=False,
    ),
]


def make_form(
    form_id,
    species_id,
    dex_number,
    stats,
    types,
    evolutions=(),
    temporary_evolutions=(),
):
    return game_master_m.PokemonForm(
        form_id=form_id,
        species_id=species_id,
        dex_number=dex_number,
        stats=stats,
        types=types,
        evolutions=evolutions,
        pokemon_class=None,
        temporary_evolutions=temporary_evolutions,
    )


GAME_MASTER = game_master_m.GameMaster(
    forms=(
        make_form("PIKACHU", "PIKACHU", 25, (112, 96, 111), ("ELECTRIC",)),
        # Pikachu has no Mega evolution; this one stands for any.
        make_form(
            "PIKACHU_NORMAL",
            "PIKACHU",
            25,
            (112, 96, 111),
            ("ELECTRIC",),
            temporary_evolutions=(
                game_master_m.TemporaryEvolution("MEGA", (200, 150, 111)),
            ),
        ),
        make_form("PIKACHU_FALL_2019", "PIKACHU", 25, (112, 96, 111), ("ELECTRIC",)),
        make_form("FARFETCHD", "FARFETCHD", 83, (124, 115, 141), ("NORMAL", "FLYING")),
        make_form(
            "FARFETCHD_NORMAL", "FARFETCHD", 83, (124, 115, 141), ("NORMAL", "FLYING")
        ),
        make_form(
            "FARFETCHD_GALARIAN",
            "FARFETCHD",
            83,
            (174, 114, 141),
            ("FIGHTING",),
            evolutions=(("SIRFETCHD", "SIRFETCHD_NORMAL"),),
        ),
        make_form(
            "SCYTHER",
            "SCYTHER",
            123,
            (218, 170, 172),
            ("BUG", "FLYING"),
            evolutions=(("KLEAVOR", None),),
        ),
        make_form("UNOWN", "UNOWN", 201, (136, 91, 134), ("PSYCHIC",)),
        make_form("UNOWN_A", "UNOWN", 201, (136, 91, 134), ("PSYCHIC",)),
        make_form("UNOWN_B", "UNOWN", 201, (136, 91, 134), ("PSYCHIC",)),
        make_form(
            "BURMY",
            "BURMY",
            412,
            (53, 83, 120),
            ("BUG",),
            evolutions=(("WORMADAM", "WORMADAM_PLANT"),),
        ),
        make_form(
            "BURMY_PLANT",
            "BURMY",
            412,
            (53, 83, 120),
            ("BUG",),
            evolutions=(("WORMADAM", "WORMADAM_PLANT"),),
        ),
        make_form(
            "BURMY_SANDY",
            "BURMY",
            412,
            (53, 83, 120),
            ("BUG",),
            evolutions=(("WORMADAM", "WORMADAM_SANDY"),),
        ),
        make_form("WORMADAM", "WORMADAM", 413, (141, 180, 155), ("BUG", "GRASS")),
        make_form("WORMADAM_PLANT", "WORMADAM", 413, (141, 180, 155), ("BUG", "GRASS")),
        make_form(
            "WORMADAM_SANDY", "WORMADAM", 413, (141, 180, 155), ("BUG", "GROUND")
        ),
        make_form("BASCULIN", "BASCULIN", 550, (189, 129, 172), ("WATER",)),
        make_form(
            "BASCULIN_WHITE_STRIPED", "BASCULIN", 550, (189, 129, 172), ("WATER",)
        ),
        make_form("SIRFETCHD", "SIRFETCHD", 865, (248, 176, 158), ("FIGHTING",)),
        make_form("SIRFETCHD_NORMAL", "SIRFETCHD", 865, (248, 176, 158), ("FIGHTING",)),
        make_form("KLEAVOR", "KLEAVOR", 900, (253, 159, 172), ("BUG", "ROCK")),
    ),
    costume_form_ids=frozenset({"PIKACHU_FALL_2019"}),
    cp_multipliers=(),
    timestamp=datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc),
)

FORM_OVERRIDES = {
    "BASCULIN_WHITE_STRIPED": overrides_m.FormOverride(
        form_id="BASCULIN_WHITE_STRIPED",
        decision=overrides_m.FormDecision.DISTINCT,
        target_form_id=None,
        variant_region=regions_m.Region.HISUI,
    ),
}

PVPOKE_SPECIES = [
    pvpoke_m.PvpokeSpecies(dex_number=25, species_id="pikachu", is_released=True),
    pvpoke_m.PvpokeSpecies(
        dex_number=83, species_id="farfetchd_galarian", is_released=True
    ),
    pvpoke_m.PvpokeSpecies(dex_number=412, species_id="burmy_plant", is_released=True),
    pvpoke_m.PvpokeSpecies(dex_number=412, species_id="burmy_sandy", is_released=True),
    pvpoke_m.PvpokeSpecies(dex_number=900, species_id="kleavor", is_released=False),
]

SHINY_RELEASES = [
    leekduck_m.ShinyRelease(
        dex_number=25,
        form_suffix="FALL_2019",
        is_costume=False,
        release_date=datetime.date(2019, 10, 17),
    ),
    leekduck_m.ShinyRelease(
        dex_number=83,
        form_suffix="GALARIAN",
        is_costume=False,
        release_date=datetime.date(2021, 8, 20),
    ),
    leekduck_m.ShinyRelease(
        dex_number=83,
        form_suffix="GALARIAN",
        is_costume=True,
        release_date=datetime.date(2020, 1, 1),
    ),
    leekduck_m.ShinyRelease(
        dex_number=412,
        form_suffix="BURMY_SANDY",
        is_costume=False,
        release_date=datetime.date(2019, 12, 5),
    ),
    leekduck_m.ShinyRelease(
        dex_number=201,
        form_suffix="B",
        is_costume=False,
        release_date=datetime.date(2027, 1, 1),
    ),
]

RELEASE_OVERRIDE_ENTRY_IDS = frozenset({"UNOWN"})


def test_build_catalog_orders_entries():
    entries = catalog_m.build_catalog(
        NATIONAL_DEX_SPECIES,
        GAME_MASTER,
        FORM_OVERRIDES,
        PVPOKE_SPECIES,
        SHINY_RELEASES,
        RELEASE_OVERRIDE_ENTRY_IDS,
    )

    actual_order = [
        (entry.entry_id, entry.region, entry.is_variant) for entry in entries
    ]

    assert actual_order == [
        ("PIKACHU", regions_m.Region.KANTO, False),
        ("FARFETCHD", regions_m.Region.KANTO, False),
        ("SCYTHER", regions_m.Region.KANTO, False),
        ("UNOWN", regions_m.Region.JOHTO, False),
        ("BURMY", regions_m.Region.SINNOH, False),
        ("BURMY_SANDY", regions_m.Region.SINNOH, False),
        ("WORMADAM", regions_m.Region.SINNOH, False),
        ("WORMADAM_SANDY", regions_m.Region.SINNOH, False),
        ("BASCULIN", regions_m.Region.UNOVA, False),
        ("FARFETCHD_GALARIAN", regions_m.Region.GALAR, True),
        ("SIRFETCHD", regions_m.Region.GALAR, True),
        ("KLEAVOR", regions_m.Region.HISUI, False),
        ("BASCULEGION", regions_m.Region.HISUI, False),
        ("BASCULIN_WHITE_STRIPED", regions_m.Region.HISUI, True),
    ]
    assert [entry.display_order for entry in entries] == list(range(len(entries)))


def test_build_catalog_names_entries_and_merges_forms():
    entries = catalog_m.build_catalog(
        NATIONAL_DEX_SPECIES,
        GAME_MASTER,
        FORM_OVERRIDES,
        PVPOKE_SPECIES,
        SHINY_RELEASES,
        RELEASE_OVERRIDE_ENTRY_IDS,
    )

    actual_entries = {entry.entry_id: (entry.name, entry.form_ids) for entry in entries}

    assert actual_entries["PIKACHU"] == ("Pikachu", ("PIKACHU_NORMAL", "PIKACHU"))
    assert actual_entries["UNOWN"] == ("Unown", ("UNOWN", "UNOWN_A", "UNOWN_B"))
    assert actual_entries["BURMY"] == ("Burmy", ("BURMY", "BURMY_PLANT"))
    assert actual_entries["BURMY_SANDY"] == ("Burmy (Sandy)", ("BURMY_SANDY",))
    assert actual_entries["FARFETCHD_GALARIAN"] == (
        "Farfetch'd (Galarian)",
        ("FARFETCHD_GALARIAN",),
    )
    assert actual_entries["BASCULEGION"] == ("Basculegion", ("BASCULEGION",))


def test_build_catalog_takes_the_temporary_evolutions_of_the_representative_form():
    entries = catalog_m.build_catalog(
        NATIONAL_DEX_SPECIES,
        GAME_MASTER,
        FORM_OVERRIDES,
        PVPOKE_SPECIES,
        SHINY_RELEASES,
        RELEASE_OVERRIDE_ENTRY_IDS,
    )

    actual_temporary_evolutions = {
        entry.entry_id: entry.temporary_evolutions for entry in entries
    }

    assert actual_temporary_evolutions["PIKACHU"] == (
        game_master_m.TemporaryEvolution("MEGA", (200, 150, 111)),
    )
    assert actual_temporary_evolutions["FARFETCHD"] == ()


def test_build_catalog_links_evolutions():
    entries = catalog_m.build_catalog(
        NATIONAL_DEX_SPECIES,
        GAME_MASTER,
        FORM_OVERRIDES,
        PVPOKE_SPECIES,
        SHINY_RELEASES,
        RELEASE_OVERRIDE_ENTRY_IDS,
    )

    actual_evolutions = {
        entry.entry_id: entry.evolution_target_entry_ids
        for entry in entries
        if entry.evolution_target_entry_ids
    }

    assert actual_evolutions == {
        "FARFETCHD_GALARIAN": ("SIRFETCHD",),
        "SCYTHER": ("KLEAVOR",),
        "BURMY": ("WORMADAM",),
        "BURMY_SANDY": ("WORMADAM_SANDY",),
        # Absent from the game master, linked to its species' base entry.
        "BASCULIN": ("BASCULEGION",),
    }


def test_build_catalog_splits_a_species_whose_base_form_an_override_chooses():
    national_dex_species = [
        national_dex_m.Species(
            dex_number=585,
            identifier="deerling",
            name="Deerling",
            evolves_from_dex_number=None,
            is_baby=False,
        ),
        national_dex_m.Species(
            dex_number=586,
            identifier="sawsbuck",
            name="Sawsbuck",
            evolves_from_dex_number=585,
            is_baby=False,
        ),
    ]
    game_master = game_master_m.GameMaster(
        forms=(
            make_form("DEERLING", "DEERLING", 585, (115, 100, 155), ("NORMAL",)),
            *(
                make_form(
                    f"DEERLING_{season}",
                    "DEERLING",
                    585,
                    (115, 100, 155),
                    ("NORMAL",),
                    evolutions=(("SAWSBUCK", f"SAWSBUCK_{season}"),),
                )
                for season in ("SPRING", "SUMMER", "AUTUMN")
            ),
            make_form("SAWSBUCK", "SAWSBUCK", 586, (198, 146, 190), ("NORMAL",)),
            *(
                make_form(
                    f"SAWSBUCK_{season}", "SAWSBUCK", 586, (198, 146, 190), ("NORMAL",)
                )
                for season in ("SPRING", "SUMMER", "AUTUMN")
            ),
        ),
        costume_form_ids=frozenset(),
        cp_multipliers=(),
        timestamp=datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc),
    )
    # The override lines order the species' entries: Autumn before Summer.
    form_overrides = {
        form_id: overrides_m.FormOverride(
            form_id=form_id,
            decision=decision,
            target_form_id=None,
            variant_region=None,
        )
        for species_id in ("DEERLING", "SAWSBUCK")
        for form_id, decision in (
            (f"{species_id}_SPRING", overrides_m.FormDecision.BASE),
            (f"{species_id}_AUTUMN", overrides_m.FormDecision.DISTINCT),
            (f"{species_id}_SUMMER", overrides_m.FormDecision.DISTINCT),
        )
    }

    entries = catalog_m.build_catalog(
        national_dex_species,
        game_master,
        form_overrides,
        pvpoke_species=[],
        shiny_releases=[],
        release_override_entry_ids=frozenset(),
    )

    actual_entries = [
        (entry.entry_id, entry.name, entry.form_ids, entry.evolution_target_entry_ids)
        for entry in entries
    ]
    assert actual_entries == [
        (
            "DEERLING",
            "Deerling (Spring)",
            ("DEERLING_SPRING", "DEERLING"),
            ("SAWSBUCK",),
        ),
        (
            "DEERLING_AUTUMN",
            "Deerling (Autumn)",
            ("DEERLING_AUTUMN",),
            ("SAWSBUCK_AUTUMN",),
        ),
        (
            "DEERLING_SUMMER",
            "Deerling (Summer)",
            ("DEERLING_SUMMER",),
            ("SAWSBUCK_SUMMER",),
        ),
        ("SAWSBUCK", "Sawsbuck (Spring)", ("SAWSBUCK_SPRING", "SAWSBUCK"), ()),
        ("SAWSBUCK_AUTUMN", "Sawsbuck (Autumn)", ("SAWSBUCK_AUTUMN",), ()),
        ("SAWSBUCK_SUMMER", "Sawsbuck (Summer)", ("SAWSBUCK_SUMMER",), ()),
    ]


def test_build_catalog_names_a_form_by_its_symbol():
    game_master = game_master_m.GameMaster(
        forms=tuple(
            make_form(form_id, "UNOWN", 201, (136, 91, 134), ("PSYCHIC",))
            for form_id in ("UNOWN", "UNOWN_A", "UNOWN_EXCLAMATION_POINT")
        ),
        costume_form_ids=frozenset(),
        cp_multipliers=(),
        timestamp=datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc),
    )
    form_overrides = {
        form_id: overrides_m.FormOverride(
            form_id=form_id,
            decision=decision,
            target_form_id=None,
            variant_region=None,
        )
        for form_id, decision in (
            ("UNOWN_A", overrides_m.FormDecision.BASE),
            ("UNOWN_EXCLAMATION_POINT", overrides_m.FormDecision.DISTINCT),
        )
    }
    unown_species = [
        species for species in NATIONAL_DEX_SPECIES if species.dex_number == 201
    ]

    entries = catalog_m.build_catalog(
        unown_species,
        game_master,
        form_overrides,
        pvpoke_species=[],
        shiny_releases=[],
        release_override_entry_ids=frozenset(),
    )

    assert [entry.name for entry in entries] == ["Unown (A)", "Unown (!)"]


def get_build_form_label_test_data():
    test_cases = [
        {
            "id": "regional-token-as-adjective",
            "form_id": "TAUROS_PALDEA_AQUA",
            "species_id": "TAUROS",
            "expected_label": "Paldean Aqua",
        },
        {
            "id": "words-capitalized",
            "form_id": "FURFROU_LA_REINE",
            "species_id": "FURFROU",
            "expected_label": "La Reine",
        },
        {
            "id": "symbol",
            "form_id": "UNOWN_QUESTION_MARK",
            "species_id": "UNOWN",
            "expected_label": "?",
        },
        {
            "id": "small-word",
            "form_id": "MAUSHOLD_FAMILY_OF_FOUR",
            "species_id": "MAUSHOLD",
            "expected_label": "Family of Four",
        },
        {
            "id": "games-spelling",
            "form_id": "VIVILLON_POKEBALL",
            "species_id": "VIVILLON",
            "expected_label": "Poké Ball",
        },
        {
            "id": "number-named-for-what-it-counts",
            "form_id": "DUDUNSPARCE_THREE",
            "species_id": "DUDUNSPARCE",
            "expected_label": "Three-Segment",
        },
    ]

    return [
        pytest.param(
            test_case["form_id"],
            test_case["species_id"],
            test_case["expected_label"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "form_id,species_id,expected_label", get_build_form_label_test_data()
)
def test_build_form_label(form_id, species_id, expected_label):
    assert catalog_m.build_form_label(form_id, species_id) == expected_label


def get_build_catalog_statuses_test_data():
    test_cases = [
        {
            "id": "pvpoke-name-unmatched-goes-to-base-entry",
            "entry_id": "PIKACHU",
            "expected_is_released": True,
            "expected_shiny_release_date": None,
        },
        {
            "id": "regional-form-matched-by-name-and-suffix",
            "entry_id": "FARFETCHD_GALARIAN",
            "expected_is_released": True,
            "expected_shiny_release_date": datetime.date(2021, 8, 20),
        },
        {
            "id": "nothing-known-about-base-entry",
            "entry_id": "FARFETCHD",
            "expected_is_released": False,
            "expected_shiny_release_date": None,
        },
        {
            "id": "leekduck-full-form-identifier-matched",
            "entry_id": "BURMY_SANDY",
            "expected_is_released": True,
            "expected_shiny_release_date": datetime.date(2019, 12, 5),
        },
        {
            "id": "release-override-and-future-shiny-of-merged-form",
            "entry_id": "UNOWN",
            "expected_is_released": True,
            "expected_shiny_release_date": datetime.date(2027, 1, 1),
        },
        {
            "id": "pvpoke-unreleased",
            "entry_id": "KLEAVOR",
            "expected_is_released": False,
            "expected_shiny_release_date": None,
        },
    ]

    return [
        pytest.param(
            test_case["entry_id"],
            test_case["expected_is_released"],
            test_case["expected_shiny_release_date"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "entry_id,expected_is_released,expected_shiny_release_date",
    get_build_catalog_statuses_test_data(),
)
def test_build_catalog_statuses(
    entry_id, expected_is_released, expected_shiny_release_date
):
    entries = catalog_m.build_catalog(
        NATIONAL_DEX_SPECIES,
        GAME_MASTER,
        FORM_OVERRIDES,
        PVPOKE_SPECIES,
        SHINY_RELEASES,
        RELEASE_OVERRIDE_ENTRY_IDS,
    )

    entry = next(entry for entry in entries if entry.entry_id == entry_id)

    assert (entry.is_released, entry.shiny_release_date) == (
        expected_is_released,
        expected_shiny_release_date,
    )


def get_build_temporary_evolution_name_test_data():
    test_cases = [
        {
            "id": "mega",
            "entry_name": "Venusaur",
            "temporary_evolution_id": "MEGA",
            "expected_name": "Mega Venusaur",
        },
        {
            "id": "mega-x",
            "entry_name": "Charizard",
            "temporary_evolution_id": "MEGA_X",
            "expected_name": "Mega Charizard X",
        },
        {
            "id": "primal",
            "entry_name": "Kyogre",
            "temporary_evolution_id": "PRIMAL",
            "expected_name": "Primal Kyogre",
        },
    ]

    return [
        pytest.param(
            test_case["entry_name"],
            test_case["temporary_evolution_id"],
            test_case["expected_name"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "entry_name,temporary_evolution_id,expected_name",
    get_build_temporary_evolution_name_test_data(),
)
def test_build_temporary_evolution_name(
    entry_name, temporary_evolution_id, expected_name
):
    assert (
        catalog_m.build_temporary_evolution_name(entry_name, temporary_evolution_id)
        == expected_name
    )


def get_build_pvpoke_name_candidates_test_data():
    test_cases = [
        {
            "id": "alolan-spelling",
            "form_id": "MEOWTH_ALOLA",
            "expected_candidate": "meowthalolan",
        },
        {
            "id": "paldean-breed-without-region",
            "form_id": "TAUROS_PALDEA_AQUA",
            "expected_candidate": "taurosaqua",
        },
        {
            "id": "paldean-spelling",
            "form_id": "WOOPER_PALDEA",
            "expected_candidate": "wooperpaldean",
        },
        {
            "id": "normal-suffix-dropped",
            "form_id": "IRONBOULDER_NORMAL",
            "expected_candidate": "ironboulder",
        },
        {
            "id": "ten-percent-as-number",
            "form_id": "ZYGARDE_TEN_PERCENT",
            "expected_candidate": "zygarde10",
        },
    ]

    return [
        pytest.param(
            test_case["form_id"], test_case["expected_candidate"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "form_id,expected_candidate", get_build_pvpoke_name_candidates_test_data()
)
def test_build_pvpoke_name_candidates(form_id, expected_candidate):
    actual_candidates = catalog_m.build_pvpoke_name_candidates(form_id)

    assert expected_candidate in actual_candidates
