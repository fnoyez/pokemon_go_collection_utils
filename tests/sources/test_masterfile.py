import textwrap

from pokemon_go_collection.sources import masterfile as masterfile_m

MASTERFILE_CONTENT = textwrap.dedent(
    """
    {
      "pokemon": {
        "25": {"pokemonName": "Pikachu", "pokedexId": 25, "defaultFormId": 598},
        "1025": {"pokemonName": "Pecharunt", "pokedexId": 1025}
      },
      "forms": {
        "0": {"formName": "Unset", "proto": "FORM_UNSET", "formId": 0},
        "598": {"formName": "Normal", "proto": "PIKACHU_NORMAL", "formId": 598},
        "894": {"formName": "Fall 2019", "proto": "PIKACHU_FALL_2019", "formId": 894}
      },
      "costumes": {
        "0": {"id": 0, "name": "Unset", "proto": "UNSET", "noEvolve": false},
        "1": {"id": 1, "name": "Holiday 2016", "proto": "HOLIDAY_2016", "noEvolve": false}
      }
    }
    """
)


def test_parse_masterfile():
    game_numbers = masterfile_m.parse_masterfile(MASTERFILE_CONTENT)

    assert game_numbers == masterfile_m.GameNumbers(
        default_form_numbers={25: 598},
        form_numbers={"FORM_UNSET": 0, "PIKACHU_NORMAL": 598, "PIKACHU_FALL_2019": 894},
        costume_numbers={"UNSET": 0, "HOLIDAY_2016": 1},
    )
