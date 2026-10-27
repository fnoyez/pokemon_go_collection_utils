import datetime

import pytest

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import costumes as costumes_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.services import refresh as refresh_m
from pokemon_go_collection.services import shundos as shundos_m

TODAY = datetime.date(2026, 10, 10)


def test_write_catalog_keeps_owned_entries(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    shiny_release_date = datetime.date(2020, 1, 1)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry("BULBASAUR", 0, shiny_release_date=shiny_release_date),
                make_entry("IVYSAUR", 1),
            ],
            {"BULBASAUR": "BULBASAUR.shiny.png", "IVYSAUR": None},
        )
    shundos_m.apply_desired_ownership(
        db_file_path,
        shundos_m.Board.SHUNDOS,
        {"BULBASAUR": True, "IVYSAUR": True},
        TODAY,
    )

    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [make_entry("BULBASAUR", 0, shiny_release_date=shiny_release_date)],
            {"BULBASAUR": "BULBASAUR.shiny.png"},
        )
    board_entries = shundos_m.load_board_entries(
        db_file_path, shundos_m.Board.SHUNDOS, TODAY
    )

    assert [(entry.entry_id, entry.state) for entry in board_entries] == [
        ("BULBASAUR", shundos_m.EntryState.OWNED)
    ]


def make_entry(entry_id, display_order, shiny_release_date=None):
    return catalog_m.CatalogEntry(
        entry_id=entry_id,
        dex_number=display_order + 1,
        name=entry_id.capitalize(),
        form_ids=(entry_id,),
        form_suffixes=(None,),
        region=regions_m.Region.KANTO,
        is_variant=False,
        display_order=display_order,
        pokemon_class=None,
        base_stats=None,
        temporary_evolutions=(),
        battle_forms=(),
        is_baby=False,
        evolution_target_entry_ids=(),
        is_released=True,
        shiny_release_date=shiny_release_date,
    )


def test_write_catalog_refuses_to_drop_owned_entry(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [make_entry("BULBASAUR", 0, shiny_release_date=datetime.date(2020, 1, 1))],
            {"BULBASAUR": None},
        )
    shundos_m.apply_desired_ownership(
        db_file_path, shundos_m.Board.SHUNDOS, {"BULBASAUR": True}, TODAY
    )

    with pytest.raises(refresh_m.CatalogRefreshError):
        with db_m.db_conn(db_file_path) as conn:
            refresh_m.write_catalog(conn, [make_entry("IVYSAUR", 0)], {"IVYSAUR": None})


def test_write_costumed_pokemons_moves_a_shundo_once_its_costume_is_named(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    shiny_release_date = datetime.date(2026, 10, 1)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_costumed_pokemons(
            conn,
            [
                make_costumed_pokemon(
                    "ZUBAT.TopHat",
                    costumes_m.CostumedPokemonKey(41, None, None, "TopHat"),
                    shiny_release_date,
                )
            ],
            {"ZUBAT.TopHat": None},
            [],
        )
    shundos_m.apply_desired_ownership(
        db_file_path, shundos_m.Board.COSTUMED_SHUNDOS, {"ZUBAT.TopHat": True}, TODAY
    )

    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_costumed_pokemons(
            conn,
            [
                make_costumed_pokemon(
                    "ZUBAT.HALLOWEEN_2026",
                    costumes_m.CostumedPokemonKey(41, None, "HALLOWEEN_2026"),
                    shiny_release_date,
                )
            ],
            {"ZUBAT.HALLOWEEN_2026": None},
            [],
        )
    board_entries = shundos_m.load_board_entries(
        db_file_path, shundos_m.Board.COSTUMED_SHUNDOS, TODAY
    )

    assert [(entry.entry_id, entry.state) for entry in board_entries] == [
        ("ZUBAT.HALLOWEEN_2026", shundos_m.EntryState.OWNED)
    ]


def make_costumed_pokemon(costumed_pokemon_id, key, shiny_release_date):
    return costumes_m.CostumedPokemon(
        costumed_pokemon_id=costumed_pokemon_id,
        key=key,
        name="Zubat (Top hat)",
        release_date=datetime.date(2026, 10, 1),
        shiny_release_date=shiny_release_date,
        pogo_assets_icon_file_names=None,
        leekduck_asset_name=None,
        bulbapedia_codes=("TopHat",),
        costume_year=2026,
    )


def test_write_costumed_pokemons_refuses_to_drop_an_owned_one(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    key = costumes_m.CostumedPokemonKey(25, None, "HOLIDAY_2016")
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_costumed_pokemons(
            conn,
            [
                make_costumed_pokemon(
                    "PIKACHU.HOLIDAY_2016", key, datetime.date(2016, 12, 25)
                )
            ],
            {"PIKACHU.HOLIDAY_2016": None},
            [],
        )
    shundos_m.apply_desired_ownership(
        db_file_path,
        shundos_m.Board.COSTUMED_SHUNDOS,
        {"PIKACHU.HOLIDAY_2016": True},
        TODAY,
    )

    with pytest.raises(refresh_m.CatalogRefreshError):
        with db_m.db_conn(db_file_path) as conn:
            refresh_m.write_costumed_pokemons(conn, [], {}, [])
