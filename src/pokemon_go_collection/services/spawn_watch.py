"""The spawn watch, as docs/spawn_watch.md describes it."""

import dataclasses
import datetime
import enum
import json
import logging
import random
import re
import urllib.error
import zoneinfo

import timezonefinder

from pokemon_go_collection import db as db_m
from pokemon_go_collection import secret_files as secret_files_m
from pokemon_go_collection.services import hunt_list as hunt_list_m
from pokemon_go_collection.services import shundos as shundos_m
from pokemon_go_collection.sources import discord as discord_m
from pokemon_go_collection.sources import http as http_m
from pokemon_go_collection.sources import pogocoordinates as pogocoordinates_m

logger = logging.getLogger(__name__)

# The shortest interval between two checks. It keeps the watch within what a
# single human user of the service would generate, which its terms require:
# no caller may lower it.
MIN_CHECK_INTERVAL_DURATION = datetime.timedelta(minutes=5)

_AUTH_FAILURE_MESSAGE = (
    "The pogocoordinates.com login was refused, so the spawn watch is off. Log in "
    "again from the Spawn watch tab, then turn the watch back on."
)


class CheckStatus(enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    # The search failed before reaching the service, for want of a network.
    NETWORK_UNAVAILABLE = "network_unavailable"


@dataclasses.dataclass(frozen=True)
class WatchConfig:
    is_enabled: bool
    check_interval_duration: datetime.timedelta


@dataclasses.dataclass(frozen=True)
class CheckOutcome:
    status: CheckStatus
    # The wait the service asked for, when it refused the search for its rate.
    retry_after_duration: datetime.timedelta | None = None


@dataclasses.dataclass(frozen=True)
class HuntTarget:
    """A hunt list entry, with the game master forms it stands for."""

    entry_id: str
    dex_number: int
    name: str
    form_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class SpawnMatch:
    spawn: pogocoordinates_m.Spawn
    target: HuntTarget
    # False when the spawn's form matched no form of the service's catalog.
    is_form_recognized: bool
    # `lat,lng`, once revealed.
    coordinates: str | None = None


def run_spawn_watch_loop(
    cfg,
    check_lock,
    stop_event,
    wake_duration=datetime.timedelta(seconds=30),
    retry_duration=datetime.timedelta(minutes=1),
):
    """Run checks while the watch is on, until `stop_event` is set.

    The settings and the last search time are read at every wake-up, so a check
    started from the tab postpones the next one like any other. `check_lock` is
    held by the check running, whichever started it. A check whose search did
    not reach the service is tried again after `retry_duration`: it adds no
    search to those the service sees.
    """
    next_check_time = None
    while not stop_event.wait(wake_duration.total_seconds()):
        config = load_watch_config(cfg.db_file_path)
        if not config.is_enabled:
            continue
        now = datetime.datetime.now(datetime.timezone.utc)
        earliest_check_time = find_earliest_check_time(
            load_last_search_time(cfg.db_file_path), config, now
        )
        next_check_time = (
            earliest_check_time
            if next_check_time is None
            else max(next_check_time, earliest_check_time)
        )
        if now < next_check_time:
            continue
        outcome = run_spawn_check_unless_busy(cfg, check_lock, now)
        if outcome is None:
            continue
        if outcome.status == CheckStatus.NETWORK_UNAVAILABLE:
            wait_duration = retry_duration
        else:
            wait_duration = max(
                config.check_interval_duration,
                outcome.retry_after_duration or datetime.timedelta(0),
            )
        next_check_time = now + wait_duration + _draw_jitter_duration()


def load_watch_config(db_file_path):
    with db_m.db_conn(db_file_path) as conn:
        is_enabled, check_interval_minutes = conn.execute(
            """
            SELECT is_enabled, check_interval_minutes
            FROM spawn_watch_config
            """
        ).fetchone()
    return WatchConfig(
        bool(is_enabled), datetime.timedelta(minutes=check_interval_minutes)
    )


def find_earliest_check_time(last_search_time, config, now):
    """Return when the watch may check next: an interval after the last search, or now."""
    if last_search_time is None:
        return now
    return max(now, last_search_time + config.check_interval_duration)


def load_last_search_time(db_file_path):
    """Return the time of the last check whose search may have reached the service."""
    with db_m.db_conn(db_file_path) as conn:
        (last_search_time,) = conn.execute(
            """
            SELECT MAX(check_time)
            FROM spawn_check
            WHERE status != ?
            """,
            (CheckStatus.NETWORK_UNAVAILABLE.value,),
        ).fetchone()
    return (
        None
        if last_search_time is None
        else datetime.datetime.fromisoformat(last_search_time)
    )


def run_spawn_check_unless_busy(cfg, check_lock, now):
    """Run a check, unless one is already running; return its outcome, or None.

    An unexpected error ends the check, recorded as failed, rather than its
    caller: for the loop, that caller is the whole watch.
    """
    if not check_lock.acquire(blocking=False):
        return None
    try:
        return run_spawn_check(cfg, now)
    except Exception as error:
        logger.exception("Spawn check failed")
        record_check(
            cfg.db_file_path,
            now,
            CheckStatus.FAILURE,
            note=f"{type(error).__name__}: {error}",
        )
        return CheckOutcome(CheckStatus.FAILURE)
    finally:
        check_lock.release()


def run_spawn_check(cfg, now, retention_duration=datetime.timedelta(days=7)):
    """Search once, alert on the new hunt list spawns, record the check."""
    token = secret_files_m.read_secret(cfg.pogocoordinates_token_file_path)
    webhook_url = secret_files_m.read_secret(cfg.discord_webhook_url_file_path)
    if webhook_url is None:
        record_check(
            cfg.db_file_path, now, CheckStatus.FAILURE, note="No Discord webhook set"
        )
        return CheckOutcome(CheckStatus.FAILURE)
    if token is None:
        return _stop_for_login(cfg.db_file_path, webhook_url, now, "Not logged in")

    service_forms = load_service_forms(
        cfg.sources_folder_path / "pogocoordinates_catalog.json", now
    )
    hunt_targets = load_hunt_targets(cfg.db_file_path, now.date())
    try:
        spawns = pogocoordinates_m.search_spawns(
            token, build_search_spec(hunt_targets, service_forms)
        )
    except pogocoordinates_m.PogocoordinatesAuthError as error:
        return _stop_for_login(cfg.db_file_path, webhook_url, now, str(error))
    except pogocoordinates_m.PogocoordinatesRateLimitError as error:
        record_check(cfg.db_file_path, now, CheckStatus.RATE_LIMITED, note=str(error))
        return CheckOutcome(CheckStatus.RATE_LIMITED, error.retry_after_duration)
    except (urllib.error.URLError, TimeoutError) as error:
        status = (
            CheckStatus.NETWORK_UNAVAILABLE
            if http_m.is_unsent_request_error(error)
            else CheckStatus.FAILURE
        )
        record_check(cfg.db_file_path, now, status, note=str(error))
        return CheckOutcome(status)

    matches = match_spawns(spawns, hunt_targets, service_forms, now)
    alerted_encounter_ids = load_alerted_encounter_ids(cfg.db_file_path)
    new_matches = reveal_coordinates(
        [
            match
            for match in matches
            if match.spawn.encounter_id not in alerted_encounter_ids
        ]
    )
    alerted_matches, error = post_alerts(webhook_url, new_matches, now)
    # The matches alerted before a message failed are recorded, so the next
    # check alerts only the others again.
    record_alerts(cfg.db_file_path, alerted_matches, now)
    if error is not None:
        record_check(
            cfg.db_file_path,
            now,
            CheckStatus.FAILURE,
            spawns_nb=len(spawns),
            alerts_nb=len(alerted_matches),
            note=f"Discord message not sent: {error}",
        )
        return CheckOutcome(CheckStatus.FAILURE)

    record_check(
        cfg.db_file_path,
        now,
        CheckStatus.SUCCESS,
        spawns_nb=len(spawns),
        alerts_nb=len(new_matches),
    )
    delete_old_records(cfg.db_file_path, now - retention_duration)
    logger.info(f"Spawn check: {len(spawns)} spawns, {len(new_matches)} alerted")
    return CheckOutcome(CheckStatus.SUCCESS)


def record_check(
    db_file_path, check_time, status, spawns_nb=None, alerts_nb=None, note=None
):
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            INSERT INTO spawn_check (check_time, status, spawn_count, alert_count, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (check_time.isoformat(), status.value, spawns_nb, alerts_nb, note),
        )


def _stop_for_login(db_file_path, webhook_url, now, note):
    """Turn the watch off and ask, on Discord, for a new login."""
    record_check(db_file_path, now, CheckStatus.UNAUTHORIZED, note=note)
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            UPDATE spawn_watch_config
            SET is_enabled = 0
            """
        )
    discord_m.post_webhook_message(webhook_url, _AUTH_FAILURE_MESSAGE)
    logger.warning(f"Spawn watch turned off: {note}")
    return CheckOutcome(CheckStatus.UNAUTHORIZED)


def load_service_forms(
    snapshot_file_path, now, max_age_duration=datetime.timedelta(days=1)
):
    """Return the service's forms, from a snapshot fetched again when it is `max_age_duration` old.

    An unreachable service leaves the existing snapshot in use.
    """
    if snapshot_file_path.exists():
        snapshot_time = datetime.datetime.fromtimestamp(
            snapshot_file_path.stat().st_mtime, tz=datetime.timezone.utc
        )
        is_fresh = now - snapshot_time < max_age_duration
    else:
        is_fresh = False
    if not is_fresh:
        try:
            content = pogocoordinates_m.fetch_form_catalog_content()
        except (urllib.error.URLError, TimeoutError) as error:
            if not snapshot_file_path.exists():
                raise
            logger.warning(f"Service catalog unreachable ({error}); using its snapshot")
        else:
            snapshot_file_path.write_text(json.dumps(content), encoding="utf-8")
    return pogocoordinates_m.parse_form_catalog(
        json.loads(snapshot_file_path.read_text(encoding="utf-8"))
    )


def load_hunt_targets(db_file_path, today):
    board_entries = shundos_m.load_board_entries(
        db_file_path, shundos_m.Board.SHUNDOS, today
    )
    hunt_entries = hunt_list_m.select_hunt_entries(
        board_entries,
        hunt_list_m.load_evolution_edges(db_file_path, shundos_m.Board.SHUNDOS),
    )
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT entry_id, form_ids
            FROM pokemon_entry
            """
        ).fetchall()
    form_ids_by_entry_id = {
        entry_id: json.loads(form_ids) for entry_id, form_ids in rows
    }
    return [
        HuntTarget(
            entry.entry_id,
            entry.dex_number,
            entry.name,
            tuple(form_ids_by_entry_id[entry.entry_id]),
        )
        for entry in hunt_entries
    ]


def build_search_spec(hunt_targets, service_forms):
    """Return the search for shundos of the hunt targets, following docs/spawn_watch.md, *A check*."""
    service_forms_by_key = {
        (service_form.pokemon_id, service_form.form_name): service_form
        for service_form in service_forms
        if not service_form.is_costume and service_form.form_name is not None
    }
    species_forms = set()
    pokemon_ids = set()
    for target in hunt_targets:
        matched_service_forms = [
            service_forms_by_key[(target.dex_number, form_id)]
            for form_id in target.form_ids
            if (target.dex_number, form_id) in service_forms_by_key
        ]
        if not matched_service_forms:
            pokemon_ids.add(target.dex_number)
        species_forms.update(
            (service_form.pokemon_id, service_form.form_id)
            for service_form in matched_service_forms
        )
    return {
        "shiny_only": True,
        "shiny_account": None,
        "pokemon_ids": sorted(pokemon_ids),
        "species_forms": [
            {"pokemon_id": pokemon_id, "form_id": form_id, "costume_id": None}
            for pokemon_id, form_id in sorted(species_forms)
        ],
        "iv_mode": "percent",
        "iv_percent_min": 100,
        "sort": "IV",
    }


def match_spawns(
    spawns,
    hunt_targets,
    service_forms,
    now,
    min_remaining_duration=datetime.timedelta(minutes=1),
):
    """Return the spawns worth an alert, each with the hunt target it is.

    The matching rules are in docs/spawn_watch.md, *A check*.
    """
    targets_by_form_key = {
        (target.dex_number, form_id): target
        for target in hunt_targets
        for form_id in target.form_ids
    }
    targets_by_dex_number = {}
    for target in hunt_targets:
        targets_by_dex_number.setdefault(target.dex_number, []).append(target)
    service_forms_by_dex_number = {}
    for service_form in service_forms:
        if not service_form.is_costume:
            service_forms_by_dex_number.setdefault(service_form.pokemon_id, []).append(
                service_form
            )

    matches = []
    for spawn in spawns:
        if spawn.despawn_time - now < min_remaining_duration:
            continue
        form_name = find_spawn_form_name(
            spawn.form, service_forms_by_dex_number.get(spawn.pokemon_id, [])
        )
        if form_name is not None:
            target = targets_by_form_key.get((spawn.pokemon_id, form_name))
            if target is not None:
                matches.append(SpawnMatch(spawn, target, is_form_recognized=True))
        elif spawn.pokemon_id in targets_by_dex_number:
            matches.append(
                SpawnMatch(
                    spawn,
                    targets_by_dex_number[spawn.pokemon_id][0],
                    is_form_recognized=False,
                )
            )
    return matches


def find_spawn_form_name(spawn_form, species_service_forms):
    """Return the game master form name of a spawn's form, or None when it matches none."""
    if spawn_form is None:
        normal_forms = [
            service_form
            for service_form in species_service_forms
            if service_form.form_name is not None
            and service_form.form_name.endswith("_NORMAL")
        ]
        if normal_forms:
            return normal_forms[0].form_name
        if len(species_service_forms) == 1:
            return species_service_forms[0].form_name
        return None
    # The service writes a form as a word (`Alola`, `Pom-Pom`), where its
    # catalog holds an identifier (`ALOLA`, `POMPOM`).
    normalized_spawn_form = _normalize_form_name(spawn_form)
    return next(
        (
            service_form.form_name
            for service_form in species_service_forms
            if normalized_spawn_form
            in (
                _normalize_form_name(service_form.form_name),
                _normalize_form_name(service_form.form_suffix),
                str(service_form.form_id),
            )
        ),
        None,
    )


def _normalize_form_name(form_name):
    return None if form_name is None else re.sub(r"[^A-Z0-9]", "", form_name.upper())


def load_alerted_encounter_ids(db_file_path):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT encounter_id
            FROM spawn_alert
            """
        ).fetchall()
    return {row[0] for row in rows}


def reveal_coordinates(matches):
    """Return the matches with their coordinates, for those the service reveals.

    A match the service does not reveal keeps its reveal link alone, and a
    refusal for the rate leaves the following ones unrevealed too.
    """
    revealed_matches = []
    for match_index, match in enumerate(matches):
        try:
            coordinates = pogocoordinates_m.reveal_coordinates(match.spawn.reveal_code)
        except pogocoordinates_m.PogocoordinatesRateLimitError as error:
            logger.warning(f"Coordinates not revealed: {error}")
            revealed_matches.extend(matches[match_index:])
            break
        except (urllib.error.URLError, TimeoutError) as error:
            logger.warning(
                f"Coordinates of {match.spawn.encounter_id} not revealed: {error}"
            )
            revealed_matches.append(match)
        else:
            revealed_matches.append(dataclasses.replace(match, coordinates=coordinates))
    return revealed_matches


def post_alerts(webhook_url, matches, now):
    """Post one Discord message per match, in order, stopping at the first failure.

    Return the matches posted, and the error that stopped the posting or None.
    """
    alerted_matches = []
    for match in matches:
        try:
            discord_m.post_webhook_message(webhook_url, build_alert_message(match, now))
        except (urllib.error.URLError, TimeoutError) as error:
            return alerted_matches, error
        alerted_matches.append(match)
    return alerted_matches, None


def build_alert_message(match, now):
    """Return the Discord message alerting on one match."""
    spawn = match.spawn
    if match.is_form_recognized:
        name = match.target.name
    else:
        name = f"{spawn.pokemon_name} (form {spawn.form}, not recognized)"
    remaining_minutes_nb = int((spawn.despawn_time - now).total_seconds() // 60)
    parts = [
        f"**{name}** {spawn.raw_iv}",
        f"CP {spawn.cp}",
        f"L{spawn.level:g}",
        spawn.location,
        f"{remaining_minutes_nb} min left",
    ]
    if match.coordinates is None:
        reveal_url = pogocoordinates_m.build_reveal_url(spawn.reveal_code)
        parts.append(f"[coordinates](<{reveal_url}>)")
    else:
        local_time = find_local_time(match.coordinates, now)
        if local_time is not None:
            parts.append(f"Local time: {local_time:%H:%M}")
        parts.append(match.coordinates)
    return " · ".join(parts)


def find_local_time(coordinates, now):
    """Return `now` in the time zone of the `lat,lng` coordinates, or None outside every zone."""
    lat_text, lng_text = coordinates.split(",")
    time_zone_name = timezonefinder.timezone_at(
        lng=float(lng_text), lat=float(lat_text)
    )
    if time_zone_name is None:
        return None
    return now.astimezone(zoneinfo.ZoneInfo(time_zone_name))


def record_alerts(db_file_path, matches, alert_time):
    with db_m.db_conn(db_file_path) as conn:
        conn.executemany(
            """
            INSERT INTO spawn_alert (
              encounter_id, entry_id, name, raw_iv, cp, level, location,
              despawn_time, reveal_url, coordinates, alert_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    match.spawn.encounter_id,
                    match.target.entry_id,
                    match.target.name,
                    match.spawn.raw_iv,
                    match.spawn.cp,
                    match.spawn.level,
                    match.spawn.location,
                    match.spawn.despawn_time.isoformat(),
                    pogocoordinates_m.build_reveal_url(match.spawn.reveal_code),
                    match.coordinates,
                    alert_time.isoformat(),
                )
                for match in matches
            ],
        )


def delete_old_records(db_file_path, cutoff_time):
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            DELETE FROM spawn_check
            WHERE check_time < ?
            """,
            (cutoff_time.isoformat(),),
        )
        conn.execute(
            """
            DELETE FROM spawn_alert
            WHERE alert_time < ?
            """,
            (cutoff_time.isoformat(),),
        )


def _draw_jitter_duration():
    return datetime.timedelta(seconds=random.uniform(0, 30))


def save_watch_config(db_file_path, is_enabled, check_interval_duration):
    """Store the settings; an interval under the minimum is refused with ValueError."""
    if check_interval_duration < MIN_CHECK_INTERVAL_DURATION:
        raise ValueError(
            f"The check interval cannot be under {MIN_CHECK_INTERVAL_DURATION}"
        )
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            UPDATE spawn_watch_config
            SET is_enabled = ?, check_interval_minutes = ?
            """,
            (int(is_enabled), int(check_interval_duration.total_seconds() // 60)),
        )


def load_recent_checks(db_file_path, checks_nb=20):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT check_time, status, spawn_count, alert_count, note
            FROM spawn_check
            ORDER BY check_time DESC
            LIMIT ?
            """,
            (checks_nb,),
        ).fetchall()
    return [
        {
            "check_time": check_time,
            "status": status,
            "spawns": spawn_count,
            "alerts": alert_count,
            "note": note,
        }
        for check_time, status, spawn_count, alert_count, note in rows
    ]


def load_recent_alerts(db_file_path, alerts_nb=50):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT
              alert_time, name, raw_iv, cp, level, location, despawn_time,
              coordinates, reveal_url
            FROM spawn_alert
            ORDER BY alert_time DESC
            LIMIT ?
            """,
            (alerts_nb,),
        ).fetchall()
    return [
        {
            "alert_time": alert_time,
            "name": name,
            "iv": raw_iv,
            "cp": cp,
            "level": level,
            "location": location,
            "despawn_time": despawn_time,
            "coordinates": coordinates,
            "reveal_url": reveal_url,
        }
        for (
            alert_time,
            name,
            raw_iv,
            cp,
            level,
            location,
            despawn_time,
            coordinates,
            reveal_url,
        ) in rows
    ]
