# Pokémon GO Collection Utils

A local application to record and monitor the state of a Pokémon GO collection, starting with shundos: which Pokémon the collection holds as a shiny with perfect IVs, and which it still lacks. Built with Python, SQLite and Streamlit.

## Documentation

- [docs/product_requirements.md](docs/product_requirements.md) — the goal, and the requirements and constraints the design answers.
- [docs/catalog.md](docs/catalog.md) — which Pokémon the application lists, how they are grouped and ordered, and where their release statuses come from.
- [docs/architecture.md](docs/architecture.md) — modules, storage, backups, data refresh, and the icon grid.

## Requirements

- [uv](https://docs.astral.sh/uv/).
- The [`game_masters`](https://github.com/PokeMiners/game_masters) repository cloned next to this one, as `../game_masters`.

## Running

```bash
uv sync
uv run streamlit run run_app.py
```
