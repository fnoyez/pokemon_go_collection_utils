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
