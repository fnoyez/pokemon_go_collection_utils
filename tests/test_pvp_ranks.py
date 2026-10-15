import pytest

import pokemon_go_collection.pvp_ranks as pvp_ranks_m

# The game master's CP multipliers of levels 1 to 55.
WHOLE_LEVEL_CP_MULTIPLIERS = (
    0.094, 0.16639787, 0.21573247, 0.25572005, 0.29024988, 0.3210876, 0.34921268,
    0.3752356, 0.39956728, 0.4225, 0.44310755, 0.4627984, 0.48168495, 0.49985844,
    0.51739395, 0.5343543, 0.5507927, 0.5667545, 0.5822789, 0.5974, 0.6121573,
    0.6265671, 0.64065295, 0.65443563, 0.667934, 0.6811649, 0.69414365, 0.7068842,
    0.7193991, 0.7317, 0.7377695, 0.74378943, 0.74976104, 0.7556855, 0.76156384,
    0.76739717, 0.7731865, 0.77893275, 0.784637, 0.7903, 0.7953, 0.8003, 0.8053,
    0.8103, 0.8153, 0.8203, 0.8253, 0.8303, 0.8353, 0.8403, 0.8453, 0.8503, 0.8553,
    0.8603, 0.8653,
)  # fmt: skip
CP_MULTIPLIERS = pvp_ranks_m.build_cp_multipliers(WHOLE_LEVEL_CP_MULTIPLIERS)
AZUMARILL_BASE_STATS = (112, 152, 225)
MELMETAL_BASE_STATS = (226, 190, 264)
# A Pokémon reaching the Great League cap beyond level 50 only.
LATE_BASE_STATS = (121, 131, 163)


def get_build_cp_multipliers_test_data():
    test_cases = [
        {"id": "whole-level", "level": 1.0, "expected_multiplier": 0.094},
        {
            "id": "half-level-up-to-40",
            "level": 1.5,
            "expected_multiplier": 0.1351374318,
        },
        {"id": "half-level-40", "level": 40.5, "expected_multiplier": 0.7928039417},
        {"id": "half-level-from-41", "level": 41.5, "expected_multiplier": 0.7978},
        {"id": "half-level-above-50", "level": 50.5, "expected_multiplier": 0.8428},
        {"id": "last-whole-level", "level": 55.0, "expected_multiplier": 0.8653},
    ]

    return [
        pytest.param(
            test_case["level"], test_case["expected_multiplier"], id=test_case["id"]
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "level,expected_multiplier", get_build_cp_multipliers_test_data()
)
def test_build_cp_multipliers(level, expected_multiplier):
    assert CP_MULTIPLIERS[level] == pytest.approx(expected_multiplier, abs=1e-9)


def get_find_reachable_levels_test_data():
    test_cases = [
        {
            "id": "no-bonus",
            "level_bonus": 0,
            "includes_half_levels_above_50": True,
            "expected_levels_nb": 99,
            "expected_last_levels": [49.0, 49.5, 50.0],
        },
        {
            "id": "best-buddy",
            "level_bonus": 1,
            "includes_half_levels_above_50": True,
            "expected_levels_nb": 101,
            "expected_last_levels": [50.0, 50.5, 51.0],
        },
        {
            "id": "best-buddy-whole-levels-above-50",
            "level_bonus": 1,
            "includes_half_levels_above_50": False,
            "expected_levels_nb": 100,
            "expected_last_levels": [49.5, 50.0, 51.0],
        },
        {
            "id": "both-bonuses-whole-levels-above-50",
            "level_bonus": 3,
            "includes_half_levels_above_50": False,
            "expected_levels_nb": 102,
            "expected_last_levels": [50.0, 51.0, 52.0, 53.0],
        },
    ]

    return [
        pytest.param(
            test_case["level_bonus"],
            test_case["includes_half_levels_above_50"],
            test_case["expected_levels_nb"],
            test_case["expected_last_levels"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "level_bonus,includes_half_levels_above_50,expected_levels_nb,expected_last_levels",
    get_find_reachable_levels_test_data(),
)
def test_find_reachable_levels(
    level_bonus, includes_half_levels_above_50, expected_levels_nb, expected_last_levels
):
    levels = pvp_ranks_m.find_reachable_levels(
        level_bonus, includes_half_levels_above_50=includes_half_levels_above_50
    )

    assert len(levels) == expected_levels_nb
    assert levels[0] == 1.0
    assert levels[-len(expected_last_levels) :] == expected_last_levels


def get_rank_iv_spreads_test_data():
    test_cases = [
        {
            "id": "great-league",
            "base_stats": AZUMARILL_BASE_STATS,
            "max_cp": 1500,
            "level_bonus": 0,
            "includes_half_levels_above_50": True,
            "min_iv": 0,
            "expected_spreads_nb": 4096,
            "expected_first_ranks": [
                ("0/15/15", 45.5, 1499),
                ("0/14/11", 46.5, 1500),
                ("0/15/12", 46.0, 1499),
            ],
        },
        {
            "id": "great-league-from-raids",
            "base_stats": AZUMARILL_BASE_STATS,
            "max_cp": 1500,
            "level_bonus": 0,
            "includes_half_levels_above_50": True,
            "min_iv": 10,
            "expected_spreads_nb": 216,
            "expected_first_ranks": [
                ("10/15/14", 39.0, 1500),
                ("10/14/15", 39.0, 1499),
            ],
        },
        {
            "id": "ultra-league",
            "base_stats": MELMETAL_BASE_STATS,
            "max_cp": 2500,
            "level_bonus": 0,
            "includes_half_levels_above_50": True,
            "min_iv": 0,
            "expected_spreads_nb": 4096,
            "expected_first_ranks": [
                ("0/13/15", 26.0, 2495),
                ("0/14/14", 26.0, 2497),
                ("1/12/15", 26.0, 2500),
            ],
        },
        {
            "id": "best-buddy",
            "base_stats": LATE_BASE_STATS,
            "max_cp": 1500,
            "level_bonus": 1,
            "includes_half_levels_above_50": True,
            "min_iv": 0,
            "expected_spreads_nb": 4096,
            "expected_first_ranks": [
                ("10/15/15", 50.5, 1500),
                ("9/15/15", 51.0, 1497),
            ],
        },
        {
            "id": "best-buddy-whole-levels-above-50",
            "base_stats": LATE_BASE_STATS,
            "max_cp": 1500,
            "level_bonus": 1,
            "includes_half_levels_above_50": False,
            "min_iv": 0,
            "expected_spreads_nb": 4096,
            "expected_first_ranks": [
                ("9/15/15", 51.0, 1497),
                ("10/15/13", 51.0, 1500),
            ],
        },
    ]

    return [
        pytest.param(
            test_case["base_stats"],
            test_case["max_cp"],
            test_case["level_bonus"],
            test_case["includes_half_levels_above_50"],
            test_case["min_iv"],
            test_case["expected_spreads_nb"],
            test_case["expected_first_ranks"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "base_stats,max_cp,level_bonus,includes_half_levels_above_50,min_iv,"
    "expected_spreads_nb,expected_first_ranks",
    get_rank_iv_spreads_test_data(),
)
def test_rank_iv_spreads(
    base_stats,
    max_cp,
    level_bonus,
    includes_half_levels_above_50,
    min_iv,
    expected_spreads_nb,
    expected_first_ranks,
):
    levels = pvp_ranks_m.find_reachable_levels(
        level_bonus, includes_half_levels_above_50=includes_half_levels_above_50
    )

    ranks_df = pvp_ranks_m.rank_iv_spreads(
        base_stats, CP_MULTIPLIERS, max_cp, levels, min_iv=min_iv
    )

    assert len(ranks_df) == expected_spreads_nb
    assert list(ranks_df.index[:3]) == [1, 2, 3]
    first_ranks_df = ranks_df.head(len(expected_first_ranks))
    assert (
        list(zip(first_ranks_df["IVs"], first_ranks_df["Level"], first_ranks_df["CP"]))
        == expected_first_ranks
    )
