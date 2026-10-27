import dataclasses
import datetime
import enum
import json
import logging
import re

logger = logging.getLogger(__name__)

_POKEMON_TEMPLATE_ID_REGEX = re.compile(r"^V(\d{4})_POKEMON_")


class PokemonClass(enum.Enum):
    """The special classes the game master puts some Pokémon in; most are in none."""

    LEGENDARY = "legendary"
    MYTHICAL = "mythical"
    ULTRA_BEAST = "ultra_beast"


# How the game master names each class.
_GAME_MASTER_POKEMON_CLASSES = {
    "POKEMON_CLASS_LEGENDARY": PokemonClass.LEGENDARY,
    "POKEMON_CLASS_MYTHIC": PokemonClass.MYTHICAL,
    "POKEMON_CLASS_ULTRA_BEAST": PokemonClass.ULTRA_BEAST,
}


@dataclasses.dataclass(frozen=True)
class TemporaryEvolution:
    """A Mega or Primal evolution of a form."""

    # The game master's identifier without its `TEMP_EVOLUTION_` prefix: MEGA,
    # MEGA_X, MEGA_Y, PRIMAL.
    temporary_evolution_id: str
    stats: tuple[int, int, int]


@dataclasses.dataclass(frozen=True)
class PokemonForm:
    """The game master's settings for one species, or one form of a species."""

    form_id: str
    species_id: str
    dex_number: int
    stats: tuple[int, int, int]
    types: tuple[str, ...]
    # (species, form) pairs; the form is None when the evolution names none.
    evolutions: tuple[tuple[str, str | None], ...]
    pokemon_class: PokemonClass | None
    # In game master order.
    temporary_evolutions: tuple[TemporaryEvolution, ...]
    # The `_NOEVOLVE` costumes the form may evolve while wearing, which keep
    # it from evolving otherwise.
    noevolve_costumes_allowed: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class GameMaster:
    # Ordered by National Pokédex number, then with each species' formless
    # settings first and its forms in the order the game master lists them.
    forms: tuple[PokemonForm, ...]
    costume_form_ids: frozenset[str]
    # The CP multiplier of each whole level, level 1 first.
    cp_multipliers: tuple[float, ...]
    # When the game master was published.
    timestamp: datetime.datetime


def load_game_master(repository_folder_path):
    latest_folder_path = repository_folder_path / "latest"
    with open(latest_folder_path / "latest.json", encoding="utf-8") as file:
        templates = json.load(file)
    # The timestamp file holds milliseconds since the epoch.
    timestamp = datetime.datetime.fromtimestamp(
        int((latest_folder_path / "timestamp.txt").read_text()) / 1000,
        tz=datetime.timezone.utc,
    )
    return parse_game_master(templates, timestamp)


def parse_game_master(templates, timestamp):
    form_orders = {}
    costume_form_ids = set()
    cp_multipliers = None
    for template in templates:
        if "playerLevel" in template["data"]:
            cp_multipliers = tuple(template["data"]["playerLevel"]["cpMultiplier"])
        form_settings = template["data"].get("formSettings")
        if form_settings is None:
            continue
        for form_index, form in enumerate(form_settings.get("forms", [])):
            form_orders[form["form"]] = form_index
            if form.get("isCostume"):
                costume_form_ids.add(form["form"])

    forms = []
    for template in templates:
        match = _POKEMON_TEMPLATE_ID_REGEX.match(template["templateId"])
        pokemon_settings = template["data"].get("pokemonSettings")
        if match is None or pokemon_settings is None:
            continue
        forms.append(_build_pokemon_form(int(match.group(1)), pokemon_settings))

    def sort_key(form):
        is_formless = form.form_id == form.species_id
        return (
            form.dex_number,
            not is_formless,
            form_orders.get(form.form_id, len(form_orders)),
            form.form_id,
        )

    return GameMaster(
        forms=tuple(sorted(forms, key=sort_key)),
        costume_form_ids=frozenset(costume_form_ids),
        cp_multipliers=cp_multipliers,
        timestamp=timestamp,
    )


def _build_pokemon_form(dex_number, pokemon_settings):
    types = [pokemon_settings["type"]]
    if "type2" in pokemon_settings:
        types.append(pokemon_settings["type2"])
    # A branch without `evolution` is a temporary evolution (a Mega), which is
    # not a Pokémon of its own.
    evolutions = tuple(
        (branch["evolution"], branch.get("form"))
        for branch in pokemon_settings.get("evolutionBranch", [])
        if "evolution" in branch
    )
    # The class names are the game master's own vocabulary, read here directly
    # rather than passed in.
    pokemon_class = (
        _GAME_MASTER_POKEMON_CLASSES[pokemon_settings["pokemonClass"]]
        if "pokemonClass" in pokemon_settings
        else None
    )
    # An override without stats only adjusts the camera or a model of the form.
    temporary_evolutions = tuple(
        TemporaryEvolution(
            override["tempEvoId"].removeprefix("TEMP_EVOLUTION_"),
            _read_stats(override["stats"]),
        )
        for override in pokemon_settings.get("tempEvoOverrides", [])
        if "stats" in override
    )
    return PokemonForm(
        form_id=pokemon_settings.get("form", pokemon_settings["pokemonId"]),
        species_id=pokemon_settings["pokemonId"],
        dex_number=dex_number,
        stats=_read_stats(pokemon_settings["stats"]),
        types=tuple(types),
        evolutions=evolutions,
        pokemon_class=pokemon_class,
        temporary_evolutions=temporary_evolutions,
        noevolve_costumes_allowed=tuple(
            pokemon_settings.get("allowNoevolveEvolution", [])
        ),
    )


def _read_stats(stats):
    return (stats["baseAttack"], stats["baseDefense"], stats["baseStamina"])
