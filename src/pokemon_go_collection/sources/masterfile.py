import dataclasses
import json

MASTERFILE_URL = (
    "https://raw.githubusercontent.com/WatWowMap/Masterfile-Generator/master/"
    "master-latest-raw.json"
)


@dataclasses.dataclass(frozen=True)
class GameNumbers:
    """The game's own numbers of the forms and costumes, which it sorts by."""

    # The form a species' Pokémon have when they have no other, by National
    # Pokédex number: 598, `PIKACHU_NORMAL`, for Pikachu.
    default_form_numbers: dict[int, int]
    # By the game's form name: `PIKACHU_FALL_2019`.
    form_numbers: dict[str, int]
    # By the game's costume name: `HOLIDAY_2016`.
    costume_numbers: dict[str, int]


def parse_masterfile(content):
    masterfile = json.loads(content)
    return GameNumbers(
        default_form_numbers={
            pokemon["pokedexId"]: pokemon["defaultFormId"]
            for pokemon in masterfile["pokemon"].values()
            if pokemon.get("defaultFormId")
        },
        form_numbers={
            form["proto"]: form["formId"] for form in masterfile["forms"].values()
        },
        costume_numbers={
            costume["proto"]: costume["id"]
            for costume in masterfile["costumes"].values()
        },
    )
