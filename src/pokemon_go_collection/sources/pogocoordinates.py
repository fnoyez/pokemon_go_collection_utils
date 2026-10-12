"""The pogocoordinates.com API, as docs/spawn_watch.md describes it."""

import dataclasses
import datetime
import json
import urllib.error
import urllib.parse

from pokemon_go_collection.sources import http as http_m

# The service's own address, not a setting: the functions below read it directly.
API_BASE_URL = "https://coordinates-api.pokemongopro.com"
SITE_URL = "https://pogocoordinates.com"


class PogocoordinatesAuthError(Exception):
    """The service refused the login token, or the account has no linked trainer."""


class PogocoordinatesRateLimitError(Exception):
    def __init__(self, retry_after_duration):
        super().__init__(f"Rate limited; retry after {retry_after_duration}")
        self.retry_after_duration = retry_after_duration


@dataclasses.dataclass(frozen=True)
class ServiceForm:
    pokemon_id: int
    form_id: int
    # The game master form name, such as `TAUROS_PALDEA_AQUA`; None for a few
    # costumes.
    form_name: str | None
    # The form name without its species prefix; None for an ordinary form.
    form_suffix: str | None
    is_costume: bool


@dataclasses.dataclass(frozen=True)
class Spawn:
    encounter_id: str
    pokemon_id: int
    pokemon_name: str
    # As the service gives it; None for an ordinary form.
    form: str | None
    cp: int
    level: float
    raw_iv: str
    iv_percent: float
    location: str
    despawn_time: datetime.datetime
    reveal_code: str


def fetch_form_catalog_content():
    """Return the service's form catalog as it sends it, for `parse_form_catalog`."""
    return http_m.fetch_json(f"{API_BASE_URL}/pokemon/catalog?costumes=true")


def parse_form_catalog(content):
    return [
        ServiceForm(
            pokemon_id=row["pokemon_id"],
            form_id=row["form_id"],
            form_name=row["form_name"],
            form_suffix=row["form_suffix"],
            is_costume=bool(row.get("costume")),
        )
        for row in content
    ]


def search_spawns(token, spec):
    """Return the spawns matching the search `spec`, searched with the account of `token`."""
    try:
        content = http_m.fetch_json(
            f"{API_BASE_URL}/search",
            body=spec,
            headers={"Authorization": f"Bearer {token}"},
        )
    except urllib.error.HTTPError as error:
        raise _translate_http_error(error) from error
    return parse_search_results(content)


def _translate_http_error(error):
    """Return the exception standing for an error response of the service."""
    try:
        detail = json.loads(error.read() or b"null")
    except json.JSONDecodeError:
        detail = None
    inner_detail = detail.get("detail") if isinstance(detail, dict) else None
    if error.code == 401:
        return PogocoordinatesAuthError("The service refused the login token")
    if error.code == 403 and isinstance(inner_detail, dict):
        return PogocoordinatesAuthError(inner_detail.get("message", "Forbidden"))
    if error.code == 429:
        retry_after = (
            inner_detail.get("retry_after") if isinstance(inner_detail, dict) else None
        )
        # Without an answer, the service's own pages wait an hour.
        return PogocoordinatesRateLimitError(
            datetime.timedelta(seconds=retry_after or 3600)
        )
    return error


def parse_search_results(content):
    return [
        Spawn(
            encounter_id=row["encounter_id"],
            pokemon_id=row["pokemon_id"],
            pokemon_name=row["pokemon_name"],
            form=row["form"],
            cp=row["cp"],
            level=row["level"],
            raw_iv=row["raw_iv"],
            iv_percent=row["iv_percent"],
            location=row["location"],
            despawn_time=datetime.datetime.fromisoformat(row["despawn_at"]),
            reveal_code=row["reveal_code"],
        )
        for row in content["results"]
    ]


def fetch_account(token):
    """Return the account of `token`, as the service describes it."""
    try:
        return http_m.fetch_json(
            f"{API_BASE_URL}/users/me", headers={"Authorization": f"Bearer {token}"}
        )
    except urllib.error.HTTPError as error:
        raise _translate_http_error(error) from error


def reveal_coordinates(reveal_code):
    """Return a spawn's coordinates, as `lat,lng`."""
    try:
        content = http_m.fetch_json(build_reveal_url(reveal_code))
    except urllib.error.HTTPError as error:
        raise _translate_http_error(error) from error
    return content["coords"]


def build_reveal_url(reveal_code):
    # Encoded as the site's pages encode it, a `/` included.
    return f"{API_BASE_URL}/reveal/{urllib.parse.quote(reveal_code, safe='')}"
