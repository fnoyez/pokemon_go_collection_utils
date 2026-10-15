import textwrap

import pytest

import pokemon_go_collection.rank_names as rank_names_m
import pokemon_go_collection.services.pvp_rank_data as pvp_rank_data_m


def make_entry(
    entry_id,
    dex_number,
    name,
    base_stats,
    form_label=None,
    is_variant=False,
    is_baby=False,
):
    return rank_names_m.TreeEntry(
        entry_id=entry_id,
        dex_number=dex_number,
        name=name,
        species_name=name.split(" (")[0],
        form_label=form_label,
        is_variant=is_variant,
        is_baby=is_baby,
        base_stats=base_stats,
    )


# In catalog order.
ENTRIES = [
    make_entry("CHARIZARD", 6, "Charizard", (223, 173, 186)),
    make_entry("PIKACHU", 25, "Pikachu", (112, 96, 111)),
    make_entry("RAICHU", 26, "Raichu", (193, 151, 155)),
    make_entry(
        "RAICHU_ALOLA",
        26,
        "Raichu (Alolan)",
        (201, 154, 155),
        form_label="Alolan",
        is_variant=True,
    ),
    make_entry("SLOWPOKE", 79, "Slowpoke", (109, 98, 207)),
    make_entry("SLOWBRO", 80, "Slowbro", (177, 180, 216)),
    make_entry("RHYHORN", 111, "Rhyhorn", (140, 127, 190)),
    make_entry("RHYDON", 112, "Rhydon", (222, 171, 233)),
    make_entry("PICHU", 172, "Pichu", (77, 53, 85), is_baby=True),
    make_entry("SLOWKING", 199, "Slowking", (177, 180, 216)),
    make_entry("RHYPERIOR", 464, "Rhyperior", (241, 190, 251)),
    make_entry("ROCKRUFF", 744, "Rockruff", (117, 78, 128), form_label="Normal"),
    make_entry(
        "ROCKRUFF_DUSK", 744, "Rockruff (Dusk)", (117, 78, 128), form_label="Dusk"
    ),
    make_entry("LYCANROC", 745, "Lycanroc", (231, 140, 181), form_label="Midday"),
    make_entry(
        "LYCANROC_MIDNIGHT",
        745,
        "Lycanroc (Midnight)",
        (218, 152, 198),
        form_label="Midnight",
    ),
    make_entry(
        "LYCANROC_DUSK", 745, "Lycanroc (Dusk)", (234, 139, 181), form_label="Dusk"
    ),
    make_entry("APPLIN", 840, "Applin", (71, 116, 120)),
    make_entry("FLAPPLE", 841, "Flapple", (214, 144, 172)),
    make_entry("APPLETUN", 842, "Appletun", (178, 146, 242)),
    make_entry("DIPPLIN", 1011, "Dipplin", (173, 184, 190)),
    make_entry("HYDRAPPLE", 1019, "Hydrapple", (216, 186, 235)),
]
EVOLUTION_EDGES = [
    ("PICHU", "PIKACHU"),
    ("PIKACHU", "RAICHU"),
    ("SLOWPOKE", "SLOWBRO"),
    ("SLOWPOKE", "SLOWKING"),
    ("RHYHORN", "RHYDON"),
    ("RHYDON", "RHYPERIOR"),
    ("ROCKRUFF", "LYCANROC"),
    ("ROCKRUFF", "LYCANROC_MIDNIGHT"),
    ("ROCKRUFF_DUSK", "LYCANROC_DUSK"),
    ("APPLIN", "FLAPPLE"),
    ("APPLIN", "APPLETUN"),
    ("APPLIN", "DIPPLIN"),
    ("DIPPLIN", "HYDRAPPLE"),
]


def make_pokemon(entry_id, temporary_evolution_id=None, name=None, base_stats=None):
    entry = next(entry for entry in ENTRIES if entry.entry_id == entry_id)
    return pvp_rank_data_m.RankablePokemon(
        entry_id,
        temporary_evolution_id,
        name or entry.name,
        base_stats or entry.base_stats,
    )


def get_build_evolution_tree_test_data():
    test_cases = [
        {
            "id": "line-from-its-last-stage",
            "pokemon": make_pokemon("RHYPERIOR"),
            "expected_groups": [
                [
                    ("Rhyperior", 0, None, False),
                    ("Rhydon", 1, None, False),
                    ("Rhyhorn", 2, None, True),
                ]
            ],
        },
        {
            "id": "branches-of-different-lengths",
            "pokemon": make_pokemon("DIPPLIN"),
            "expected_groups": [
                [("Flapple", 0, "Fl", False)],
                [("Appletun", 0, "Ap", False)],
                [("Hydrapple", 0, "Hy", False), ("Dipplin", 1, "Di", False)],
                [("Applin", 2, None, True)],
            ],
        },
        {
            "id": "forms-joined-and-equal-forms-one-member",
            "pokemon": make_pokemon("LYCANROC_DUSK"),
            "expected_groups": [
                [("Lycanroc", 0, "Md", False)],
                [("Lycanroc (Midnight)", 0, "Mn", False)],
                [("Lycanroc (Dusk)", 0, "Du", False)],
                [("Rockruff", 1, None, True)],
            ],
        },
        {
            "id": "same-first-letters",
            "pokemon": make_pokemon("SLOWPOKE"),
            "expected_groups": [
                [("Slowbro", 0, "Sb", False)],
                [("Slowking", 0, "Sk", False)],
                [("Slowpoke", 1, None, True)],
            ],
        },
        {
            "id": "baby-left-out-and-regional-form-apart",
            "pokemon": make_pokemon("RAICHU"),
            "expected_groups": [
                [("Raichu", 0, None, False), ("Pikachu", 1, None, False)]
            ],
        },
        {
            "id": "baby-alone",
            "pokemon": make_pokemon("PICHU"),
            "expected_groups": [[("Pichu", 0, None, True)]],
        },
        {
            "id": "regional-form-no-evolution-leads-to",
            "pokemon": make_pokemon("RAICHU_ALOLA"),
            "expected_groups": [[("Raichu (Alolan)", 0, None, False)]],
        },
        {
            "id": "mega-alone",
            "pokemon": make_pokemon(
                "CHARIZARD",
                temporary_evolution_id="MEGA_Y",
                name="Mega Charizard Y",
                base_stats=(319, 212, 186),
            ),
            "expected_groups": [[("Mega Charizard Y", 0, None, False)]],
        },
    ]

    return [
        pytest.param(
            test_case["pokemon"], test_case["expected_groups"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "pokemon,expected_groups", get_build_evolution_tree_test_data()
)
def test_build_evolution_tree(pokemon, expected_groups):
    groups = rank_names_m.build_evolution_tree(ENTRIES, EVOLUTION_EDGES, pokemon)

    assert [
        [
            (member.name, member.stages_nb, member.code, member.is_little_cup_eligible)
            for member in group
        ]
        for group in groups
    ] == expected_groups


def make_text(text):
    return textwrap.dedent(text).strip("\n")


def get_build_rank_names_text_test_data():
    test_cases = [
        {
            "id": "line",
            "pokemon": make_pokemon("RHYHORN"),
            "shows_evolved_little_cup": False,
            "expected_text": make_text(
                """
                Max lvl to be sure for PvPH trade: Lv23
                Max lvl to be sure for PvPS trade: Lv14
                Max lvl to be sure for PvPH- trade: Lv27
                Max lvl to be sure for PvPS- trade: Lv16
                Max lvl to be sure for PvPS-- trade: Lv33
                Max lvl to be sure for PvPCE trade: Lv10

                Max Lvl PvPH1 (0/14/14): Lv25
                Max Lvl PvPH1- (0/14/14): Lv29.5
                Max Lvl PvPS1 (0/14/14): Lv15
                Max Lvl PvPS1- (2/15/14): Lv17.5
                Max Lvl PvPS1-- (0/13/15): Lv41
                Max Lvl PvPCE1 (0/13/9): Lv12
                """
            ),
        },
        {
            "id": "line-with-little-cup-for-evolved",
            "pokemon": make_pokemon("RHYHORN"),
            "shows_evolved_little_cup": True,
            "expected_text": make_text(
                """
                Max lvl to be sure for PvPH trade: Lv23
                Max lvl to be sure for PvPS trade: Lv14
                Max lvl to be sure for PvPH- trade: Lv27
                Max lvl to be sure for PvPS- trade: Lv16
                Max lvl to be sure for PvPS-- trade: Lv33
                Max lvl to be sure for PvPCE trade: Lv4
                Max lvl to be sure for PvPCE- trade: Lv5
                Max lvl to be sure for PvPCE-- trade: Lv10

                Max Lvl PvPH1 (0/14/14): Lv25
                Max Lvl PvPH1- (0/14/14): Lv29.5
                Max Lvl PvPS1 (0/14/14): Lv15
                Max Lvl PvPS1- (2/15/14): Lv17.5
                Max Lvl PvPS1-- (0/13/15): Lv41
                Max Lvl PvPCE1 (0/3/4): Lv5.5
                Max Lvl PvPCE1- (4/15/15): Lv6
                Max Lvl PvPCE1-- (0/13/9): Lv12
                """
            ),
        },
        {
            "id": "branches",
            "pokemon": make_pokemon("ROCKRUFF"),
            "shows_evolved_little_cup": False,
            "expected_text": make_text(
                """
                Max lvl to be sure for PvPHMd trade: Lv35
                Max lvl to be sure for PvPSMd trade: Lv19
                Max lvl to be sure for PvPHMn trade: Lv33
                Max lvl to be sure for PvPSMn trade: Lv19
                Max lvl to be sure for PvPHDu trade: Lv34
                Max lvl to be sure for PvPSDu trade: Lv19
                Max lvl to be sure for PvPCE trade: Lv18

                Max Lvl PvPH1Md (0/14/14): Lv40
                Max Lvl PvPS1Md (0/14/14): Lv21
                Max Lvl PvPH1Mn (1/15/14): Lv38
                Max Lvl PvPS1Mn (0/15/14): Lv20.5
                Max Lvl PvPH1Du (0/15/14): Lv39
                Max Lvl PvPS1Du (2/15/15): Lv20.5
                Max Lvl PvPCE1 (0/13/15): Lv21
                """
            ),
        },
    ]

    return [
        pytest.param(
            test_case["pokemon"],
            test_case["shows_evolved_little_cup"],
            test_case["expected_text"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "pokemon,shows_evolved_little_cup,expected_text",
    get_build_rank_names_text_test_data(),
)
def test_build_rank_names_text(
    cp_multipliers, pokemon, shows_evolved_little_cup, expected_text
):
    groups = rank_names_m.build_evolution_tree(ENTRIES, EVOLUTION_EDGES, pokemon)

    text = rank_names_m.build_rank_names_text(
        cp_multipliers, groups, shows_evolved_little_cup
    )

    assert text == expected_text
