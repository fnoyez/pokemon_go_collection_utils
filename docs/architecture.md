# Architecture — Pokémon GO Collection Utils

## Overview

- Local-first, single-user application: it runs on the user's machine, serves one person, and needs no account or remote server.
- Storage: one SQLite database file, accessed with direct SQL (no ORM).
- Interface: a Streamlit application, one tab per feature. The Shundos tab is the first.
- Services: plain Python modules for building the catalog, refreshing its sources, recording the collection and taking backups, free of any Streamlit code.
- CLI: initializing the database, taking a backup, refreshing the catalog, and running one spawn check (`pgcollection-spawn-check`), which refuses to run within the minimum interval of the last check.

## Module layout

- `run_app.py` — the file `streamlit run` starts; sets up logging and calls `app.main`.
- `src/pokemon_go_collection/logging_setup.py` — the logging setup every entry point calls.
- `src/pokemon_go_collection/app.py` — the Streamlit page: configuration, database initialization, automatic backup and refresh, tabs.
- `src/pokemon_go_collection/config.py` — configuration: paths and refresh period.
- `src/pokemon_go_collection/db.py` — connection helpers.
- `src/pokemon_go_collection/migrate.py` and `migrations/` — the migration runner and the schema.
- `src/pokemon_go_collection/regions.py` — the regions and the National Pokédex numbers each introduced.
- `src/pokemon_go_collection/sources/` — one module per data source, each turning the source's raw content into plain records: `game_master.py`, `national_dex.py`, `pvpoke.py`, `leekduck.py`, `overrides.py`, `icons.py`, `pogocoordinates.py`, `discord.py`; and `http.py`, the download helper they share.
- `src/pokemon_go_collection/pvp_ranks.py` — the PvP rank computation of [pvp_ranks.md](pvp_ranks.md), pure functions over base stats and CP multipliers.
- `src/pokemon_go_collection/catalog.py` — combines the sources' records into catalog entries, ordered and with their statuses, following [catalog.md](catalog.md). Pure functions over records, so it is tested without network or database.
- `src/pokemon_go_collection/services/` — `refresh.py` (fetching sources and rebuilding the catalog tables), `shundos.py` (reading and recording the collection), `hunt_list.py` (the shundo hunt list), `spawn_watch.py` (the spawn watch) and `pogocoordinates_login.py` (its login), `backups.py`.
- `src/pokemon_go_collection/ui_shundos.py` — the Shundos tab.
- `src/pokemon_go_collection/ui_pvp_ranks.py` — the PvP ranks tab.
- `src/pokemon_go_collection/ui_spawn_watch.py` — the Spawn watch tab; the watch itself is `services/spawn_watch.py`, described in [spawn_watch.md](spawn_watch.md).
- `src/pokemon_go_collection/components/pokemon_grid/` — the clickable icon grid, a Streamlit component (below).
- `src/pokemon_go_collection/cli.py` — the CLI entry points.
- `scripts/seed_national_dex.py` — writes `data/national_dex.csv` from PokeAPI.
- `data/` — the committed reference data: the National Pokédex seed and the hand-maintained overrides.

## Storage and configuration

- Application home: `~/.pokemon_go_collection`.
- Database file: `~/.pokemon_go_collection/collection.sqlite`.
- Source snapshots: `~/.pokemon_go_collection/sources/`, the last successfully fetched copy of each downloaded source.
- Backup folder: `/home/pavel/Data/Projects/data/.pokemon_go_collection_db_backup`.
- Icon cache: `static/icons/` in the repository, ignored by git. Streamlit serves files only from a `static` folder next to the script it runs, so the cache lives there rather than in the application home; it holds nothing that a refresh cannot download again.
- Game master repository: `../game_masters`, next to this repository.
- Spawn watch login profile and secrets: see [spawn_watch.md](spawn_watch.md), *Storage*.

Paths are validated at startup, and the application stops with an error when one is invalid. The backup folder has to exist beforehand.

## Data model

The schema is the ordered sequence of modules under `src/pokemon_go_collection/migrations/`, each exposing `upgrade(conn)`. At every start, the runner (`migrate.py`) applies, in name order and in one transaction, the modules the `schema_migration` table does not record yet, and records them there; a database that already holds data is backed up first (see *Backups*). Its tables:

- `POKEMON_ENTRY` — the catalog, one row per entry, with the base stats of its representative form when the game master has them, rebuilt by each refresh. Rows are updated in place, so an entry keeps its identifier from one refresh to the next.
- `CP_MULTIPLIER` — the CP multiplier of every level, whole and half, rebuilt by each refresh from the game master.
- `POKEMON_EVOLUTION` — the evolutions between entries, one row per (source, target) pair, rebuilt by each refresh.
- `SHUNDO` — the collection's shundos, one row per owned entry, referring to `POKEMON_ENTRY`.
- `CATALOG_REFRESH` — one row per refresh, with the game master timestamp it used and its outcome.
- `BACKUP_EVENT` — one row per backup taken.
- `SPAWN_WATCH_CONFIG`, `SPAWN_CHECK`, `SPAWN_ALERT` — the spawn watch's settings and records, described in [spawn_watch.md](spawn_watch.md), *Storage*.

A refresh whose new catalog no longer holds an entry the collection owns fails, naming the entry, rather than deleting what the collection records. A form disappearing from the sources is a change to look into, and `data/form_overrides.csv` is where it is resolved.

## Backups

The SQLite backup API copies the database while the application runs, one automatic backup is taken per day when the application starts, retention keeps the last 30 daily, 12 monthly and 5 yearly automatic backups, and a backup taken before applying migrations is never pruned. Manual backups are taken from the sidebar or the CLI.

## Data refresh

A refresh brings the catalog up to date with its sources:

1. Pull the game master repository (`git pull --ff-only`).
2. Download the PvPoke game master and the LeekDuck shiny data, replacing their snapshots.
3. Rebuild the catalog from the sources.
4. Download the icons missing from the cache.
5. Write the catalog, with each entry's icon and base stats, to `POKEMON_ENTRY`, and the CP multipliers to `CP_MULTIPLIER`, in one transaction.
6. Record the refresh in `CATALOG_REFRESH`.

A source that cannot be reached (no network, a site down) leaves its last snapshot in use, and the refresh records a warning; a refresh with no snapshot at all to fall back on fails.

The application runs a refresh when it starts and the last successful one is older than the refresh period (7 days by default); after a failed attempt, it waits an hour before trying again. A refresh is also started from the sidebar, or with the CLI (`pgcollection-refresh`).

## The icon grid

Marking a shundo is a click on the Pokémon's icon. Streamlit's own widgets cannot do this at the scale of the catalog: an image is not clickable, and over a thousand checkboxes would redraw the whole page at every click. The grid is therefore a Streamlit component (`st.components.v2`): HTML, CSS and JavaScript held in the repository, with no frontend build step.

- Python passes the component the entries to show, grouped and ordered, with their state and icon URL.
- A click on a markable icon toggles it in the browser immediately. The component then sends Python the ownership asked for every entry clicked since the page was loaded, and Python makes `SHUNDO` match it. Sending the whole mapping rather than the last click is what keeps rapid clicks safe: Streamlit may coalesce several events into one rerun, and the mapping still holds each of them.
- The tab redraws inside a Streamlit fragment, so a click does not rerun the rest of the page.

The tab around the grid holds a filter (all, missing, owned), a search on names, and the count of owned and markable entries per region.
