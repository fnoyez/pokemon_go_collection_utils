"""The spawn watch, as docs/spawn_watch.md describes it."""

import dataclasses
import datetime
import enum
import json
import logging
import random
import urllib.error

from pokemon_go_collection import db as db_m
from pokemon_go_collection import secret_files as secret_files_m
from pokemon_go_collection.services import hunt_list as hunt_list_m
from pokemon_go_collection.services import shundos as shundos_m
from pokemon_go_collection.sources import discord as discord_m
from pokemon_go_collection.sources import pogocoordinates as pogocoordinates_m

logger = logging.getLogger(__name__)

# The shortest interval between two checks. It keeps the watch within what a
# single human user of the service would generate, which its terms require:
# no caller may lower it.
MIN_CHECK_INTERVAL_DURATION = datetime.timedelta(minutes=5)

# Discord refuses a message longer than this many characters.
_DISCORD_MESSAGE_MAX_LENGTH = 2000

_AUTH_FAILURE_MESSAGE = (
    "The pogocoordinates.com login was refused, so the spawn watch is off. Log in "
    "again from the Spawn watch tab, then turn the watch back on."
)


class CheckStatus(enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"


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


def run_spawn_watch_loop(cfg, stop_event, wake_duration=datetime.timedelta(seconds=30)):
    """Run checks while the watch is on, until `stop_event` is set.

    The settings are read at every wake-up. An unexpected error ends the
    check it happened in, not the loop: the loop is the whole watch.
    """
    next_check_time = None
    while not stop_event.wait(wake_duration.total_seconds()):
        config = load_watch_config(cfg.db_file_path)
        if not config.is_enabled:
            continue
        now = datetime.datetime.now(datetime.timezone.utc)
        if next_check_time is None:
            next_check_time = find_first_check_time(
                load_last_check_time(cfg.db_file_path), config, now
            )
        if now < next_check_time:
            continue
        try:
            outcome = run_spawn_check(cfg, now)
        except Exception as error:
            logger.exception("Spawn check failed")
            record_check(
                cfg.db_file_path,
                now,
                CheckStatus.FAILURE,
                note=f"{type(error).__name__}: {error}",
            )
            outcome = CheckOutcome(CheckStatus.FAILURE)
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


def find_first_check_time(last_check_time, config, now):
    """Return when the watch checks first: an interval after the last check, at the earliest."""
    if last_check_time is None:
        return now
    return max(now, last_check_time + config.check_interval_duration)


def load_last_check_time(db_file_path):
    with db_m.db_conn(db_file_path) as conn:
        (last_check_time,) = conn.execute(
            """
            SELECT MAX(check_time)
            FROM spawn_check
            """
        ).fetchone()
    return (
        None
        if last_check_time is None
        else datetime.datetime.fromisoformat(last_check_time)
    )


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
        record_check(cfg.db_file_path, now, CheckStatus.FAILURE, note=str(error))
        return CheckOutcome(CheckStatus.FAILURE)

    matches = match_spawns(spawns, hunt_targets, service_forms, now)
    alerted_encounter_ids = load_alerted_encounter_ids(cfg.db_file_path)
    new_matches = [
        match
        for match in matches
        if match.spawn.encounter_id not in alerted_encounter_ids
    ]
    try:
        for message in build_alert_messages(new_matches, now):
            discord_m.post_webhook_message(webhook_url, message)
    except (urllib.error.URLError, TimeoutError) as error:
        record_check(
            cfg.db_file_path,
            now,
            CheckStatus.FAILURE,
            spawns_nb=len(spawns),
            note=f"Discord message not sent: {error}",
        )
        return CheckOutcome(CheckStatus.FAILURE)

    record_alerts(cfg.db_file_path, new_matches, now)
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
    board_entries = shundos_m.load_board_entries(db_file_path, today)
    hunt_entries = hunt_list_m.select_hunt_entries(
        board_entries, hunt_list_m.load_evolution_edges(db_file_path)
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
    return next(
        (
            service_form.form_name
            for service_form in species_service_forms
            if spawn_form
            in (
                service_form.form_name,
                service_form.form_suffix,
                str(service_form.form_id),
            )
        ),
        None,
    )


def load_alerted_encounter_ids(db_file_path):
    with db_m.db_conn(db_file_path) as conn:
        rows = conn.execute(
            """
            SELECT encounter_id
            FROM spawn_alert
            """
        ).fetchall()
    return {row[0] for row in rows}


def build_alert_messages(matches, now):
    """Return the Discord messages listing the matches, each within Discord's length limit."""
    messages = []
    lines = []
    for match in matches:
        line = _build_alert_line(match, now)
        if lines and len("\n".join([*lines, line])) > _DISCORD_MESSAGE_MAX_LENGTH:
            messages.append("\n".join(lines))
            lines = []
        lines.append(line)
    if lines:
        messages.append("\n".join(lines))
    return messages


def _build_alert_line(match, now):
    spawn = match.spawn
    if match.is_form_recognized:
        name = match.target.name
    else:
        name = f"{spawn.pokemon_name} (form {spawn.form}, not recognized)"
    remaining_minutes_nb = int((spawn.despawn_time - now).total_seconds() // 60)
    reveal_url = pogocoordinates_m.build_reveal_url(spawn.reveal_code)
    parts = [
        f"**{name}** {spawn.raw_iv}",
        f"CP {spawn.cp}",
        f"L{spawn.level:g}",
        spawn.location,
        f"{remaining_minutes_nb} min left",
        f"[coordinates](<{reveal_url}>)",
    ]
    return " · ".join(parts)


def record_alerts(db_file_path, matches, alert_time):
    with db_m.db_conn(db_file_path) as conn:
        conn.executemany(
            """
            INSERT INTO spawn_alert (
              encounter_id, entry_id, name, raw_iv, cp, level, location,
              despawn_time, reveal_url, alert_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            SELECT alert_time, name, raw_iv, cp, level, location, despawn_time, reveal_url
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
            "coordinates": reveal_url,
        }
        for alert_time, name, raw_iv, cp, level, location, despawn_time, reveal_url in rows
    ]
