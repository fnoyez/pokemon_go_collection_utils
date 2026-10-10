from contextlib import nullcontext as does_not_raise

import pytest

from pokemon_go_collection import regions as regions_m


def get_find_region_test_data():
    test_cases = [
        {
            "id": "first-kanto",
            "dex_number": 1,
            "expected_region": regions_m.Region.KANTO,
            "expectation": does_not_raise(),
        },
        {
            "id": "melmetal-in-alola",
            "dex_number": 809,
            "expected_region": regions_m.Region.ALOLA,
            "expectation": does_not_raise(),
        },
        {
            "id": "last-galar",
            "dex_number": 898,
            "expected_region": regions_m.Region.GALAR,
            "expectation": does_not_raise(),
        },
        {
            "id": "first-hisui",
            "dex_number": 899,
            "expected_region": regions_m.Region.HISUI,
            "expectation": does_not_raise(),
        },
        {
            "id": "undeclared-number-raises",
            "dex_number": 1026,
            "expected_region": None,
            "expectation": pytest.raises(ValueError),
        },
    ]

    return [
        pytest.param(
            test_case["dex_number"],
            test_case["expected_region"],
            test_case["expectation"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "dex_number,expected_region,expectation", get_find_region_test_data()
)
def test_find_region(dex_number, expected_region, expectation):
    with expectation:
        actual_region = regions_m.find_region(dex_number)
        assert actual_region == expected_region
