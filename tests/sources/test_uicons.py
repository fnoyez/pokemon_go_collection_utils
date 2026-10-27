import json

import pytest

from pokemon_go_collection.sources import masterfile as masterfile_m
from pokemon_go_collection.sources import uicons as uicons_m

GAME_NUMBERS = masterfile_m.GameNumbers(
    default_form_numbers={25: 598, 710: 2641},
    form_numbers={
        "PIKACHU_NORMAL": 598,
        "PIKACHU_FALL_2019": 894,
        "PUMPKABOO_SMALL": 2641,
        "PUMPKABOO_AVERAGE": 2642,
    },
    costume_numbers={"HOLIDAY_2016": 1, "FALL_2022": 57},
)


def get_parse_index_test_data():
    test_cases = [
        {
            "id": "species-default-form",
            "file_name": "25.png",
            "expected_icons": [
                uicons_m.Icon(
                    file_name="25.png",
                    dex_number=25,
                    form_id="PIKACHU_NORMAL",
                    costume=None,
                    is_female=False,
                    is_shiny=False,
                )
            ],
        },
        {
            "id": "costume-on-the-default-form",
            "file_name": "710_c57_s.png",
            "expected_icons": [
                uicons_m.Icon(
                    file_name="710_c57_s.png",
                    dex_number=710,
                    form_id="PUMPKABOO_SMALL",
                    costume="FALL_2022",
                    is_female=False,
                    is_shiny=True,
                )
            ],
        },
        {
            "id": "costume-on-a-form",
            "file_name": "710_f2642_c57.png",
            "expected_icons": [
                uicons_m.Icon(
                    file_name="710_f2642_c57.png",
                    dex_number=710,
                    form_id="PUMPKABOO_AVERAGE",
                    costume="FALL_2022",
                    is_female=False,
                    is_shiny=False,
                )
            ],
        },
        {
            "id": "female-costume",
            "file_name": "25_c1_g2_s.png",
            "expected_icons": [
                uicons_m.Icon(
                    file_name="25_c1_g2_s.png",
                    dex_number=25,
                    form_id="PIKACHU_NORMAL",
                    costume="HOLIDAY_2016",
                    is_female=True,
                    is_shiny=True,
                )
            ],
        },
        {
            "id": "species-without-forms",
            "file_name": "41.png",
            "expected_icons": [
                uicons_m.Icon(
                    file_name="41.png",
                    dex_number=41,
                    form_id=None,
                    costume=None,
                    is_female=False,
                    is_shiny=False,
                )
            ],
        },
        {
            "id": "shadow-icon-left-out",
            "file_name": "25_c1_a1.png",
            "expected_icons": [],
        },
        {
            "id": "unnumbered-form-left-out",
            "file_name": "25_f3379.png",
            "expected_icons": [],
        },
        {
            "id": "unnumbered-costume-left-out",
            "file_name": "25_c99.png",
            "expected_icons": [],
        },
    ]

    return [
        pytest.param(
            test_case["file_name"],
            test_case["expected_icons"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize("file_name,expected_icons", get_parse_index_test_data())
def test_parse_index(file_name, expected_icons):
    content = json.dumps({"pokemon": [file_name], "raid": ["egg.png"]})

    actual_icons = uicons_m.parse_index(content, GAME_NUMBERS)

    assert actual_icons == expected_icons


def get_build_icon_file_name_test_data():
    test_cases = [
        {
            "id": "default-form",
            "dex_number": 25,
            "form_number": None,
            "costume_number": None,
            "is_shiny": False,
            "expected_output": "25.png",
        },
        {
            "id": "shiny-costume-on-a-form",
            "dex_number": 710,
            "form_number": 2642,
            "costume_number": 57,
            "is_shiny": True,
            "expected_output": "710_f2642_c57_s.png",
        },
    ]

    return [
        pytest.param(
            test_case["dex_number"],
            test_case["form_number"],
            test_case["costume_number"],
            test_case["is_shiny"],
            test_case["expected_output"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "dex_number,form_number,costume_number,is_shiny,expected_output",
    get_build_icon_file_name_test_data(),
)
def test_build_icon_file_name(
    dex_number, form_number, costume_number, is_shiny, expected_output
):
    actual_output = uicons_m.build_icon_file_name(
        dex_number, form_number, costume_number, is_shiny
    )
    assert actual_output == expected_output
