import datetime
import socket
import threading
import types
import urllib.error
from contextlib import nullcontext as does_not_raise
from unittest.mock import patch

import pytest

from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection.services import spawn_watch as spawn_watch_m
from pokemon_go_collection.sources import discord as discord_m
from pokemon_go_collection.sources import pogocoordinates as pogocoordinates_m

NOW = datetime.datetime(2026, 10, 10, 20, 0, tzinfo=datetime.timezone.utc)

# Rattata with an Alolan form, Zorua with a Hisuian form, Unown with letters
# only, Pikachu with a costume, and Basculegion, which the service lists under
# forms the catalog does not know.
SERVICE_FORMS = [
    pogocoordinates_m.ServiceForm(
        pokemon_id=19,
        form_id=45,
        form_name="RATTATA_NORMAL",
        form_suffix=None,
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=19,
        form_id=46,
        form_name="RATTATA_ALOLA",
        form_suffix="ALOLA",
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=25,
        form_id=598,
        form_name="PIKACHU_NORMAL",
        form_suffix=None,
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=25,
        form_id=894,
        form_name="PIKACHU_FALL_2019",
        form_suffix="FALL_2019",
        is_costume=True,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=201,
        form_id=1,
        form_name="UNOWN_A",
        form_suffix="A",
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=201,
        form_id=2,
        form_name="UNOWN_B",
        form_suffix="B",
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=570,
        form_id=2108,
        form_name="ZORUA_NORMAL",
        form_suffix=None,
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=570,
        form_id=2796,
        form_name="ZORUA_HISUIAN",
        form_suffix="HISUIAN",
        is_costume=False,
    ),
    pogocoordinates_m.ServiceForm(
        pokemon_id=902,
        form_id=3001,
        form_name="BASCULEGION_NORMAL",
        form_suffix=None,
        is_costume=False,
    ),
]

RATTATA_ALOLA = spawn_watch_m.HuntTarget(
    entry_id="RATTATA_ALOLA",
    dex_number=19,
    name="Rattata (Alolan)",
    form_ids=("RATTATA_ALOLA",),
)
PIKACHU = spawn_watch_m.HuntTarget(
    entry_id="PIKACHU",
    dex_number=25,
    name="Pikachu",
    form_ids=("PIKACHU_NORMAL", "PIKACHU"),
)
UNOWN = spawn_watch_m.HuntTarget(
    entry_id="UNOWN",
    dex_number=201,
    name="Unown",
    form_ids=("UNOWN", "UNOWN_A", "UNOWN_B"),
)
ZORUA = spawn_watch_m.HuntTarget(
    entry_id="ZORUA", dex_number=570, name="Zorua", form_ids=("ZORUA_NORMAL", "ZORUA")
)
BASCULEGION = spawn_watch_m.HuntTarget(
    entry_id="BASCULEGION",
    dex_number=902,
    name="Basculegion",
    form_ids=("BASCULEGION",),
)


def get_build_search_spec_test_data():
    test_cases = [
        {
            "id": "matched-forms-asked-for-by-form",
            "hunt_targets": [RATTATA_ALOLA, PIKACHU, UNOWN],
            "expected_pokemon_ids": [],
            "expected_species_forms": [(19, 46), (25, 598), (201, 1), (201, 2)],
        },
        {
            "id": "entry-without-listed-form-asked-for-whole",
            "hunt_targets": [ZORUA, BASCULEGION],
            "expected_pokemon_ids": [902],
            "expected_species_forms": [(570, 2108)],
        },
    ]

    return [
        pytest.param(
            test_case["hunt_targets"],
            test_case["expected_pokemon_ids"],
            test_case["expected_species_forms"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "hunt_targets,expected_pokemon_ids,expected_species_forms",
    get_build_search_spec_test_data(),
)
def test_build_search_spec(hunt_targets, expected_pokemon_ids, expected_species_forms):
    spec = spawn_watch_m.build_search_spec(hunt_targets, SERVICE_FORMS)

    assert spec["pokemon_ids"] == expected_pokemon_ids
    assert [
        (species_form["pokemon_id"], species_form["form_id"])
        for species_form in spec["species_forms"]
    ] == expected_species_forms
    assert (spec["shiny_only"], spec["iv_percent_min"], spec["sort"]) == (
        True,
        100,
        "IV",
    )


def get_find_spawn_form_name_test_data():
    test_cases = [
        {
            "id": "no-form-is-the-normal-form",
            "spawn_form": None,
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": "RATTATA_NORMAL",
        },
        {
            "id": "no-form-is-the-only-form",
            "spawn_form": None,
            "species_service_forms": SERVICE_FORMS[4:5],
            "expected_form_name": "UNOWN_A",
        },
        {
            "id": "no-form-among-several-without-normal",
            "spawn_form": None,
            "species_service_forms": SERVICE_FORMS[4:6],
            "expected_form_name": None,
        },
        {
            "id": "form-as-the-service-writes-it",
            "spawn_form": "Alola",
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": "RATTATA_ALOLA",
        },
        {
            "id": "form-by-suffix",
            "spawn_form": "ALOLA",
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": "RATTATA_ALOLA",
        },
        {
            "id": "form-by-name",
            "spawn_form": "RATTATA_ALOLA",
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": "RATTATA_ALOLA",
        },
        {
            "id": "form-by-identifier",
            "spawn_form": "46",
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": "RATTATA_ALOLA",
        },
        {
            "id": "unknown-form",
            "spawn_form": "GALARIAN",
            "species_service_forms": SERVICE_FORMS[0:2],
            "expected_form_name": None,
        },
    ]

    return [
        pytest.param(
            test_case["spawn_form"],
            test_case["species_service_forms"],
            test_case["expected_form_name"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "spawn_form,species_service_forms,expected_form_name",
    get_find_spawn_form_name_test_data(),
)
def test_find_spawn_form_name(spawn_form, species_service_forms, expected_form_name):
    assert (
        spawn_watch_m.find_spawn_form_name(spawn_form, species_service_forms)
        == expected_form_name
    )


def make_spawn(
    encounter_id,
    pokemon_id,
    form=None,
    despawn_time=NOW + datetime.timedelta(minutes=10),
):
    return pogocoordinates_m.Spawn(
        encounter_id=encounter_id,
        pokemon_id=pokemon_id,
        pokemon_name=f"Pokemon {pokemon_id}",
        form=form,
        cp=500,
        level=20.0,
        raw_iv="15/15/15",
        iv_percent=100.0,
        location="Orléans, Loiret, France",
        despawn_time=despawn_time,
        reveal_code=f"code-{encounter_id}",
    )


def get_match_spawns_test_data():
    test_cases = [
        {
            "id": "form-on-hunt-list",
            "spawns": [make_spawn("1", 19, form="Alola")],
            "expected_matches": [("1", "RATTATA_ALOLA", True)],
        },
        {
            "id": "other-form-of-hunted-species-dropped",
            "spawns": [make_spawn("1", 19)],
            "expected_matches": [],
        },
        {
            "id": "species-not-hunted-dropped",
            "spawns": [make_spawn("1", 10)],
            "expected_matches": [],
        },
        {
            "id": "despawning-within-a-minute-dropped",
            "spawns": [
                make_spawn("1", 570, despawn_time=NOW + datetime.timedelta(seconds=50))
            ],
            "expected_matches": [],
        },
        {
            "id": "unknown-form-of-hunted-species-kept",
            "spawns": [make_spawn("1", 570, form="SPOOKY")],
            "expected_matches": [("1", "ZORUA", False)],
        },
        {
            "id": "ordinary-form",
            "spawns": [make_spawn("1", 570)],
            "expected_matches": [("1", "ZORUA", True)],
        },
    ]

    return [
        pytest.param(
            test_case["spawns"],
            test_case["expected_matches"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize("spawns,expected_matches", get_match_spawns_test_data())
def test_match_spawns(spawns, expected_matches):
    matches = spawn_watch_m.match_spawns(
        spawns, [RATTATA_ALOLA, PIKACHU, UNOWN, ZORUA], SERVICE_FORMS, NOW
    )

    assert [
        (match.spawn.encounter_id, match.target.entry_id, match.is_form_recognized)
        for match in matches
    ] == expected_matches


def get_find_earliest_check_time_test_data():
    config = spawn_watch_m.WatchConfig(
        is_enabled=True, check_interval_duration=datetime.timedelta(minutes=5)
    )
    test_cases = [
        {
            "id": "never-checked",
            "last_search_time": None,
            "config": config,
            "expected_time": NOW,
        },
        {
            "id": "last-check-older-than-interval",
            "last_search_time": NOW - datetime.timedelta(minutes=10),
            "config": config,
            "expected_time": NOW,
        },
        {
            "id": "last-check-within-interval",
            "last_search_time": NOW - datetime.timedelta(minutes=2),
            "config": config,
            "expected_time": NOW + datetime.timedelta(minutes=3),
        },
    ]

    return [
        pytest.param(
            test_case["last_search_time"],
            test_case["config"],
            test_case["expected_time"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "last_search_time,config,expected_time", get_find_earliest_check_time_test_data()
)
def test_find_earliest_check_time(last_search_time, config, expected_time):
    assert (
        spawn_watch_m.find_earliest_check_time(last_search_time, config, NOW)
        == expected_time
    )


def get_build_alert_message_test_data():
    spawn = make_spawn("1", 570)
    test_cases = [
        {
            "id": "coordinates-revealed",
            "match": spawn_watch_m.SpawnMatch(
                spawn,
                ZORUA,
                is_form_recognized=True,
                coordinates="34.6512122,135.5342254",
            ),
            "expected_message": (
                "**Zorua** 15/15/15 · CP 500 · L20 · Orléans, Loiret, France · "
                "10 min left · Local time: 05:00 · 34.6512122,135.5342254"
            ),
        },
        {
            "id": "coordinates-not-revealed",
            "match": spawn_watch_m.SpawnMatch(spawn, ZORUA, is_form_recognized=True),
            "expected_message": (
                "**Zorua** 15/15/15 · CP 500 · L20 · Orléans, Loiret, France · "
                "10 min left · [coordinates]"
                "(<https://coordinates-api.pokemongopro.com/reveal/code-1>)"
            ),
        },
        {
            "id": "form-not-recognized",
            "match": spawn_watch_m.SpawnMatch(
                make_spawn("1", 570, form="Spooky"),
                ZORUA,
                is_form_recognized=False,
                coordinates="34.6512122,135.5342254",
            ),
            "expected_message": (
                "**Pokemon 570 (form Spooky, not recognized)** 15/15/15 · "
                "CP 500 · L20 · Orléans, Loiret, France · 10 min left · "
                "Local time: 05:00 · 34.6512122,135.5342254"
            ),
        },
    ]

    return [
        pytest.param(
            test_case["match"],
            test_case["expected_message"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize("match,expected_message", get_build_alert_message_test_data())
def test_build_alert_message(match, expected_message):
    assert spawn_watch_m.build_alert_message(match, NOW) == expected_message


def get_find_local_time_test_data():
    test_cases = [
        {
            "id": "summer-time",
            "coordinates": "48.126439,11.591259",
            "expected_time_text": "2026-10-10 22:00:00+02:00",
        },
        {
            "id": "no-summer-time",
            "coordinates": "34.6512122,135.5342254",
            "expected_time_text": "2026-10-11 05:00:00+09:00",
        },
    ]

    return [
        pytest.param(
            test_case["coordinates"],
            test_case["expected_time_text"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "coordinates,expected_time_text", get_find_local_time_test_data()
)
def test_find_local_time(coordinates, expected_time_text):
    local_time = spawn_watch_m.find_local_time(coordinates, NOW)
    assert local_time.isoformat(sep=" ") == expected_time_text


def test_reveal_coordinates_stops_revealing_when_rate_limited():
    matches = [
        spawn_watch_m.SpawnMatch(
            make_spawn(encounter_id, 570), ZORUA, is_form_recognized=True
        )
        for encounter_id in ("1", "2", "3")
    ]
    reveal_outcomes = [
        "34.6512122,135.5342254",
        pogocoordinates_m.PogocoordinatesRateLimitError(datetime.timedelta(hours=1)),
    ]

    with patch.object(
        pogocoordinates_m, "reveal_coordinates", side_effect=reveal_outcomes
    ) as reveal_mock:
        revealed_matches = spawn_watch_m.reveal_coordinates(matches)

    assert [match.coordinates for match in revealed_matches] == [
        "34.6512122,135.5342254",
        None,
        None,
    ]
    assert reveal_mock.call_count == 2


def test_post_alerts_posts_one_message_per_match():
    matches = [
        spawn_watch_m.SpawnMatch(
            make_spawn(encounter_id, 570), ZORUA, is_form_recognized=True
        )
        for encounter_id in ("1", "2")
    ]

    with patch.object(discord_m, "post_webhook_message") as post_mock:
        alerted_matches, error = spawn_watch_m.post_alerts(
            "https://discord.example/webhook", matches, NOW
        )

    assert alerted_matches == matches
    assert error is None
    assert [call.args[1] for call in post_mock.call_args_list] == [
        spawn_watch_m.build_alert_message(match, NOW) for match in matches
    ]


def test_post_alerts_stops_at_the_first_failed_message():
    matches = [
        spawn_watch_m.SpawnMatch(
            make_spawn(encounter_id, 570), ZORUA, is_form_recognized=True
        )
        for encounter_id in ("1", "2", "3")
    ]
    post_error = urllib.error.URLError("unreachable")

    with patch.object(
        discord_m, "post_webhook_message", side_effect=[None, post_error]
    ) as post_mock:
        alerted_matches, error = spawn_watch_m.post_alerts(
            "https://discord.example/webhook", matches, NOW
        )

    assert alerted_matches == matches[:1]
    assert error is post_error
    assert post_mock.call_count == 2


def get_save_watch_config_test_data():
    test_cases = [
        {
            "id": "minimum-interval",
            "check_interval_duration": datetime.timedelta(minutes=5),
            "expectation": does_not_raise(),
        },
        {
            "id": "interval-under-minimum-refused",
            "check_interval_duration": datetime.timedelta(minutes=4),
            "expectation": pytest.raises(ValueError),
        },
    ]

    return [
        pytest.param(
            test_case["check_interval_duration"],
            test_case["expectation"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "check_interval_duration,expectation", get_save_watch_config_test_data()
)
def test_save_watch_config(tmp_path, check_interval_duration, expectation):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)

    with expectation:
        spawn_watch_m.save_watch_config(db_file_path, True, check_interval_duration)
        config = spawn_watch_m.load_watch_config(db_file_path)
        assert config == spawn_watch_m.WatchConfig(
            is_enabled=True, check_interval_duration=check_interval_duration
        )


def test_delete_old_records_keeps_recent_alerts(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    old_time = NOW - datetime.timedelta(days=8)
    spawn_watch_m.record_alerts(
        db_file_path,
        [
            spawn_watch_m.SpawnMatch(
                make_spawn("old", 570), ZORUA, is_form_recognized=True
            )
        ],
        old_time,
    )
    spawn_watch_m.record_alerts(
        db_file_path,
        [
            spawn_watch_m.SpawnMatch(
                make_spawn("recent", 570), ZORUA, is_form_recognized=True
            )
        ],
        NOW,
    )
    spawn_watch_m.record_check(
        db_file_path, old_time, spawn_watch_m.CheckStatus.SUCCESS
    )
    spawn_watch_m.record_check(db_file_path, NOW, spawn_watch_m.CheckStatus.SUCCESS)

    spawn_watch_m.delete_old_records(db_file_path, NOW - datetime.timedelta(days=7))

    assert spawn_watch_m.load_alerted_encounter_ids(db_file_path) == {"recent"}
    assert spawn_watch_m.load_last_search_time(db_file_path) == NOW
    assert len(spawn_watch_m.load_recent_checks(db_file_path)) == 1


def test_run_spawn_check_unless_busy_skips_while_a_check_runs(tmp_path):
    cfg = types.SimpleNamespace(db_file_path=tmp_path / "collection.sqlite")
    check_lock = threading.Lock()
    check_lock.acquire()

    with patch.object(spawn_watch_m, "run_spawn_check") as run_spawn_check:
        outcome = spawn_watch_m.run_spawn_check_unless_busy(cfg, check_lock, NOW)

    assert outcome is None
    run_spawn_check.assert_not_called()


def test_run_spawn_check_unless_busy_records_an_unexpected_error(tmp_path):
    cfg = types.SimpleNamespace(db_file_path=tmp_path / "collection.sqlite")
    migrate_m.init_db(cfg.db_file_path)
    check_lock = threading.Lock()

    with patch.object(
        spawn_watch_m, "run_spawn_check", side_effect=KeyError("species")
    ):
        outcome = spawn_watch_m.run_spawn_check_unless_busy(cfg, check_lock, NOW)

    assert outcome == spawn_watch_m.CheckOutcome(spawn_watch_m.CheckStatus.FAILURE)
    assert [
        (check["status"], check["note"])
        for check in spawn_watch_m.load_recent_checks(cfg.db_file_path)
    ] == [("failure", "KeyError: 'species'")]
    assert not check_lock.locked()


def test_run_spawn_check_records_a_search_without_network_apart(tmp_path):
    cfg = make_check_cfg(tmp_path)
    error = urllib.error.URLError(
        socket.gaierror(-3, "Temporary failure in name resolution")
    )

    with (
        patch.object(spawn_watch_m, "load_service_forms", return_value=SERVICE_FORMS),
        patch.object(pogocoordinates_m, "search_spawns", side_effect=error),
    ):
        outcome = spawn_watch_m.run_spawn_check(cfg, NOW)

    assert outcome == spawn_watch_m.CheckOutcome(
        spawn_watch_m.CheckStatus.NETWORK_UNAVAILABLE
    )
    assert [
        check["status"] for check in spawn_watch_m.load_recent_checks(cfg.db_file_path)
    ] == ["network_unavailable"]


def make_check_cfg(folder_path):
    """Return the settings of a check, logged in and with a webhook set."""
    cfg = types.SimpleNamespace(
        db_file_path=folder_path / "collection.sqlite",
        pogocoordinates_token_file_path=folder_path / "token",
        discord_webhook_url_file_path=folder_path / "webhook_url",
        sources_folder_path=folder_path,
    )
    migrate_m.init_db(cfg.db_file_path)
    cfg.pogocoordinates_token_file_path.write_text("token", encoding="utf-8")
    cfg.discord_webhook_url_file_path.write_text(
        "https://discord.example/webhook", encoding="utf-8"
    )
    return cfg


def test_load_last_search_time_skips_the_checks_without_network(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    spawn_watch_m.record_check(
        db_file_path,
        NOW - datetime.timedelta(minutes=5),
        spawn_watch_m.CheckStatus.FAILURE,
    )
    spawn_watch_m.record_check(
        db_file_path, NOW, spawn_watch_m.CheckStatus.NETWORK_UNAVAILABLE
    )

    assert spawn_watch_m.load_last_search_time(
        db_file_path
    ) == NOW - datetime.timedelta(minutes=5)
