"""The PvP rank computation, as docs/pvp_ranks.md describes it."""

import enum
import itertools
import math
import re

import numpy as np
import pandas as pd


class League(enum.Enum):
    """A PvP league, valued by its CP cap."""

    LITTLE_CUP = 500
    GREAT_LEAGUE = 1500
    ULTRA_LEAGUE = 2500


def build_cp_multipliers(whole_level_cp_multipliers):
    """Return the CP multiplier of every level, whole and half, keyed by level.

    `whole_level_cp_multipliers` holds those of the whole levels, level 1 first.
    """
    cp_multipliers = {
        float(level): multiplier
        for level, multiplier in enumerate(whole_level_cp_multipliers, start=1)
    }
    for level, (multiplier, next_multiplier) in enumerate(
        itertools.pairwise(whole_level_cp_multipliers), start=1
    ):
        if level <= 40:
            half_level_multiplier = math.sqrt((multiplier**2 + next_multiplier**2) / 2)
        else:
            half_level_multiplier = (multiplier + next_multiplier) / 2
        cp_multipliers[level + 0.5] = half_level_multiplier
    return dict(sorted(cp_multipliers.items()))


def find_reachable_levels(level_bonus, includes_half_levels_above_50=True):
    """Return the levels a specimen can be at, with a bonus of `level_bonus` levels."""
    # Level 50 is the game's power-up limit, not a setting.
    levels = [1 + index / 2 for index in range(99)]
    for index in range(1, 2 * level_bonus + 1):
        level = 50 + index / 2
        if includes_half_levels_above_50 or level.is_integer():
            levels.append(level)
    return levels


def rank_iv_spreads(
    base_stats, cp_multipliers, max_cp, levels, min_iv=0, max_iv=15, decimals_nb=5
):
    """Return the IV spreads of the IV range, each at its best level under `max_cp`, by rank.

    `cp_multipliers` maps each level to its CP multiplier, and `levels` are the
    levels a specimen can be at.
    """
    base_attack, base_defense, base_stamina = base_stats
    ivs = np.arange(min_iv, max_iv + 1)
    # One row per IV spread, by attack IV, then defense IV, then stamina IV, and
    # one column per level.
    att_ivs, def_ivs, sta_ivs = (
        iv_grid.reshape(-1, 1) for iv_grid in np.meshgrid(ivs, ivs, ivs, indexing="ij")
    )
    reachable_levels = np.array(
        [level for level in cp_multipliers if level in set(levels)]
    )
    level_cp_multipliers = np.array(
        [cp_multipliers[level] for level in reachable_levels]
    )
    attacks = np.round((base_attack + att_ivs) * level_cp_multipliers, decimals_nb)
    defenses = np.round((base_defense + def_ivs) * level_cp_multipliers, decimals_nb)
    unfloored_staminas = (base_stamina + sta_ivs) * level_cp_multipliers
    hps = np.floor(unfloored_staminas).astype(int)
    cps = np.floor(
        np.maximum(
            10,
            0.1
            * attacks
            * np.sqrt(defenses * np.round(unfloored_staminas, decimals_nb)),
        )
    ).astype(int)
    stat_products = attacks * defenses * hps

    # The best level of a spread is the one of highest stat product under the
    # cap, the lowest of several equal ones.
    is_under_cap = cps <= max_cp
    best_level_indexes = np.where(is_under_cap, stat_products, -np.inf).argmax(axis=1)
    best_stat_products = np.take_along_axis(
        stat_products, best_level_indexes.reshape(-1, 1), axis=1
    ).ravel()
    iv_sums = (att_ivs + def_ivs + sta_ivs).ravel()
    # The sort is stable, so spreads equal in both keys stay in IV order.
    spread_indexes = np.lexsort((-iv_sums, -best_stat_products))
    # A spread above the cap at every level has no rank.
    spread_indexes = spread_indexes[is_under_cap.any(axis=1)[spread_indexes]]
    level_indexes = best_level_indexes[spread_indexes]
    spread_stat_products = stat_products[spread_indexes, level_indexes]
    return pd.DataFrame(
        {
            "Level": reachable_levels[level_indexes],
            "CP": cps[spread_indexes, level_indexes],
            "IVs": [
                f"{att_iv}/{def_iv}/{sta_iv}"
                for att_iv, def_iv, sta_iv in zip(
                    att_ivs.ravel()[spread_indexes],
                    def_ivs.ravel()[spread_indexes],
                    sta_ivs.ravel()[spread_indexes],
                    strict=True,
                )
            ],
            "Att": attacks[spread_indexes, level_indexes],
            "Def": defenses[spread_indexes, level_indexes],
            "HP": hps[spread_indexes, level_indexes],
            "Stat Product": np.round(spread_stat_products / 1000, 3),
            "% Max Stat": np.round(
                100 * spread_stat_products / spread_stat_products[0], 2
            ),
            "% Max IV Sum": np.round(100 * iv_sums[spread_indexes] / 45).astype(int),
        },
        index=pd.Index(np.arange(1, len(spread_indexes) + 1), name="Rank"),
    )


def parse_iv_spreads(iv_spreads_text):
    """Return the IV spreads typed one per line, each as `attack defense stamina`."""
    iv_spreads = []
    for line in re.split(r"\n+", iv_spreads_text.strip()):
        ivs = line.split()
        if len(ivs) != 3 or not all(iv.isdigit() for iv in ivs):
            raise ValueError(f"Not an IV spread: '{line}'")
        iv_spreads.append(tuple(int(iv) for iv in ivs))
    return iv_spreads


def select_iv_spread_ranks(ranks_df, iv_spreads):
    """Return the rows of `ranks_df`, from `rank_iv_spreads`, of the IV spreads given."""
    iv_spread_texts = [
        "/".join(str(iv) for iv in iv_spread) for iv_spread in iv_spreads
    ]
    return ranks_df[ranks_df["IVs"].isin(iv_spread_texts)]
