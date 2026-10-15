import datetime

from pokemon_go_collection.sources import game_master as game_master_m

TIMESTAMP = datetime.datetime(2026, 8, 28, 7, 35, tzinfo=datetime.timezone.utc)


def test_parse_game_master_reads_the_temporary_evolutions_having_stats():
    templates = [
        {
            "templateId": "V0006_POKEMON_CHARIZARD",
            "data": {
                "pokemonSettings": {
                    "pokemonId": "CHARIZARD",
                    "type": "POKEMON_TYPE_FIRE",
                    "type2": "POKEMON_TYPE_FLYING",
                    "stats": {
                        "baseStamina": 186,
                        "baseAttack": 223,
                        "baseDefense": 173,
                    },
                    "tempEvoOverrides": [
                        {
                            "tempEvoId": "TEMP_EVOLUTION_MEGA_X",
                            "stats": {
                                "baseStamina": 186,
                                "baseAttack": 273,
                                "baseDefense": 213,
                            },
                        },
                        {
                            "tempEvoId": "TEMP_EVOLUTION_MEGA_Y",
                            "stats": {
                                "baseStamina": 186,
                                "baseAttack": 319,
                                "baseDefense": 212,
                            },
                        },
                        {"camera": {"cylinderRadiusM": 0.5}},
                    ],
                }
            },
        },
        {
            "templateId": "PLAYER_LEVEL_SETTINGS",
            "data": {"playerLevel": {"cpMultiplier": [0.094, 0.16639787]}},
        },
    ]

    game_master = game_master_m.parse_game_master(templates, TIMESTAMP)

    assert game_master.forms[0].stats == (223, 173, 186)
    assert game_master.forms[0].temporary_evolutions == (
        game_master_m.TemporaryEvolution("MEGA_X", (273, 213, 186)),
        game_master_m.TemporaryEvolution("MEGA_Y", (319, 212, 186)),
    )
