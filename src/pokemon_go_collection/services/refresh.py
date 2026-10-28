import dataclasses
import datetime
import json
import logging
import urllib.error

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import costumes as costumes_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import pvp_ranks as pvp_ranks_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.sources import bulbapedia as bulbapedia_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import http as http_m
from pokemon_go_collection.sources import icons as icons_m
from pokemon_go_collection.sources import leekduck as leekduck_m
from pokemon_go_collection.sources import masterfile as masterfile_m
from pokemon_go_collection.sources import national_dex as national_dex_m
from pokemon_go_collection.sources import overrides as overrides_m
from pokemon_go_collection.sources import pvpoke as pvpoke_m
from pokemon_go_collection.sources import uicons as uicons_m

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
        game_master_content = fetch_source_snapshot(
            game_master_m.GAME_MASTER_URL,
            cfg.sources_folder_path / "game_master.json",
            warnings,
        )
        game_master_timestamp_content = fetch_source_snapshot(
            game_master_m.TIMESTAMP_URL,
            cfg.sources_folder_path / "game_master_timestamp.json",
            warnings,
        )
        uicons_index_content = fetch_source_snapshot(
            uicons_m.UICONS_INDEX_URL,
            cfg.sources_folder_path / "uicons_index.json",
            warnings,
        )
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
        bulbapedia_content = fetch_source_snapshot(
            bulbapedia_m.EVENT_POKEMON_URL,
            cfg.sources_folder_path / "bulbapedia_event_pokemon.wiki",
            warnings,
        )
        masterfile_content = fetch_source_snapshot(
            masterfile_m.MASTERFILE_URL,
            cfg.sources_folder_path / "masterfile.json",
            warnings,
        )

        game_master = game_master_m.load_game_master(
            game_master_content, game_master_timestamp_content
        )
        game_numbers = masterfile_m.parse_masterfile(masterfile_content)
        game_master_timestamp = game_master.timestamp.isoformat()
        national_dex_species = national_dex_m.load_national_dex(
            cfg.data_folder_path / "national_dex.csv"
        )
        form_overrides = overrides_m.load_form_overrides(
            cfg.data_folder_path / "form_overrides.csv"
        )
        costume_matches = overrides_m.load_costume_matches(
            cfg.data_folder_path / "costume_matches.csv"
        )
        shiny_releases = leekduck_m.parse_shiny_data(leekduck_content)
        entries = catalog_m.build_catalog(
            national_dex_species,
            game_master,
            form_overrides,
            costume_matches,
            pvpoke_m.parse_pvpoke_game_master(pvpoke_content),
            shiny_releases,
            overrides_m.load_release_overrides(
                cfg.data_folder_path / "release_overrides.csv"
            ),
        )
        costume_catalog = costumes_m.build_costume_catalog(
            national_dex_species,
            game_master,
            form_overrides,
            uicons_m.parse_index(uicons_index_content, game_numbers),
            shiny_releases,
            bulbapedia_m.parse_event_pokemon(bulbapedia_content.decode("utf-8")),
            costume_matches,
            game_numbers,
        )
        warnings.extend(build_costume_match_warnings(costume_catalog))
        icon_file_names = icons_m.download_missing_icons(
            entries, game_numbers, cfg.icons_folder_path, now.date()
        )
        costumed_pokemon_icon_file_names = icons_m.ensure_costumed_pokemon_icons(
            costume_catalog.costumed_pokemons, cfg.icons_folder_path, now.date()
        )
        with db_m.db_conn(cfg.db_file_path) as conn:
            write_catalog(conn, entries, icon_file_names)
            write_costumed_pokemons(
                conn,
                costume_catalog.costumed_pokemons,
                costumed_pokemon_icon_file_names,
                entries,
            )
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


def build_costume_match_warnings(costume_catalog):
    """Return a warning for each change data/costume_matches.csv calls for.

    `scripts/report_costume_catalog.py` reports them in full.
    """
    warnings = []
    if costume_catalog.unmatched_sprites:
        sprite_names = ", ".join(
            f"{sprite.dex_number} {sprite.code}"
            for sprite in costume_catalog.unmatched_sprites
        )
        warnings.append(
            f"Bulbapedia sprites without a line in data/costume_matches.csv: {sprite_names}"
        )
    if costume_catalog.unused_matches:
        match_names = ", ".join(
            f"{match.dex_number} {match.bulbapedia_code}"
            for match in costume_catalog.unused_matches
        )
        warnings.append(
            f"Lines of data/costume_matches.csv standing for no Bulbapedia sprite: {match_names}"
        )
    return warnings


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
    conn.execute(
        """
        DELETE FROM battle_form
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
    conn.executemany(
        """
        INSERT INTO battle_form (
          form_id, entry_id, name, form_order,
          base_attack, base_defense, base_stamina
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                battle_form.form_id,
                entry.entry_id,
                battle_form.name,
                form_order,
                *battle_form.stats,
            )
            for entry in entries
            for form_order, battle_form in enumerate(entry.battle_forms)
        ],
    )


def write_costumed_pokemons(conn, costumed_pokemons, icon_file_names, entries):
    """Replace the costumed Pokémon rows, keeping each one's identifier.

    A costumed shundo owned on a costumed Pokémon identified by its Bulbapedia
    code moves to the one standing for the same sprite, once a source gives its
    game name: `ZUBAT.TopHat` becomes `ZUBAT.<costume>`. Refuses to drop any
    other costumed Pokémon the collection owns, as `write_catalog` does.
    """
    new_ids = {
        costumed_pokemon.costumed_pokemon_id for costumed_pokemon in costumed_pokemons
    }
    # The species' class and baby status are those of its base entry, which
    # comes first among the entries of its number.
    base_entries = {}
    for entry in entries:
        base_entries.setdefault(entry.dex_number, entry)
    conn.executemany(
        """
        INSERT INTO costumed_pokemon (
          costumed_pokemon_id, dex_number, name, region, display_order,
          form_suffix, costume, bulbapedia_code, release_date, shiny_release_date,
          costume_year, pokemon_class, is_baby, icon_file_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (costumed_pokemon_id) DO UPDATE SET
          dex_number = excluded.dex_number,
          name = excluded.name,
          region = excluded.region,
          display_order = excluded.display_order,
          form_suffix = excluded.form_suffix,
          costume = excluded.costume,
          bulbapedia_code = excluded.bulbapedia_code,
          release_date = excluded.release_date,
          shiny_release_date = excluded.shiny_release_date,
          costume_year = excluded.costume_year,
          pokemon_class = excluded.pokemon_class,
          is_baby = excluded.is_baby,
          icon_file_name = excluded.icon_file_name
        """,
        [
            (
                costumed_pokemon.costumed_pokemon_id,
                costumed_pokemon.key.dex_number,
                costumed_pokemon.name,
                regions_m.find_region(costumed_pokemon.key.dex_number).value,
                display_order,
                costumed_pokemon.key.form_suffix,
                costumed_pokemon.key.costume,
                costumed_pokemon.key.bulbapedia_code,
                _format_date(costumed_pokemon.release_date),
                _format_date(costumed_pokemon.shiny_release_date),
                costumed_pokemon.costume_year,
                _find_pokemon_class_value(
                    base_entries.get(costumed_pokemon.key.dex_number)
                ),
                int(
                    costumed_pokemon.key.dex_number in base_entries
                    and base_entries[costumed_pokemon.key.dex_number].is_baby
                ),
                icon_file_names[costumed_pokemon.costumed_pokemon_id],
            )
            for display_order, costumed_pokemon in enumerate(costumed_pokemons)
        ],
    )

    lost_owned_rows = conn.execute(
        """
        SELECT s.costumed_pokemon_id, c.dex_number, c.bulbapedia_code
        FROM costumed_shundo AS s
        JOIN costumed_pokemon AS c USING (costumed_pokemon_id)
        """
    ).fetchall()
    new_ids_by_sprite = {
        (costumed_pokemon.key.dex_number, bulbapedia_code): (
            costumed_pokemon.costumed_pokemon_id
        )
        for costumed_pokemon in costumed_pokemons
        for bulbapedia_code in costumed_pokemon.bulbapedia_codes
    }
    lost_owned_ids = []
    for owned_id, dex_number, bulbapedia_code in lost_owned_rows:
        if owned_id in new_ids:
            continue
        if (dex_number, bulbapedia_code) in new_ids_by_sprite:
            new_id = new_ids_by_sprite[(dex_number, bulbapedia_code)]
            conn.execute(
                """
                UPDATE costumed_shundo
                SET costumed_pokemon_id = ?
                WHERE costumed_pokemon_id = ?
                """,
                (new_id, owned_id),
            )
            logger.info(f"Costumed shundo {owned_id} moved to {new_id}")
        else:
            lost_owned_ids.append(owned_id)
    if lost_owned_ids:
        raise CatalogRefreshError(
            f"The new costumed Pokémon drop owned ones: {sorted(lost_owned_ids)}"
        )

    conn.execute(
        """
        DELETE FROM costumed_pokemon_evolution
        """
    )
    current_ids = {
        row[0]
        for row in conn.execute(
            """
            SELECT costumed_pokemon_id
            FROM costumed_pokemon
            """
        )
    }
    conn.executemany(
        """
        DELETE FROM costumed_pokemon
        WHERE costumed_pokemon_id = ?
        """,
        [
            (costumed_pokemon_id,)
            for costumed_pokemon_id in sorted(current_ids - new_ids)
        ],
    )
    conn.executemany(
        """
        INSERT INTO costumed_pokemon_evolution (
          source_costumed_pokemon_id, target_costumed_pokemon_id
        )
        VALUES (?, ?)
        """,
        [
            (costumed_pokemon.costumed_pokemon_id, target_id)
            for costumed_pokemon in costumed_pokemons
            for target_id in costumed_pokemon.evolution_target_ids
        ],
    )


def _format_date(date):
    return date.isoformat() if date is not None else None


def _find_pokemon_class_value(base_entry):
    if base_entry is None or base_entry.pokemon_class is None:
        return None
    return base_entry.pokemon_class.value


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
