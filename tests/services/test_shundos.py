import datetime

import pytest

from pokemon_go_collection.services import shundos as shundos_m

TODAY = datetime.date(2026, 10, 10)

# Pichu -> Pikachu -> Raichu, Eevee -> Vaporeon or Jolteon, and Mewtwo, which
# does not evolve.
EVOLUTION_EDGES = {
    "PICHU": ["PIKACHU"],
    "PIKACHU": ["RAICHU"],
    "EEVEE": ["VAPOREON", "JOLTEON"],
}


def get_find_entry_state_test_data():
    test_cases = [
        {
            "id": "unreleased",
            "is_released": False,
            "shiny_release_date": None,
            "is_owned": False,
            "expected_state": shundos_m.EntryState.UNRELEASED,
        },
        {
            "id": "released-without-shiny",
            "is_released": True,
            "shiny_release_date": None,
            "is_owned": False,
            "expected_state": shundos_m.EntryState.NO_SHINY,
        },
        {
            "id": "shiny-announced-for-later",
            "is_released": True,
            "shiny_release_date": datetime.date(2026, 10, 11),
            "is_owned": False,
            "expected_state": shundos_m.EntryState.NO_SHINY,
        },
        {
            "id": "shiny-released-today-makes-entry-released",
            "is_released": False,
            "shiny_release_date": TODAY,
            "is_owned": False,
            "expected_state": shundos_m.EntryState.MISSING,
        },
        {
            "id": "owned-whatever-the-statuses",
            "is_released": False,
            "shiny_release_date": None,
            "is_owned": True,
            "expected_state": shundos_m.EntryState.OWNED,
        },
    ]

    return [
        pytest.param(
            test_case["is_released"],
            test_case["shiny_release_date"],
            test_case["is_owned"],
            test_case["expected_state"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "is_released,shiny_release_date,is_owned,expected_state",
    get_find_entry_state_test_data(),
)
def test_find_entry_state(is_released, shiny_release_date, is_owned, expected_state):
    actual_state = shundos_m.find_entry_state(
        is_released, shiny_release_date, is_owned, TODAY
    )

    assert actual_state == expected_state


def get_collect_evolution_lines_test_data():
    test_cases = [
        {
            "id": "first-stage-brings-later-ones",
            "entry_ids": {"PICHU"},
            "expected_entry_ids": {"PICHU", "PIKACHU", "RAICHU"},
        },
        {
            "id": "last-stage-brings-earlier-ones",
            "entry_ids": {"RAICHU"},
            "expected_entry_ids": {"PICHU", "PIKACHU", "RAICHU"},
        },
        {
            "id": "branch-brings-sibling-branches",
            "entry_ids": {"VAPOREON"},
            "expected_entry_ids": {"EEVEE", "VAPOREON", "JOLTEON"},
        },
        {
            "id": "non-evolving-entry-alone",
            "entry_ids": {"MEWTWO"},
            "expected_entry_ids": {"MEWTWO"},
        },
        {
            "id": "several-lines-merged",
            "entry_ids": {"PIKACHU", "RAICHU", "JOLTEON"},
            "expected_entry_ids": {
                "PICHU",
                "PIKACHU",
                "RAICHU",
                "EEVEE",
                "VAPOREON",
                "JOLTEON",
            },
        },
        {
            "id": "no-entry",
            "entry_ids": set(),
            "expected_entry_ids": set(),
        },
    ]

    return [
        pytest.param(
            test_case["entry_ids"],
            test_case["expected_entry_ids"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "entry_ids,expected_entry_ids", get_collect_evolution_lines_test_data()
)
def test_collect_evolution_lines(entry_ids, expected_entry_ids):
    actual_entry_ids = shundos_m.collect_evolution_lines(EVOLUTION_EDGES, entry_ids)

    assert actual_entry_ids == expected_entry_ids
