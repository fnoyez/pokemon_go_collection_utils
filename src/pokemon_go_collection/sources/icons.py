import concurrent.futures
import logging
import shutil
import urllib.error

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection.sources import http as http_m

logger = logging.getLogger(__name__)

# Where the icon sources publish their files: addresses of the sources
# themselves, not settings, so the download functions read them directly.
POGO_ASSETS_ICON_BASE_URL = (
    "https://raw.githubusercontent.com/PokeMiners/pogo_assets/master/Images/Pokemon/"
    "Addressable%20Assets"
)
POKEAPI_SPRITE_BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
)
LEEKDUCK_ICON_BASE_URL = "https://cdn.leekduck.com/assets/img/pokemon_icons"


def download_missing_icons(entries, icons_folder_path, today, workers_nb=16):
    """Return the icon file name of each entry, downloading the icons not cached yet.

    The shiny icon is preferred. An entry keeps its normal icon until its shiny
    is released, and only then is the shiny one looked for again. An entry
    with no icon reachable maps to None.
    """
    icons_folder_path.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers_nb) as executor:
        icon_file_names = executor.map(
            lambda entry: _ensure_entry_icon(entry, icons_folder_path, today), entries
        )
        return dict(zip((entry.entry_id for entry in entries), icon_file_names))


def _ensure_entry_icon(entry, icons_folder_path, today):
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
        entry, POGO_ASSETS_ICON_BASE_URL, POKEAPI_SPRITE_BASE_URL
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


def build_icon_candidate_urls(entry, pogo_assets_base_url, pokeapi_base_url):
    """Return (is_shiny, url) pairs to try in order: Pokémon GO icons first, shiny first."""
    # The entry's representative form comes first. An asset names a form by
    # its suffix or by its whole identifier (`pm201.fUNOWN_A`), and the
    # species' usual form by no suffix at all.
    asset_names = []
    for form_id, suffix in zip(entry.form_ids, entry.form_suffixes):
        if suffix in (None, "NORMAL"):
            form_asset_names = [f"pm{entry.dex_number}"]
        else:
            form_asset_names = [
                f"pm{entry.dex_number}.f{suffix}",
                f"pm{entry.dex_number}.f{form_id}",
            ]
        asset_names.extend(name for name in form_asset_names if name not in asset_names)
    return [
        *((True, f"{pogo_assets_base_url}/{name}.s.icon.png") for name in asset_names),
        *((False, f"{pogo_assets_base_url}/{name}.icon.png") for name in asset_names),
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
    costumed_pokemons,
    pogo_assets_icons_folder_path,
    icons_folder_path,
    today,
    workers_nb=16,
):
    """Return the icon file name of each costumed Pokémon, caching the icons not cached yet.

    The icon comes from the pogo_assets clone, or else from LeekDuck. The
    shiny one is shown once the shiny is released, the normal one until then,
    as for an entry. A costumed Pokémon with no icon maps to None.
    """
    icons_folder_path.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers_nb) as executor:
        icon_file_names = executor.map(
            lambda costumed_pokemon: _ensure_costumed_pokemon_icon(
                costumed_pokemon,
                pogo_assets_icons_folder_path,
                icons_folder_path,
                today,
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


def _ensure_costumed_pokemon_icon(
    costumed_pokemon, pogo_assets_icons_folder_path, icons_folder_path, today
):
    is_shiny_shown = catalog_m.is_shiny_released(
        costumed_pokemon.shiny_release_date, today
    )
    for is_shiny in (True, False) if is_shiny_shown else (False,):
        suffix = ".shiny" if is_shiny else ""
        file_name = f"{costumed_pokemon.costumed_pokemon_id}{suffix}.png"
        icon_file_path = icons_folder_path / file_name
        if icon_file_path.exists():
            return file_name
        pogo_assets_file_names = costumed_pokemon.pogo_assets_icon_file_names
        pogo_assets_file_name = (
            pogo_assets_file_names[int(is_shiny)]
            if pogo_assets_file_names is not None
            else None
        )
        if pogo_assets_file_name is not None:
            shutil.copyfile(
                pogo_assets_icons_folder_path / pogo_assets_file_name, icon_file_path
            )
            return file_name
        if costumed_pokemon.leekduck_asset_name is not None:
            content = _fetch_icon(
                f"{LEEKDUCK_ICON_BASE_URL}/{costumed_pokemon.leekduck_asset_name}"
                f"{'.s' if is_shiny else ''}.icon.png"
            )
            if content is not None:
                icon_file_path.write_bytes(content)
                return file_name
    logger.warning(f"No icon found for {costumed_pokemon.costumed_pokemon_id}")
    return None
