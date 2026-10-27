import concurrent.futures
import logging
import urllib.error

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection.sources import http as http_m
from pokemon_go_collection.sources import uicons as uicons_m

logger = logging.getLogger(__name__)

# Where PokeAPI publishes its sprites: an address of the source itself, not a
# setting, so the download functions read it directly, as they read UICONS'.
POKEAPI_SPRITE_BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
)


def download_missing_icons(
    entries, game_numbers, icons_folder_path, today, workers_nb=16
):
    """Return the icon file name of each entry, downloading the icons not cached yet.

    The shiny icon is preferred. An entry keeps its normal icon until its shiny
    is released, and only then is the shiny one looked for again. An entry
    with no icon reachable maps to None.
    """
    icons_folder_path.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers_nb) as executor:
        icon_file_names = executor.map(
            lambda entry: _ensure_entry_icon(
                entry, game_numbers, icons_folder_path, today
            ),
            entries,
        )
        return dict(zip((entry.entry_id for entry in entries), icon_file_names))


def _ensure_entry_icon(entry, game_numbers, icons_folder_path, today):
    shiny_file_name = f"{entry.entry_id}.shiny.png"
    normal_file_name = f"{entry.entry_id}.png"
    if (icons_folder_path / shiny_file_name).exists():
        return shiny_file_name
    has_normal_icon = (icons_folder_path / normal_file_name).exists()
    if has_normal_icon and not catalog_m.is_shiny_released(
        entry.shiny_release_date, today
    ):
        return normal_file_name

    for is_shiny, url in build_icon_candidate_urls(
        entry,
        game_numbers,
        uicons_m.UICONS_POKEMON_BASE_URL,
        POKEAPI_SPRITE_BASE_URL,
    ):
        if has_normal_icon and not is_shiny:
            return normal_file_name
        content = _fetch_icon(url)
        if content is not None:
            file_name = shiny_file_name if is_shiny else normal_file_name
            (icons_folder_path / file_name).write_bytes(content)
            return file_name
    logger.warning(f"No icon found for {entry.entry_id}")
    return normal_file_name if has_normal_icon else None


def build_icon_candidate_urls(entry, game_numbers, uicons_base_url, pokeapi_base_url):
    """Return (is_shiny, url) pairs to try in order: Pokémon GO icons first, shiny first."""
    # The entry's representative form comes first. An icon names a form by its
    # number, and the species' default form by none; a form the masterfile
    # does not number has no icon.
    default_form_number = game_numbers.default_form_numbers.get(entry.dex_number)
    form_numbers = []
    for form_id, suffix in zip(entry.form_ids, entry.form_suffixes):
        form_number = game_numbers.form_numbers.get(form_id)
        if suffix in (None, "NORMAL") or (
            form_number is not None and form_number == default_form_number
        ):
            form_number = None
        elif form_number is None:
            continue
        if form_number not in form_numbers:
            form_numbers.append(form_number)
    file_names = [
        (
            is_shiny,
            uicons_m.build_icon_file_name(
                entry.dex_number, form_number, None, is_shiny
            ),
        )
        for is_shiny in (True, False)
        for form_number in form_numbers
    ]
    return [
        *(
            (is_shiny, f"{uicons_base_url}/{file_name}")
            for is_shiny, file_name in file_names
        ),
        (True, f"{pokeapi_base_url}/shiny/{entry.dex_number}.png"),
        (False, f"{pokeapi_base_url}/{entry.dex_number}.png"),
    ]


def _fetch_icon(url):
    try:
        return http_m.fetch_bytes(url, timeout_duration=30)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            logger.warning(f"Fetching {url} failed: {error}")
        return None
    except urllib.error.URLError as error:
        logger.warning(f"Fetching {url} failed: {error}")
        return None


def ensure_costumed_pokemon_icons(
    costumed_pokemons, icons_folder_path, today, workers_nb=16
):
    """Return the icon file name of each costumed Pokémon, caching the icons not cached yet.

    The icon comes from UICONS. The shiny one is shown once the shiny is
    released, the normal one until then, as for an entry. A costumed Pokémon
    with no icon maps to None.
    """
    icons_folder_path.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers_nb) as executor:
        icon_file_names = executor.map(
            lambda costumed_pokemon: _ensure_costumed_pokemon_icon(
                costumed_pokemon, icons_folder_path, today
            ),
            costumed_pokemons,
        )
        return dict(
            zip(
                (
                    costumed_pokemon.costumed_pokemon_id
                    for costumed_pokemon in costumed_pokemons
                ),
                icon_file_names,
            )
        )


def _ensure_costumed_pokemon_icon(costumed_pokemon, icons_folder_path, today):
    is_shiny_shown = catalog_m.is_shiny_released(
        costumed_pokemon.shiny_release_date, today
    )
    for is_shiny in (True, False) if is_shiny_shown else (False,):
        suffix = ".shiny" if is_shiny else ""
        file_name = f"{costumed_pokemon.costumed_pokemon_id}{suffix}.png"
        if (icons_folder_path / file_name).exists():
            return file_name
        uicons_file_name = (
            costumed_pokemon.icon_file_names[int(is_shiny)]
            if costumed_pokemon.icon_file_names is not None
            else None
        )
        if uicons_file_name is not None:
            content = _fetch_icon(
                f"{uicons_m.UICONS_POKEMON_BASE_URL}/{uicons_file_name}"
            )
            if content is not None:
                (icons_folder_path / file_name).write_bytes(content)
                return file_name
    logger.warning(f"No icon found for {costumed_pokemon.costumed_pokemon_id}")
    return None
