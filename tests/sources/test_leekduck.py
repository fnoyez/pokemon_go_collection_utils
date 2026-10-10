import datetime
import textwrap

import pytest

from pokemon_go_collection.sources import leekduck as leekduck_m


def make_json_text(text):
    return textwrap.dedent(text)


def get_parse_shiny_data_test_data():
    test_cases = [
        {
            "id": "species",
            "content": make_json_text(
                """
                [
                  {"dex": 1, "family": "Bulbasaur", "released_date": "2018/03/25", "aa_fn": "pm1"}
                ]
                """
            ),
            "expected_shiny_releases": [
                leekduck_m.ShinyRelease(
                    dex_number=1,
                    form_suffix=None,
                    is_costume=False,
                    release_date=datetime.date(2018, 3, 25),
                )
            ],
        },
        {
            "id": "form",
            "content": make_json_text(
                """
                [
                  {"dex": 83, "family": "Farfetchd_G", "released_date": "2021/08/20", "aa_fn": "pm83.fGALARIAN"}
                ]
                """
            ),
            "expected_shiny_releases": [
                leekduck_m.ShinyRelease(
                    dex_number=83,
                    form_suffix="GALARIAN",
                    is_costume=False,
                    release_date=datetime.date(2021, 8, 20),
                )
            ],
        },
        {
            "id": "costumed-form-and-female",
            "content": make_json_text(
                """
                [
                  {"dex": 77, "family": "Ponyta", "released_date": "2021/07/17", "aa_fn": "pm77.fGALARIAN.cGOFEST_2021_NOEVOLVE"},
                  {"dex": 202, "family": "Wobbuffet", "released_date": "2019/10/17", "aa_fn": "pm202.g2"}
                ]
                """
            ),
            "expected_shiny_releases": [
                leekduck_m.ShinyRelease(
                    dex_number=77,
                    form_suffix="GALARIAN",
                    is_costume=True,
                    release_date=datetime.date(2021, 7, 17),
                ),
                leekduck_m.ShinyRelease(
                    dex_number=202,
                    form_suffix=None,
                    is_costume=False,
                    release_date=datetime.date(2019, 10, 17),
                ),
            ],
        },
        {
            "id": "unparseable-asset-name-skipped",
            "content": make_json_text(
                """
                [
                  {"dex": 25, "family": "Pikachu", "released_date": "2020/01/01", "aa_fn": "pm25.???"}
                ]
                """
            ),
            "expected_shiny_releases": [],
        },
    ]

    return [
        pytest.param(
            test_case["content"],
            test_case["expected_shiny_releases"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "content,expected_shiny_releases", get_parse_shiny_data_test_data()
)
def test_parse_shiny_data(content, expected_shiny_releases):
    actual_shiny_releases = leekduck_m.parse_shiny_data(content)

    assert actual_shiny_releases == expected_shiny_releases
