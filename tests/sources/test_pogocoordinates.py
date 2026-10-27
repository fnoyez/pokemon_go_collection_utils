import datetime
import json
import textwrap

from pokemon_go_collection.sources import pogocoordinates as pogocoordinates_m

SEARCH_RESPONSE_TEXT = textwrap.dedent(
    """
    {
      "results": [
        {
          "encounter_id": "-3428825051598173534",
          "pokemon_id": 570,
          "pokemon_name": "Zorua",
          "form": null,
          "costume_id": null,
          "costume": null,
          "cp": 676,
          "level": 21.0,
          "location": "Richfield, Minnesota, United States",
          "raw_iv": "15/15/15",
          "iv_percent": 100,
          "despawn_at": "2026-10-10T15:35:48-05:00",
          "reveal_code": "ozR_gLgk/vn7",
          "shiny": true
        }
      ],
      "tier": "logged_in",
      "cap": 10,
      "total_matches": 0
    }
    """
)


def test_parse_search_results():
    spawns = pogocoordinates_m.parse_search_results(json.loads(SEARCH_RESPONSE_TEXT))

    assert spawns == [
        pogocoordinates_m.Spawn(
            encounter_id="-3428825051598173534",
            pokemon_id=570,
            pokemon_name="Zorua",
            form=None,
            cp=676,
            level=21.0,
            raw_iv="15/15/15",
            iv_percent=100,
            location="Richfield, Minnesota, United States",
            despawn_time=datetime.datetime(
                2026, 10, 10, 20, 35, 48, tzinfo=datetime.timezone.utc
            ),
            reveal_code="ozR_gLgk/vn7",
        )
    ]


def test_build_reveal_url_quotes_the_code():
    assert pogocoordinates_m.build_reveal_url("ozR_gLgk/vn7") == (
        "https://coordinates-api.pokemongopro.com/reveal/ozR_gLgk%2Fvn7"
    )


def test_parse_form_catalog_reads_the_costumes_spawning_now():
    content = json.loads(
        textwrap.dedent(
            """
            [
              {"pokemon_id": 37, "form_id": 55, "form_suffix": null, "form_name": null, "species_name": "Vulpix", "costume": true, "costume_id": 57, "costume_name": "FALL_2022", "live": true},
              {"pokemon_id": 25, "form_id": 894, "form_suffix": "FALL_2019", "form_name": "PIKACHU_FALL_2019", "species_name": "Pikachu", "costume": true, "live": false},
              {"pokemon_id": 19, "form_id": 46, "form_suffix": "ALOLA", "form_name": "RATTATA_ALOLA", "species_name": "Rattata"}
            ]
            """
        )
    )

    assert pogocoordinates_m.parse_form_catalog(content) == [
        pogocoordinates_m.ServiceForm(
            pokemon_id=37,
            form_id=55,
            form_name=None,
            form_suffix=None,
            is_costume=True,
            costume_id=57,
            costume_name="FALL_2022",
            is_live=True,
        ),
        pogocoordinates_m.ServiceForm(
            pokemon_id=25,
            form_id=894,
            form_name="PIKACHU_FALL_2019",
            form_suffix="FALL_2019",
            is_costume=True,
            costume_id=None,
            costume_name=None,
            is_live=False,
        ),
        pogocoordinates_m.ServiceForm(
            pokemon_id=19,
            form_id=46,
            form_name="RATTATA_ALOLA",
            form_suffix="ALOLA",
            is_costume=False,
            costume_id=None,
            costume_name=None,
            is_live=False,
        ),
    ]
