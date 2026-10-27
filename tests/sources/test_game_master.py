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


def test_parse_game_master_names_the_forms_given_by_their_number():
    stats = {"baseStamina": 120, "baseAttack": 83, "baseDefense": 73}
    templates = [
        {
            "templateId": "FORMS_V0041_POKEMON_ZUBAT",
            "data": {
                "formSettings": {
                    "pokemon": "ZUBAT",
                    "forms": [
                        {"form": "ZUBAT_NORMAL"},
                        {"form": 3362, "isCostume": True},
                    ],
                }
            },
        },
        {
            "templateId": "V0041_POKEMON_ZUBAT_HALLOWEEN_2026_01",
            "data": {
                "pokemonSettings": {
                    "pokemonId": "ZUBAT",
                    "form": 3362,
                    "type": "POKEMON_TYPE_POISON",
                    "stats": stats,
                    "evolutionBranch": [{"evolution": "GOLBAT", "form": 3363}],
                }
            },
        },
        {
            "templateId": "V0042_POKEMON_GOLBAT_HALLOWEEN_2026_01",
            "data": {
                "pokemonSettings": {
                    "pokemonId": "GOLBAT",
                    "form": 3363,
                    "type": "POKEMON_TYPE_POISON",
                    "stats": stats,
                }
            },
        },
    ]

    game_master = game_master_m.parse_game_master(templates, TIMESTAMP)

    assert game_master.costume_form_ids == frozenset({"ZUBAT_HALLOWEEN_2026_01"})
    assert [form.form_id for form in game_master.forms] == [
        "ZUBAT_HALLOWEEN_2026_01",
        "GOLBAT_HALLOWEEN_2026_01",
    ]
    assert game_master.forms[0].evolutions == (("GOLBAT", "GOLBAT_HALLOWEEN_2026_01"),)
