"""The rank-based names of an evolutionary tree, as docs/pvp_ranks.md, *Rank-based names*, describes them."""

import collections
import dataclasses
import unicodedata

from pokemon_go_collection import pvp_ranks as pvp_ranks_m

# The name prefix of each league, part of the naming scheme.
_LEAGUE_PREFIXES = {
    pvp_ranks_m.League.LITTLE_CUP: "PvPCE",
    pvp_ranks_m.League.GREAT_LEAGUE: "PvPS",
    pvp_ranks_m.League.ULTRA_LEAGUE: "PvPH",
}


@dataclasses.dataclass(frozen=True)
class TreeEntry:
    """A catalog entry, with what building a tree needs to know of it."""

    entry_id: str
    dex_number: int
    name: str
    # The entry's name without its form label: `Lycanroc` for Lycanroc (Midnight).
    species_name: str
    # `Midnight` for Lycanroc (Midnight), `Midday` for Lycanroc; None for an
    # entry of a species without forms.
    form_label: str | None
    is_variant: bool
    is_baby: bool
    # (attack, defense, stamina)
    base_stats: tuple[int, int, int]


@dataclasses.dataclass(frozen=True)
class TreeMember:
    name: str
    base_stats: tuple[int, int, int]
    # Its number of dashes, see docs/pvp_ranks.md, *Names*.
    stages_nb: int
    code: str | None
    # Without the Little Cup for evolved Pokémon, see docs/pvp_ranks.md, *The text*.
    is_little_cup_eligible: bool


def build_evolution_tree(entries, evolution_edges, pokemon):
    """Return the members of `pokemon`'s evolutionary tree, as groups in text order.

    `entries` are the catalog's entries having base stats, in catalog order, and
    `evolution_edges` the (source, target) entry identifier pairs of the
    catalog's evolutions. `pokemon` is a `RankablePokemon`. Each group is a
    branch, or the members without a code, ordered from the last stage to the
    first.
    """
    entries_by_id = {entry.entry_id: entry for entry in entries}
    evolving_entry_ids = {source_entry_id for source_entry_id, _ in evolution_edges}
    evolved_entry_ids = {target_entry_id for _, target_entry_id in evolution_edges}
    entry = entries_by_id[pokemon.entry_id]
    is_entry_itself = (
        pokemon.temporary_evolution_id is None and pokemon.battle_form_id is None
    )
    if not is_entry_itself or entry.is_baby:
        member = TreeMember(
            pokemon.name,
            pokemon.base_stats,
            0,
            None,
            is_entry_itself and entry.entry_id in evolving_entry_ids,
        )
        return [[member]]

    tree_entries = _find_tree_entries(entries, evolution_edges, entry)
    # Entries of one species with the same base stats are one member, the first
    # in catalog order standing for them.
    representative_entries = {}
    representative_entry_ids = {}
    for tree_entry in tree_entries:
        representative_entry = representative_entries.setdefault(
            (tree_entry.dex_number, tree_entry.base_stats), tree_entry
        )
        representative_entry_ids[tree_entry.entry_id] = representative_entry.entry_id
    members_entry_ids = collections.defaultdict(list)
    for entry_id, representative_entry_id in representative_entry_ids.items():
        members_entry_ids[representative_entry_id].append(entry_id)
    children = {entry_id: [] for entry_id in members_entry_ids}
    parents = {entry_id: [] for entry_id in members_entry_ids}
    for source_entry_id, target_entry_id in evolution_edges:
        if (
            source_entry_id in representative_entry_ids
            and target_entry_id in representative_entry_ids
        ):
            parent_entry_id = representative_entry_ids[source_entry_id]
            child_entry_id = representative_entry_ids[target_entry_id]
            if child_entry_id not in children[parent_entry_id]:
                children[parent_entry_id].append(child_entry_id)
                parents[child_entry_id].append(parent_entry_id)
    catalog_positions = {
        catalog_entry.entry_id: position
        for position, catalog_entry in enumerate(entries)
    }
    for entry_ids in (*children.values(), *parents.values()):
        entry_ids.sort(key=catalog_positions.get)

    stages_nbs = {}
    for entry_id in members_entry_ids:
        _count_stages(entry_id, children, stages_nbs)
    coded_entry_ids = _find_coded_entry_ids(
        sorted(members_entry_ids, key=catalog_positions.get), children, parents
    )
    codes = _build_codes(
        [entries_by_id[entry_id] for entry_id in coded_entry_ids], stages_nbs
    )
    members = {
        entry_id: TreeMember(
            entries_by_id[entry_id].name,
            entries_by_id[entry_id].base_stats,
            stages_nbs[entry_id],
            codes.get(entry_id),
            bool(children[entry_id])
            and not any(
                member_entry_id in evolved_entry_ids
                for member_entry_id in member_entry_ids
            ),
        )
        for entry_id, member_entry_ids in members_entry_ids.items()
    }
    return [
        [members[entry_id] for entry_id in group_entry_ids]
        for group_entry_ids in _group_members(
            sorted(members_entry_ids, key=catalog_positions.get),
            children,
            parents,
            coded_entry_ids,
            stages_nbs,
            catalog_positions,
        )
    ]


def _find_tree_entries(entries, evolution_edges, entry):
    """Return the entries of `entry`'s tree, babies left out, in catalog order."""
    linked_entry_ids = collections.defaultdict(set)
    tree_candidate_ids = {
        candidate.entry_id for candidate in entries if not candidate.is_baby
    }
    for source_entry_id, target_entry_id in evolution_edges:
        if {source_entry_id, target_entry_id} <= tree_candidate_ids:
            linked_entry_ids[source_entry_id].add(target_entry_id)
            linked_entry_ids[target_entry_id].add(source_entry_id)
    species_entry_ids = collections.defaultdict(list)
    for candidate in entries:
        if candidate.entry_id in tree_candidate_ids and not candidate.is_variant:
            species_entry_ids[candidate.dex_number].append(candidate.entry_id)
    for entry_ids in species_entry_ids.values():
        for entry_id in entry_ids:
            linked_entry_ids[entry_id].update(entry_ids)

    tree_entry_ids = {entry.entry_id}
    pending_entry_ids = [entry.entry_id]
    while pending_entry_ids:
        for linked_entry_id in linked_entry_ids[pending_entry_ids.pop()]:
            if linked_entry_id not in tree_entry_ids:
                tree_entry_ids.add(linked_entry_id)
                pending_entry_ids.append(linked_entry_id)
    return [candidate for candidate in entries if candidate.entry_id in tree_entry_ids]


def _count_stages(entry_id, children, stages_nbs):
    if entry_id not in stages_nbs:
        stages_nbs[entry_id] = max(
            (
                1 + _count_stages(child_entry_id, children, stages_nbs)
                for child_entry_id in children[entry_id]
            ),
            default=0,
        )
    return stages_nbs[entry_id]


def _find_coded_entry_ids(ordered_entry_ids, children, parents):
    """Return the members having a code, in catalog order.

    A member has a code when it has a sibling, among the children of one of its
    predecessors or, for a first stage, among the first stages, or when one of
    its predecessors has a code.
    """
    root_entry_ids = [
        entry_id for entry_id in ordered_entry_ids if not parents[entry_id]
    ]
    coded_entry_ids = set()
    # Predecessors come before their evolutions in this order, since the
    # members are visited from the first stages down.
    for entry_id in _order_from_first_stages(root_entry_ids, children):
        has_sibling = (
            len(root_entry_ids) > 1
            if not parents[entry_id]
            else any(
                len(children[parent_entry_id]) > 1
                for parent_entry_id in parents[entry_id]
            )
        )
        if has_sibling or any(
            parent_entry_id in coded_entry_ids for parent_entry_id in parents[entry_id]
        ):
            coded_entry_ids.add(entry_id)
    return [entry_id for entry_id in ordered_entry_ids if entry_id in coded_entry_ids]


def _order_from_first_stages(root_entry_ids, children):
    """Return the members so that every one comes after all its predecessors."""
    remaining_parents_nbs = collections.Counter()
    for child_entry_ids in children.values():
        remaining_parents_nbs.update(child_entry_ids)
    ordered_entry_ids = []
    pending_entry_ids = collections.deque(root_entry_ids)
    while pending_entry_ids:
        entry_id = pending_entry_ids.popleft()
        ordered_entry_ids.append(entry_id)
        for child_entry_id in children[entry_id]:
            remaining_parents_nbs[child_entry_id] -= 1
            if remaining_parents_nbs[child_entry_id] == 0:
                pending_entry_ids.append(child_entry_id)
    return ordered_entry_ids


def _build_codes(coded_entries, stages_nbs):
    """Return the code of each member having one, keyed by entry identifier."""
    entries_by_stages_nb = collections.defaultdict(list)
    for entry in coded_entries:
        entries_by_stages_nb[stages_nbs[entry.entry_id]].append(entry)
    codes = {}
    for stage_entries in entries_by_stages_nb.values():
        species_counts = collections.Counter(
            entry.dex_number for entry in stage_entries
        )
        letters_by_entry_id = {
            entry.entry_id: _keep_letters(
                entry.form_label
                if species_counts[entry.dex_number] > 1 and entry.form_label
                else entry.species_name
            )
            for entry in stage_entries
        }
        codes.update(_pick_distinct_codes(letters_by_entry_id))
    return codes


def _keep_letters(text):
    """Return the letters of `text`, without their accents."""
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text)
        if character.isascii() and character.isalpha()
    )


def _pick_distinct_codes(letters_by_entry_id):
    """Return a code per entry: its first two letters, or the first letter and a
    later one where the entries sharing their first two letters differ."""
    entry_ids_by_default_code = collections.defaultdict(list)
    for entry_id, letters in letters_by_entry_id.items():
        entry_ids_by_default_code[_build_code(letters, 1)].append(entry_id)
    codes = {}
    for default_code, entry_ids in entry_ids_by_default_code.items():
        if len(entry_ids) == 1:
            codes[entry_ids[0]] = default_code
            continue
        other_codes = set(entry_ids_by_default_code) - {default_code}
        max_length = max(len(letters_by_entry_id[entry_id]) for entry_id in entry_ids)
        for position in range(2, max_length):
            candidate_codes = [
                _build_code(letters_by_entry_id[entry_id], position)
                for entry_id in entry_ids
            ]
            if len(set(candidate_codes)) == len(entry_ids) and not (
                set(candidate_codes) & other_codes
            ):
                codes.update(zip(entry_ids, candidate_codes, strict=True))
                break
        else:
            # Names identical letter for letter, such as two forms without a
            # label: numbered, so the names stay distinct.
            codes.update(
                (entry_id, f"{default_code}{number}")
                for number, entry_id in enumerate(entry_ids, start=1)
            )
    return codes


def _build_code(letters, position):
    return f"{letters[:1].upper()}{letters[position : position + 1].lower()}"


def _group_members(
    ordered_entry_ids, children, parents, coded_entry_ids, stages_nbs, catalog_positions
):
    """Return the branches, in catalog order of the member starting them, then the
    members without a code; each from the last stage to the first."""
    grouped_entry_ids = set()
    groups = []
    for entry_id in coded_entry_ids:
        if any(
            parent_entry_id in coded_entry_ids for parent_entry_id in parents[entry_id]
        ):
            continue
        group = []
        pending_entry_ids = [entry_id]
        while pending_entry_ids:
            member_entry_id = pending_entry_ids.pop()
            if member_entry_id not in grouped_entry_ids:
                grouped_entry_ids.add(member_entry_id)
                group.append(member_entry_id)
                pending_entry_ids.extend(children[member_entry_id])
        groups.append(group)
    groups.append(
        [entry_id for entry_id in ordered_entry_ids if entry_id not in coded_entry_ids]
    )
    return [
        sorted(
            group,
            key=lambda entry_id: (stages_nbs[entry_id], catalog_positions[entry_id]),
        )
        for group in groups
        if group
    ]


def build_rank_names_text(cp_multipliers, groups, shows_evolved_little_cup):
    """Return the text of the tree's rank-based names, from `build_evolution_tree`.

    `cp_multipliers` maps each level to its CP multiplier.
    """
    levels = pvp_ranks_m.find_reachable_levels(0)
    pvp_stats = {}
    for group in groups:
        for member in group:
            for league in _find_member_leagues(member, shows_evolved_little_cup):
                ranks_df = pvp_ranks_m.rank_iv_spreads(
                    member.base_stats, cp_multipliers, league.value, levels
                )
                hundo_level = ranks_df.loc[ranks_df["IVs"] == "15/15/15", "Level"].iloc[
                    0
                ]
                pvp_stats[(member, league)] = (
                    ranks_df["IVs"].iloc[0],
                    ranks_df["Level"].iloc[0],
                    hundo_level,
                )

    big_leagues = [pvp_ranks_m.League.ULTRA_LEAGUE, pvp_ranks_m.League.GREAT_LEAGUE]
    members = [member for group in groups for member in group]
    trade_lines = []
    for member, league in [
        *((member, league) for member in members for league in big_leagues),
        *((member, pvp_ranks_m.League.LITTLE_CUP) for member in members),
    ]:
        if (member, league) not in pvp_stats:
            continue
        _, _, hundo_level = pvp_stats[(member, league)]
        # Level 50 being the highest, a 15/15/15 there is within the cap at every level.
        if hundo_level < 50:
            name = _build_name(member, league, "", shows_evolved_little_cup)
            trade_lines.append(
                f"Max lvl to be sure for {name} trade: Lv{int(hundo_level)}"
            )

    rank_lines = []
    for member, league in [
        *(
            (member, league)
            for group in groups
            for league in big_leagues
            for member in group
        ),
        *((member, pvp_ranks_m.League.LITTLE_CUP) for member in members),
    ]:
        if (member, league) not in pvp_stats:
            continue
        rank_1_ivs, rank_1_level, hundo_level = pvp_stats[(member, league)]
        if hundo_level < 50:
            name = _build_name(member, league, "1", shows_evolved_little_cup)
            rank_lines.append(f"Max Lvl {name} ({rank_1_ivs}): Lv{rank_1_level:g}")

    return "\n\n".join("\n".join(lines) for lines in (trade_lines, rank_lines) if lines)


def _find_member_leagues(member, shows_evolved_little_cup):
    leagues = [pvp_ranks_m.League.ULTRA_LEAGUE, pvp_ranks_m.League.GREAT_LEAGUE]
    if shows_evolved_little_cup or member.is_little_cup_eligible:
        leagues.append(pvp_ranks_m.League.LITTLE_CUP)
    return leagues


def _build_name(member, league, rank, shows_evolved_little_cup):
    # The Little Cup's first stages need no dashes, being its only members.
    has_dashes = league != pvp_ranks_m.League.LITTLE_CUP or shows_evolved_little_cup
    parts = [_LEAGUE_PREFIXES[league], rank]
    if has_dashes:
        parts.append("-" * member.stages_nb)
    if member.code is not None:
        parts.append(member.code)
    return "".join(parts)
