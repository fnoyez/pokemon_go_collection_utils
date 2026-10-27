import pytest

from pokemon_go_collection.sources import pogo_assets as pogo_assets_m


def get_parse_icon_file_name_test_data():
    test_cases = [
        {
            "id": "species",
            "file_name": "pm25.icon.png",
            "expected_icon": pogo_assets_m.Icon(
                file_name="pm25.icon.png",
                dex_number=25,
                form_suffix=None,
                costume=None,
                is_female=False,
                is_shiny=False,
            ),
        },
        {
            "id": "shiny-costume",
            "file_name": "pm25.cHOLIDAY_2016.s.icon.png",
            "expected_icon": pogo_assets_m.Icon(
                file_name="pm25.cHOLIDAY_2016.s.icon.png",
                dex_number=25,
                form_suffix=None,
                costume="HOLIDAY_2016",
                is_female=False,
                is_shiny=True,
            ),
        },
        {
            "id": "female-costume-on-a-form",
            "file_name": "pm710.fSMALL.cFALL_2022.g2.icon.png",
            "expected_icon": pogo_assets_m.Icon(
                file_name="pm710.fSMALL.cFALL_2022.g2.icon.png",
                dex_number=710,
                form_suffix="SMALL",
                costume="FALL_2022",
                is_female=True,
                is_shiny=False,
            ),
        },
        {
            "id": "lowercase-costume-kept-as-written",
            "file_name": "pm133.cMay_2023.icon.png",
            "expected_icon": pogo_assets_m.Icon(
                file_name="pm133.cMay_2023.icon.png",
                dex_number=133,
                form_suffix=None,
                costume="May_2023",
                is_female=False,
                is_shiny=False,
            ),
        },
        {
            "id": "portrait-is-not-an-icon",
            "file_name": "pm6.fMEGA_X.portrait.png",
            "expected_icon": None,
        },
    ]

    return [
        pytest.param(
            test_case["file_name"], test_case["expected_icon"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "file_name,expected_icon", get_parse_icon_file_name_test_data()
)
def test_parse_icon_file_name(file_name, expected_icon):
    assert pogo_assets_m.parse_icon_file_name(file_name) == expected_icon
