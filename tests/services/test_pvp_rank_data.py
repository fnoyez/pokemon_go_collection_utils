from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.services import pvp_rank_data as pvp_rank_data_m
from pokemon_go_collection.services import refresh as refresh_m


def test_load_rankable_pokemons_leaves_out_entries_without_stats(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry("AZUMARILL", 184, 0, (112, 152, 225)),
                make_entry("UNRELEASED", 1100, 1, None),
            ],
            {"AZUMARILL": None, "UNRELEASED": None},
        )

    assert pvp_rank_data_m.load_rankable_pokemons(db_file_path) == [
        pvp_rank_data_m.RankablePokemon("AZUMARILL", "Azumarill", (112, 152, 225))
    ]


def make_entry(entry_id, dex_number, display_order, base_stats):
    return catalog_m.CatalogEntry(
        entry_id=entry_id,
        dex_number=dex_number,
        name=entry_id.capitalize(),
        form_ids=(entry_id,),
        form_suffixes=(None,),
        region=regions_m.Region.KANTO,
        is_variant=False,
        display_order=display_order,
        pokemon_class=None,
        base_stats=base_stats,
        is_baby=False,
        evolution_target_entry_ids=(),
        is_released=True,
        shiny_release_date=None,
    )


def test_load_rankable_pokemons_orders_by_dex_number_then_catalog_order(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry("RAICHU", 26, 25, (201, 154, 155)),
                make_entry("MEOWTH", 52, 51, (92, 78, 120)),
                make_entry("RAICHU_ALOLA", 26, 919, (201, 156, 155)),
            ],
            {"RAICHU": None, "MEOWTH": None, "RAICHU_ALOLA": None},
        )

    pokemons = pvp_rank_data_m.load_rankable_pokemons(db_file_path)

    assert [pokemon.entry_id for pokemon in pokemons] == [
        "RAICHU",
        "RAICHU_ALOLA",
        "MEOWTH",
    ]


def test_load_cp_multipliers_reads_what_a_refresh_writes(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    cp_multipliers = {1.0: 0.094, 1.5: 0.1351374318, 2.0: 0.16639787}
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_cp_multipliers(conn, cp_multipliers)

    assert pvp_rank_data_m.load_cp_multipliers(db_file_path) == cp_multipliers
