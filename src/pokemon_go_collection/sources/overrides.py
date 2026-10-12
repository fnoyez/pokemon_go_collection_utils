import csv
import dataclasses
import enum

from pokemon_go_collection import regions as regions_m


class FormDecision(enum.Enum):
    # The form is the same Pokémon as another form: its species' base form, or
    # the target form the override names.
    MERGE = "merge"
    # The form is a Pokémon of its own.
    DISTINCT = "distinct"
    # The form is its species' base form, standing for the species' base entry.
    BASE = "base"


@dataclasses.dataclass(frozen=True)
class FormOverride:
    form_id: str
    decision: FormDecision
    # The form a merged form joins, or None for the species' base form.
    target_form_id: str | None
    # The region whose variant block the form's line goes to, for a distinct form.
    variant_region: regions_m.Region | None


def load_form_overrides(file_path):
    """Return the overrides by form identifier, in the file's order.

    That order is the display order of the entries of a species whose base form
    an override chooses.
    """
    with open(file_path, encoding="utf-8", newline="") as file:
        return {
            row["form_id"]: FormOverride(
                form_id=row["form_id"],
                decision=FormDecision(row["decision"]),
                target_form_id=row["target_form_id"] or None,
                variant_region=(
                    regions_m.Region(row["variant_region"])
                    if row["variant_region"]
                    else None
                ),
            )
            for row in csv.DictReader(file)
        }


def load_release_override_entry_ids(file_path):
    with open(file_path, encoding="utf-8", newline="") as file:
        return frozenset(row["entry_id"] for row in csv.DictReader(file))
