import dataclasses
import datetime
import json
import logging
import urllib.error

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import pvp_ranks as pvp_ranks_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import http as http_m
from pokemon_go_collection.sources import icons as icons_m
from pokemon_go_collection.sources import leekduck as leekduck_m
from pokemon_go_collection.sources import national_dex as national_dex_m
from pokemon_go_collection.sources import overrides as overrides_m
from pokemon_go_collection.sources import pvpoke as pvpoke_m

logger = logging.getLogger(__name__)


class CatalogRefreshError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class RefreshOutcome:
    entries_nb: int
    warnings: tuple[str, ...]


def is_refresh_due(
    db_file_path,
    refresh_period_duration,
    now,
    retry_delay_duration=datetime.timedelta(hours=1),
):
    """Tell whether the last successful refresh is older than the refresh period.

    A failed attempt postpones the next one by `retry_delay_duration`, so an
    unreachable source is not retried at every page render.
    """
    with db_m.db_conn(db_file_path) as conn:
        last_success_time, last_attempt_time = conn.execute(
            """
            SELECT
              MAX(CASE WHEN status = 'success' THEN end_time END),
              MAX(end_time)
            FROM catalog_refresh
            """
        ).fetchone()
    if last_attempt_time is None:
        return True
    if now - datetime.datetime.fromisoformat(last_attempt_time) < retry_delay_duration:
        return False
    return last_success_time is None or (
        now - datetime.datetime.fromisoformat(last_success_time)
        >= refresh_period_duration
    )


def run_refresh(cfg, now):
    """Bring the catalog up to date with its sources, as docs/architecture.md describes."""
    warnings = []
    game_master_timestamp = None
    try:
        pull_error_message = game_master_m.pull_game_master_repository(
            cfg.game_master_repository_folder_path
        )
        if pull_error_message is not None:
            warnings.append(pull_error_message)
        pvpoke_content = fetch_source_snapshot(
            pvpoke_m.PVPOKE_GAME_MASTER_URL,
            cfg.sources_folder_path / "pvpoke_game_master.json",
            warnings,
        )
        leekduck_content = fetch_source_snapshot(
            leekduck_m.LEEKDUCK_SHINY_DATA_URL,
            cfg.sources_folder_path / "leekduck_shiny_data.json",
            warnings,
        )

        game_master = game_master_m.load_game_master(
            cfg.game_master_repository_folder_path
        )
        game_master_timestamp = game_master.timestamp.isoformat()
        entries = catalog_m.build_catalog(
            national_dex_m.load_national_dex(cfg.data_folder_path / "national_dex.csv"),
            game_master,
            overrides_m.load_form_overrides(
                cfg.data_folder_path / "form_overrides.csv"
            ),
            pvpoke_m.parse_pvpoke_game_master(pvpoke_content),
            leekduck_m.parse_shiny_data(leekduck_content),
            overrides_m.load_release_overrides(
                cfg.data_folder_path / "release_overrides.csv"
            ),
        )
        icon_file_names = icons_m.download_missing_icons(
            entries, cfg.icons_folder_path, now.date()
        )
        with db_m.db_conn(cfg.db_file_path) as conn:
            write_catalog(conn, entries, icon_file_names)
            write_cp_multipliers(
                conn, pvp_ranks_m.build_cp_multipliers(game_master.cp_multipliers)
            )
    except Exception as error:
        _record_refresh(
            cfg.db_file_path,
            now,
            "failure",
            game_master_timestamp=game_master_timestamp,
            note="; ".join([*warnings, f"{type(error).__name__}: {error}"]),
        )
        raise

    _record_refresh(
        cfg.db_file_path,
        now,
        "success",
        game_master_timestamp=game_master_timestamp,
        entry_count=len(entries),
        note="; ".join(warnings) or None,
    )
    for warning in warnings:
        logger.warning(warning)
    logger.info(f"Catalog refreshed: {len(entries)} entries")
    return RefreshOutcome(entries_nb=len(entries), warnings=tuple(warnings))


def fetch_source_snapshot(url, snapshot_file_path, warnings):
    """Return the source's content, refreshing its snapshot when the source is reachable.

    An unreachable source falls back to its last snapshot, and adds a warning.
    """
    try:
        content = http_m.fetch_bytes(url)
    except (urllib.error.URLError, TimeoutError) as error:
        if not snapshot_file_path.exists():
            raise CatalogRefreshError(
                f"{url} is unreachable ({error}) and no snapshot of it exists"
            ) from error
        warnings.append(f"{url} is unreachable ({error}); using its last snapshot")
        return snapshot_file_path.read_bytes()
    snapshot_file_path.write_bytes(content)
    return content


def write_catalog(conn, entries, icon_file_names):
    """Replace the catalog rows, keeping each entry's identifier.

    Refuses to drop an entry the collection owns: a form vanishing from the
    sources is resolved in data/form_overrides.csv, not by losing a record.
    """
    new_entry_ids = {entry.entry_id for entry in entries}
    owned_rows = conn.execute(
        """
        SELECT entry_id
        FROM shundo
        """
    )
    owned_entry_ids = {row[0] for row in owned_rows}
    lost_owned_entry_ids = owned_entry_ids - new_entry_ids
    if lost_owned_entry_ids:
        raise CatalogRefreshError(
            f"The new catalog drops owned entries: {sorted(lost_owned_entry_ids)}"
        )

    current_rows = conn.execute(
        """
        SELECT entry_id
        FROM pokemon_entry
        """
    )
    current_entry_ids = {row[0] for row in current_rows}
    conn.execute(
        """
        DELETE FROM pokemon_evolution
        """
    )
    conn.execute(
        """
        DELETE FROM temporary_evolution
        """
    )
    conn.executemany(
        """
        DELETE FROM pokemon_entry
        WHERE entry_id = ?
        """,
        [(entry_id,) for entry_id in sorted(current_entry_ids - new_entry_ids)],
    )
    conn.executemany(
        """
        INSERT INTO pokemon_entry (
          entry_id, dex_number, name, form_ids, region, is_variant, display_order,
          pokemon_class, is_baby, is_released, shiny_release_date, icon_file_name,
          base_attack, base_defense, base_stamina
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (entry_id) DO UPDATE SET
          dex_number = excluded.dex_number,
          name = excluded.name,
          form_ids = excluded.form_ids,
          region = excluded.region,
          is_variant = excluded.is_variant,
          display_order = excluded.display_order,
          pokemon_class = excluded.pokemon_class,
          is_baby = excluded.is_baby,
          is_released = excluded.is_released,
          shiny_release_date = excluded.shiny_release_date,
          icon_file_name = excluded.icon_file_name,
          base_attack = excluded.base_attack,
          base_defense = excluded.base_defense,
          base_stamina = excluded.base_stamina
        """,
        [
            (
                entry.entry_id,
                entry.dex_number,
                entry.name,
                json.dumps(entry.form_ids),
                entry.region.value,
                int(entry.is_variant),
                entry.display_order,
                entry.pokemon_class.value if entry.pokemon_class else None,
                int(entry.is_baby),
                int(entry.is_released),
                (
                    entry.shiny_release_date.isoformat()
                    if entry.shiny_release_date
                    else None
                ),
                icon_file_names[entry.entry_id],
                *(entry.base_stats or (None, None, None)),
            )
            for entry in entries
        ],
    )
    conn.executemany(
        """
        INSERT INTO pokemon_evolution (source_entry_id, target_entry_id)
        VALUES (?, ?)
        """,
        [
            (entry.entry_id, target_entry_id)
            for entry in entries
            for target_entry_id in entry.evolution_target_entry_ids
        ],
    )
    conn.executemany(
        """
        INSERT INTO temporary_evolution (
          entry_id, temporary_evolution_id, name,
          base_attack, base_defense, base_stamina
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                entry.entry_id,
                temporary_evolution.temporary_evolution_id,
                catalog_m.build_temporary_evolution_name(
                    entry.name, temporary_evolution.temporary_evolution_id
                ),
                *temporary_evolution.stats,
            )
            for entry in entries
            for temporary_evolution in entry.temporary_evolutions
        ],
    )


def write_cp_multipliers(conn, cp_multipliers):
    conn.execute(
        """
        DELETE FROM cp_multiplier
        """
    )
    conn.executemany(
        """
        INSERT INTO cp_multiplier (level, multiplier)
        VALUES (?, ?)
        """,
        list(cp_multipliers.items()),
    )


def _record_refresh(
    db_file_path,
    start_time,
    status,
    game_master_timestamp=None,
    entry_count=None,
    note=None,
):
    end_time = datetime.datetime.now(datetime.timezone.utc)
    with db_m.db_conn(db_file_path) as conn:
        conn.execute(
            """
            INSERT INTO catalog_refresh (
              start_time, end_time, status, game_master_timestamp, entry_count, note
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                start_time.isoformat(),
                end_time.isoformat(),
                status,
                game_master_timestamp,
                entry_count,
                note,
            ),
        )


def load_last_refresh(db_file_path):
    """Return the last refresh as a dict, or None when none has run."""
    with db_m.db_conn(db_file_path) as conn:
        row = conn.execute(
            """
            SELECT end_time, status, game_master_timestamp, entry_count, note
            FROM catalog_refresh
            ORDER BY refresh_id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "end_time": row[0],
        "status": row[1],
        "game_master_timestamp": row[2],
        "entry_count": row[3],
        "note": row[4],
    }
