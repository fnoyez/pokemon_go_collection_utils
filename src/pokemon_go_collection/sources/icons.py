import concurrent.futures
import logging
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
