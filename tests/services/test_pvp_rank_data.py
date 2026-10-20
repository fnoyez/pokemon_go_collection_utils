import pytest

from pokemon_go_collection import catalog as catalog_m
from pokemon_go_collection import db as db_m
from pokemon_go_collection import migrate as migrate_m
from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.services import pvp_rank_data as pvp_rank_data_m
from pokemon_go_collection.services import refresh as refresh_m
from pokemon_go_collection.sources import game_master as game_master_m


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
        pvp_rank_data_m.RankablePokemon(
            "AZUMARILL", None, None, 184, "Azumarill", (112, 152, 225)
        )
    ]


def make_entry(
    entry_id,
    dex_number,
    display_order,
    base_stats,
    temporary_evolutions=(),
    battle_forms=(),
    name=None,
    form_ids=None,
):
    return catalog_m.CatalogEntry(
        entry_id=entry_id,
        dex_number=dex_number,
        name=name or entry_id.capitalize(),
        form_ids=form_ids or (entry_id,),
        form_suffixes=(None,),
        region=regions_m.Region.KANTO,
        is_variant=False,
        display_order=display_order,
        pokemon_class=None,
        base_stats=base_stats,
        temporary_evolutions=temporary_evolutions,
        battle_forms=battle_forms,
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


def test_load_rankable_pokemons_lists_temporary_evolutions_after_their_entry(
    tmp_path,
):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry(
                    "CHARIZARD",
                    6,
                    5,
                    (223, 173, 186),
                    temporary_evolutions=(
                        game_master_m.TemporaryEvolution("MEGA_Y", (319, 212, 186)),
                        game_master_m.TemporaryEvolution("MEGA_X", (273, 213, 186)),
                    ),
                ),
                make_entry("SQUIRTLE", 7, 6, (94, 121, 127)),
                make_entry(
                    "KYOGRE",
                    382,
                    381,
                    (270, 228, 205),
                    temporary_evolutions=(
                        game_master_m.TemporaryEvolution("PRIMAL", (353, 268, 205)),
                    ),
                ),
            ],
            {"CHARIZARD": None, "SQUIRTLE": None, "KYOGRE": None},
        )

    assert pvp_rank_data_m.load_rankable_pokemons(db_file_path) == [
        pvp_rank_data_m.RankablePokemon(
            "CHARIZARD", None, None, 6, "Charizard", (223, 173, 186)
        ),
        pvp_rank_data_m.RankablePokemon(
            "CHARIZARD", "MEGA_X", None, 6, "Mega Charizard X", (273, 213, 186)
        ),
        pvp_rank_data_m.RankablePokemon(
            "CHARIZARD", "MEGA_Y", None, 6, "Mega Charizard Y", (319, 212, 186)
        ),
        pvp_rank_data_m.RankablePokemon(
            "SQUIRTLE", None, None, 7, "Squirtle", (94, 121, 127)
        ),
        pvp_rank_data_m.RankablePokemon(
            "KYOGRE", None, None, 382, "Kyogre", (270, 228, 205)
        ),
        pvp_rank_data_m.RankablePokemon(
            "KYOGRE", "PRIMAL", None, 382, "Primal Kyogre", (353, 268, 205)
        ),
    ]


def test_load_rankable_pokemons_lists_battle_forms_after_their_entry(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry(
                    "MINIOR",
                    774,
                    0,
                    (116, 194, 155),
                    battle_forms=(
                        catalog_m.BattleForm(
                            "MINIOR_BLUE", "Minior (Blue)", (218, 131, 155)
                        ),
                        catalog_m.BattleForm(
                            "MINIOR_GREEN", "Minior (Green)", (218, 131, 155)
                        ),
                    ),
                ),
                make_entry("KOMALA", 775, 1, (216, 165, 163)),
            ],
            {"MINIOR": None, "KOMALA": None},
        )

    assert pvp_rank_data_m.load_rankable_pokemons(db_file_path) == [
        pvp_rank_data_m.RankablePokemon(
            "MINIOR", None, None, 774, "Minior", (116, 194, 155)
        ),
        pvp_rank_data_m.RankablePokemon(
            "MINIOR", None, "MINIOR_BLUE", 774, "Minior (Blue)", (218, 131, 155)
        ),
        pvp_rank_data_m.RankablePokemon(
            "MINIOR", None, "MINIOR_GREEN", 774, "Minior (Green)", (218, 131, 155)
        ),
        pvp_rank_data_m.RankablePokemon(
            "KOMALA", None, None, 775, "Komala", (216, 165, 163)
        ),
    ]


def test_load_evolution_tree_data_splits_names_into_species_and_form(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_catalog(
            conn,
            [
                make_entry(
                    "ROCKRUFF",
                    744,
                    0,
                    (117, 78, 128),
                    form_ids=("ROCKRUFF_NORMAL", "ROCKRUFF"),
                ),
                make_entry(
                    "LYCANROC",
                    745,
                    1,
                    (231, 140, 181),
                    form_ids=("LYCANROC", "LYCANROC_MIDDAY"),
                ),
                make_entry(
                    "LYCANROC_MIDNIGHT",
                    745,
                    2,
                    (218, 152, 198),
                    name="Lycanroc (Midnight)",
                ),
                make_entry("MEW", 151, 3, (210, 210, 225)),
            ],
            {
                "ROCKRUFF": None,
                "LYCANROC": None,
                "LYCANROC_MIDNIGHT": None,
                "MEW": None,
            },
        )
        conn.execute(
            """
            INSERT INTO pokemon_evolution (source_entry_id, target_entry_id)
            VALUES ('ROCKRUFF', 'LYCANROC'), ('ROCKRUFF', 'LYCANROC_MIDNIGHT')
            """
        )

    entries, evolution_edges = pvp_rank_data_m.load_evolution_tree_data(db_file_path)

    assert [
        (entry.entry_id, entry.species_name, entry.form_label) for entry in entries
    ] == [
        ("MEW", "Mew", None),
        ("ROCKRUFF", "Rockruff", "Normal"),
        ("LYCANROC", "Lycanroc", "Midday"),
        ("LYCANROC_MIDNIGHT", "Lycanroc", "Midnight"),
    ]
    assert sorted(evolution_edges) == [
        ("ROCKRUFF", "LYCANROC"),
        ("ROCKRUFF", "LYCANROC_MIDNIGHT"),
    ]


def test_load_cp_multipliers_reads_what_a_refresh_writes(tmp_path):
    db_file_path = tmp_path / "collection.sqlite"
    migrate_m.init_db(db_file_path)
    cp_multipliers = {1.0: 0.094, 1.5: 0.1351374318, 2.0: 0.16639787}
    with db_m.db_conn(db_file_path) as conn:
        refresh_m.write_cp_multipliers(conn, cp_multipliers)

    assert pvp_rank_data_m.load_cp_multipliers(db_file_path) == cp_multipliers


def make_pokemon(name):
    return pvp_rank_data_m.RankablePokemon(name.upper(), None, None, 0, name, (1, 1, 1))


POKEMONS = [
    make_pokemon("Minior"),
    make_pokemon("Minior (Blue)"),
    make_pokemon("Flabébé (Red)"),
    make_pokemon("Raichu"),
]


def get_find_pokemons_by_name_test_data():
    test_cases = [
        {
            "id": "substring-any-case",
            "name_part": "mINIo",
            "expected_names": ["Minior", "Minior (Blue)"],
        },
        {
            "id": "form-label",
            "name_part": "blue",
            "expected_names": ["Minior (Blue)"],
        },
        {
            "id": "accents-ignored",
            "name_part": "flabebe",
            "expected_names": ["Flabébé (Red)"],
        },
        {
            "id": "accented-search-text",
            "name_part": "Flabé",
            "expected_names": ["Flabébé (Red)"],
        },
        {
            "id": "surrounding-spaces-ignored",
            "name_part": " raichu ",
            "expected_names": ["Raichu"],
        },
        {
            "id": "nothing-found",
            "name_part": "pikachu",
            "expected_names": [],
        },
    ]

    return [
        pytest.param(
            test_case["name_part"], test_case["expected_names"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "name_part,expected_names", get_find_pokemons_by_name_test_data()
)
def test_find_pokemons_by_name(name_part, expected_names):
    found_pokemons = pvp_rank_data_m.find_pokemons_by_name(POKEMONS, name_part)

    assert [pokemon.name for pokemon in found_pokemons] == expected_names
