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
    ivs = list(range(min_iv, max_iv + 1))
    reachable_levels = [level for level in cp_multipliers if level in set(levels)]
    return (
        pd.MultiIndex.from_product(
            [ivs, ivs, ivs, reachable_levels],
            names=["att_iv", "def_iv", "sta_iv", "Level"],
        )
        .to_frame(index=False)
        .assign(
            **{
                "CP Multiplier": (
                    lambda df_: df_["Level"].map(cp_multipliers).astype(float)
                ),
            }
        )
        .assign(
            **{
                "Att": (
                    lambda df_: (
                        (base_attack + df_["att_iv"]) * df_["CP Multiplier"]
                    ).round(decimals_nb)
                ),
                "Def": (
                    lambda df_: (
                        (base_defense + df_["def_iv"]) * df_["CP Multiplier"]
                    ).round(decimals_nb)
                ),
                "HP": (
                    lambda df_: np.floor(
                        (base_stamina + df_["sta_iv"]) * df_["CP Multiplier"]
                    ).astype(int)
                ),
                "Non-floored Sta": (
                    lambda df_: (
                        (base_stamina + df_["sta_iv"]) * df_["CP Multiplier"]
                    ).round(decimals_nb)
                ),
            }
        )
        .assign(
            **{
                "Original Stat Product": (
                    lambda df_: df_["Att"] * df_["Def"] * df_["HP"]
                ),
                "CP": (
                    lambda df_: np.floor(
                        np.maximum(
                            10,
                            0.1
                            * df_["Att"]
                            * np.sqrt(df_["Def"] * df_["Non-floored Sta"]),
                        )
                    ).astype(int)
                ),
                "Original IV Sum": (
                    lambda df_: df_["att_iv"] + df_["def_iv"] + df_["sta_iv"]
                ),
            }
        )
        .assign(
            **{
                "IVs": (
                    lambda df_: df_.apply(
                        lambda record: "/".join(
                            str(int(record[column_name]))
                            for column_name in ("att_iv", "def_iv", "sta_iv")
                        ),
                        axis=1,
                    )
                ),
                "Stat Product": (
                    lambda df_: (df_["Original Stat Product"] / 1000).round(3)
                ),
            }
        )
        .query("CP <= @max_cp")
        .sort_values(
            ["Original Stat Product", "Original IV Sum"],
            ascending=False,
            kind="stable",
        )
        .groupby(["IVs"], as_index=False, sort=False)
        .first()
        .reset_index(drop=True)
        .assign(Rank=lambda df_: df_.index + 1)
        .set_index(["Rank"])
        .assign(
            **{
                "% Max Stat": (
                    lambda df_: (
                        100
                        * df_["Original Stat Product"]
                        / df_["Original Stat Product"].iloc[0]
                    ).round(2)
                ),
                "% Max IV Sum": (
                    lambda df_: (100 * df_["Original IV Sum"] / 45).round(0).astype(int)
                ),
            }
        )[
            [
                "Level",
                "CP",
                "IVs",
                "Att",
                "Def",
                "HP",
                "Stat Product",
                "% Max Stat",
                "% Max IV Sum",
            ]
        ]
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
