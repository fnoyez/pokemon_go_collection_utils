import csv
import dataclasses


@dataclasses.dataclass(frozen=True)
class Species:
    dex_number: int
    # PokeAPI's identifier, such as `mr-mime`.
    identifier: str
    name: str
    evolves_from_dex_number: int | None


def load_national_dex(file_path):
    with open(file_path, encoding="utf-8", newline="") as file:
        return [
            Species(
                dex_number=int(row["dex_number"]),
                identifier=row["identifier"],
                name=row["name"],
                evolves_from_dex_number=(
                    int(row["evolves_from_dex_number"])
                    if row["evolves_from_dex_number"]
                    else None
                ),
            )
            for row in csv.DictReader(file)
        ]
