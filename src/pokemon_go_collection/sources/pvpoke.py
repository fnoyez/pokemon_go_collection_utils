import dataclasses
import json
import re

PVPOKE_GAME_MASTER_URL = (
    "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster.json"
)

# Shadows, Megas and Primals are states of a Pokémon, not Pokémon of their own.
_NON_POKEMON_SPECIES_ID_REGEX = re.compile(r"_(shadow|mega|mega_x|mega_y|primal)$")


@dataclasses.dataclass(frozen=True)
class PvpokeSpecies:
    dex_number: int
    # PvPoke's identifier, such as `farfetchd_galarian`.
    species_id: str
    is_released: bool


def parse_pvpoke_game_master(content):
    return [
        PvpokeSpecies(
            dex_number=pokemon["dex"],
            species_id=pokemon["speciesId"],
            is_released=pokemon.get("released", False),
        )
        for pokemon in json.loads(content)["pokemon"]
        if not _NON_POKEMON_SPECIES_ID_REGEX.search(pokemon["speciesId"])
    ]
