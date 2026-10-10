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
    is_costume: bool
    release_date: datetime.date


def parse_shiny_data(content):
    shiny_releases = []
    for item in json.loads(content):
        match = _ASSET_NAME_REGEX.match(item["aa_fn"])
        if match is None:
            logger.debug(f"Skipping LeekDuck asset name {item['aa_fn']!r}")
            continue
        segments = [segment for segment in match.group(2).split(".") if segment]
        form_suffixes = [segment[1:] for segment in segments if segment[0] == "f"]
        shiny_releases.append(
            ShinyRelease(
                dex_number=int(match.group(1)),
                form_suffix=form_suffixes[0] if form_suffixes else None,
                is_costume=any(segment[0] == "c" for segment in segments),
                release_date=datetime.datetime.strptime(
                    item["released_date"], "%Y/%m/%d"
                ).date(),
            )
        )
    return shiny_releases
