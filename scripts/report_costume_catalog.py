"""Build the costumed Pokémon from their sources, and report how the sources cover them.

Pulls the game master and pogo_assets repositories, fetches LeekDuck's shiny
data, Bulbapedia's list of event Pokémon and the masterfile's numbers, prints the report and writes the
costumed Pokémon to a CSV file:

    uv run python scripts/report_costume_catalog.py --output-file-path costumed_pokemons.csv
"""

import argparse
import collections
import csv
import datetime
import logging
import pathlib

from pokemon_go_collection import config as config_m
from pokemon_go_collection import costumes as costumes_m
from pokemon_go_collection import logging_setup as logging_setup_m
from pokemon_go_collection.services import refresh as refresh_m
from pokemon_go_collection.sources import bulbapedia as bulbapedia_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import git_repository as git_repository_m
from pokemon_go_collection.sources import leekduck as leekduck_m
from pokemon_go_collection.sources import masterfile as masterfile_m
from pokemon_go_collection.sources import national_dex as national_dex_m
from pokemon_go_collection.sources import overrides as overrides_m
from pokemon_go_collection.sources import pogo_assets as pogo_assets_m

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Report how the sources cover the costumed Pokémon",
        allow_abbrev=False,
    )
    parser.add_argument("--output-file-path", required=True)
    args = parser.parse_args()

    logging_setup_m.setup_logging(logging_level=logging.INFO)
    cfg = config_m.load_config(
        config_m.DEFAULT_APP_HOME_FOLDER_PATH,
        config_m.DEFAULT_BACKUP_FOLDER_PATH,
        config_m.REPOSITORY_FOLDER_PATH,
    )
    warnings = []
    for repository_folder_path in (
        cfg.game_master_repository_folder_path,
        cfg.pogo_assets_repository_folder_path,
    ):
        pull_error_message = git_repository_m.pull_repository(repository_folder_path)
        if pull_error_message is not None:
            warnings.append(pull_error_message)
    leekduck_content = refresh_m.fetch_source_snapshot(
        leekduck_m.LEEKDUCK_SHINY_DATA_URL,
        cfg.sources_folder_path / "leekduck_shiny_data.json",
        warnings,
    )
    bulbapedia_content = refresh_m.fetch_source_snapshot(
        bulbapedia_m.EVENT_POKEMON_URL,
        cfg.sources_folder_path / "bulbapedia_event_pokemon.wiki",
        warnings,
    )
    masterfile_content = refresh_m.fetch_source_snapshot(
        masterfile_m.MASTERFILE_URL,
        cfg.sources_folder_path / "masterfile.json",
        warnings,
    )
    for warning in warnings:
        logger.warning(warning)

    costume_catalog = costumes_m.build_costume_catalog(
        national_dex_m.load_national_dex(cfg.data_folder_path / "national_dex.csv"),
        game_master_m.load_game_master(cfg.game_master_repository_folder_path),
        overrides_m.load_form_overrides(cfg.data_folder_path / "form_overrides.csv"),
        pogo_assets_m.list_icons(cfg.pogo_assets_repository_folder_path),
        leekduck_m.parse_shiny_data(leekduck_content),
        bulbapedia_m.parse_event_pokemon(bulbapedia_content.decode("utf-8")),
        overrides_m.load_costume_matches(cfg.data_folder_path / "costume_matches.csv"),
        masterfile_m.parse_masterfile(masterfile_content),
    )
    write_costumed_pokemons(
        pathlib.Path(args.output_file_path), costume_catalog.costumed_pokemons
    )
    print(build_report(costume_catalog, datetime.date.today()))


def write_costumed_pokemons(file_path, costumed_pokemons):
    with open(file_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(
            [
                "costumed_pokemon_id",
                "name",
                "release_date",
                "shiny_release_date",
                "pogo_assets_icon",
                "leekduck_asset_name",
                "bulbapedia_codes",
                "game_order",
            ]
        )
        for costumed_pokemon in costumed_pokemons:
            writer.writerow(
                [
                    costumed_pokemon.costumed_pokemon_id,
                    costumed_pokemon.name,
                    costumed_pokemon.release_date or "",
                    costumed_pokemon.shiny_release_date or "",
                    (costumed_pokemon.pogo_assets_icon_file_names or ("",))[0],
                    costumed_pokemon.leekduck_asset_name or "",
                    " ".join(costumed_pokemon.bulbapedia_codes),
                    " ".join(str(n) for n in costumed_pokemon.game_order or ()),
                ]
            )


def build_report(costume_catalog, today):
    costumed_pokemons = costume_catalog.costumed_pokemons
    source_coverage = collections.Counter(
        " + ".join(find_sources(costumed_pokemon))
        for costumed_pokemon in costumed_pokemons
    )
    lines = [
        f"{len(costumed_pokemons)} costumed Pokémon",
        f"- released: {count(costumed_pokemons, lambda c: c.release_date is not None and c.release_date <= today)}",
        f"- announced: {count(costumed_pokemons, lambda c: c.release_date is not None and c.release_date > today)}",
        f"- in no Bulbapedia event: {count(costumed_pokemons, lambda c: c.release_date is None)}",
        f"- shiny released: {count(costumed_pokemons, lambda c: c.shiny_release_date is not None and c.shiny_release_date <= today)}",
        f"- with a pogo_assets icon: {count(costumed_pokemons, lambda c: c.pogo_assets_icon_file_names is not None)}",
        f"- with a LeekDuck icon only: {count(costumed_pokemons, lambda c: c.pogo_assets_icon_file_names is None and c.leekduck_asset_name is not None)}",
        f"- with no icon: {count(costumed_pokemons, lambda c: c.pogo_assets_icon_file_names is None and c.leekduck_asset_name is None)}",
        f"- unnumbered by the masterfile: {count(costumed_pokemons, lambda c: c.game_order is None)}",
        "",
        "Sources holding each costumed Pokémon:",
        *(f"- {sources}: {nb}" for sources, nb in source_coverage.most_common()),
        "",
        "Named by Bulbapedia only, the game name being in no source:",
        *(
            f"- {c.costumed_pokemon_id}: {c.name}, released {c.release_date}"
            for c in costumed_pokemons
            if c.key.bulbapedia_code is not None
        ),
        "",
        "Unnumbered by the masterfile, ordered by release date:",
        *(
            f"- {c.costumed_pokemon_id}: {c.name}"
            for c in costumed_pokemons
            if c.game_order is None
        ),
        "",
        "In no Bulbapedia event, unreleasable:",
        *(
            f"- {c.costumed_pokemon_id}: {c.name} ({' + '.join(find_sources(c))})"
            for c in costumed_pokemons
            if costumes_m.is_unreleasable(c.release_date, c.costume_year, today)
        ),
        "",
        "In no Bulbapedia event, not released yet:",
        *(
            f"- {c.costumed_pokemon_id}: {c.name} ({' + '.join(find_sources(c))})"
            for c in costumed_pokemons
            if c.release_date is None
            and not costumes_m.is_unreleasable(c.release_date, c.costume_year, today)
        ),
        "",
        "Bulbapedia sprites data/costume_matches.csv has no line for:",
        *(
            f"- {sprite.dex_number} {sprite.code!r} ({sprite.name})"
            for sprite in costume_catalog.unmatched_sprites
        ),
        "",
        "Lines of data/costume_matches.csv standing for no Bulbapedia sprite:",
        *(
            f"- {match.dex_number} {match.bulbapedia_code!r}"
            for match in costume_catalog.unused_matches
        ),
    ]
    return "\n".join(lines)


def find_sources(costumed_pokemon):
    sources = []
    if costumed_pokemon.pogo_assets_icon_file_names is not None:
        sources.append("pogo_assets")
    if costumed_pokemon.leekduck_asset_name is not None:
        sources.append("LeekDuck")
    if costumed_pokemon.bulbapedia_codes:
        sources.append("Bulbapedia")
    return sources


def count(costumed_pokemons, predicate):
    return sum(
        1 for costumed_pokemon in costumed_pokemons if predicate(costumed_pokemon)
    )


if __name__ == "__main__":
    main()
