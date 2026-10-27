# Pokémon GO Collection Utils

A local application to record and monitor the state of a Pokémon GO collection, starting with shundos: which Pokémon the collection holds as a shiny with perfect IVs, and which it still lacks. Built with Python, SQLite and Streamlit.

## Documentation

- [docs/product_requirements.md](docs/product_requirements.md) — the goal, and the requirements and constraints the design answers.
- [docs/catalog.md](docs/catalog.md) — which Pokémon the application lists, how they are grouped and ordered, and where their release statuses come from.
- [docs/architecture.md](docs/architecture.md) — modules, storage, backups, data refresh, and the icon grid.
- [docs/costumes.md](docs/costumes.md) — the costumed Pokémon: how their sources are matched, and where their release dates come from.
- [docs/data_sources.md](docs/data_sources.md) — the external sources about Pokémon GO: where each is, how it names a Pokémon, what it holds and lacks.
- [docs/game_data_extraction.md](docs/game_data_extraction.md) — a plan for reading the game's own files: what they can replace among the sources, what they cannot, and what to check before building it.
- [docs/spawn_watch.md](docs/spawn_watch.md) — the Discord alerts for shundos spawning now, and how they use pogocoordinates.com.
- [docs/pvp_ranks.md](docs/pvp_ranks.md) — the PvP concepts (leagues, stat product, ranks) and the PvP ranks tab.

## Requirements

- [uv](https://docs.astral.sh/uv/).
- Google Chrome, for logging in to pogocoordinates.com from the Spawn watch tab.

## Running

```bash
uv sync
uv run streamlit run run_app.py
```
