import dataclasses
import datetime
import json
import logging
import re

logger = logging.getLogger(__name__)

LEEKDUCK_SHINY_DATA_URL = "https://leekduck.com/shiny/pms.json"

# An asset name is `pm<dex number>` followed by segments: `.f<form>`, `.c<costume>`,
# and `.g2` for a female variant.
_ASSET_NAME_REGEX = re.compile(r"^pm(\d+)((?:\.(?:f[A-Z0-9_]+|c[A-Z0-9_]+|g2))*)$")


@dataclasses.dataclass(frozen=True)
class ShinyRelease:
    dex_number: int
    # The game master form identifier without its species prefix
    # (`GALARIAN` for `FARFETCHD_GALARIAN`), or None for the species itself.
    form_suffix: str | None
    # The game's costume name (`JAN_2020_NOEVOLVE`), or None without a costume.
    costume: str | None
    release_date: datetime.date
    # The name of the Pokémon's icon files, without their extension: `pm25.fFALL_2019`.
    asset_name: str
    # LeekDuck's English label of the form or costume (`Party Hat`), or None
    # for the species itself.
    label: str | None


def parse_shiny_data(content):
    shiny_releases = []
    for item in json.loads(content):
        match = _ASSET_NAME_REGEX.match(item["aa_fn"])
        if match is None:
            logger.debug(f"Skipping LeekDuck asset name {item['aa_fn']!r}")
            continue
        segments = [segment for segment in match.group(2).split(".") if segment]
        form_suffixes = [segment[1:] for segment in segments if segment[0] == "f"]
        costumes = [segment[1:] for segment in segments if segment[0] == "c"]
        shiny_releases.append(
            ShinyRelease(
                dex_number=int(match.group(1)),
                form_suffix=form_suffixes[0] if form_suffixes else None,
                costume=costumes[0] if costumes else None,
                release_date=datetime.datetime.strptime(
                    item["released_date"], "%Y/%m/%d"
                ).date(),
                asset_name=item["aa_fn"],
                # The label breaks its lines where the checklist shows it.
                label=(
                    " ".join(item["name_suffix"].split())
                    if "name_suffix" in item
                    else None
                ),
            )
        )
    return shiny_releases
