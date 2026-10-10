"""Write data/national_dex.csv from PokeAPI's data.

Run once, and again when a main series game introduces new species:

    uv run python scripts/seed_national_dex.py
"""

import argparse
import csv
import io
import logging
import pathlib

from pokemon_go_collection import logging_setup as logging_setup_m
from pokemon_go_collection.sources import http as http_m

logger = logging.getLogger(__name__)

POKEAPI_CSV_BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"
)
ENGLISH_LANGUAGE_ID = "9"
NATIONAL_DEX_FILE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "national_dex.csv"
)


def main():
    parser = argparse.ArgumentParser(
        description="Write the National Pokédex seed from PokeAPI's data",
        allow_abbrev=False,
    )
    parser.add_argument("--output-file-path", default=str(NATIONAL_DEX_FILE_PATH))
    args = parser.parse_args()

    logging_setup_m.setup_logging(logging_level=logging.INFO)
    species_rows = fetch_pokeapi_csv(POKEAPI_CSV_BASE_URL, "pokemon_species")
    name_rows = fetch_pokeapi_csv(POKEAPI_CSV_BASE_URL, "pokemon_species_names")
    rows = build_national_dex_rows(species_rows, name_rows, ENGLISH_LANGUAGE_ID)
    write_national_dex(pathlib.Path(args.output_file_path), rows)
    logger.info(f"{len(rows)} species written to {args.output_file_path}")


def fetch_pokeapi_csv(base_url, table_name):
    content = http_m.fetch_bytes(f"{base_url}/{table_name}.csv").decode("utf-8")
    return list(csv.DictReader(io.StringIO(content)))


def build_national_dex_rows(species_rows, name_rows, language_id):
    names = {
        row["pokemon_species_id"]: row["name"]
        for row in name_rows
        if row["local_language_id"] == language_id
    }
    rows = [
        {
            "dex_number": int(row["id"]),
            "identifier": row["identifier"],
            "name": names[row["id"]],
            "evolves_from_dex_number": row["evolves_from_species_id"],
            "is_baby": row["is_baby"],
        }
        for row in species_rows
    ]
    return sorted(rows, key=lambda row: row["dex_number"])


def write_national_dex(file_path, rows):
    with open(file_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "dex_number",
                "identifier",
                "name",
                "evolves_from_dex_number",
                "is_baby",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
