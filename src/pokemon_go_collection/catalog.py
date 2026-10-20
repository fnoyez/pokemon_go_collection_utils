"""Build the catalog from its sources' records, following docs/catalog.md."""

import collections
import dataclasses
import datetime
import logging
import re

from pokemon_go_collection import regions as regions_m
from pokemon_go_collection.sources import game_master as game_master_m
from pokemon_go_collection.sources import overrides as overrides_m

logger = logging.getLogger(__name__)

# Above this many passes, the classification of forms by their evolutions is
# not settling, which means a cycle in the evolution data.
_MAX_CLASSIFICATION_PASSES_NB = 20

# How a regional form token reads in an entry's name.
_REGIONAL_FORM_TOKEN_ADJECTIVES = {
    "ALOLA": "Alolan",
    "GALARIAN": "Galarian",
    "HISUIAN": "Hisuian",
    "PALDEA": "Paldean",
}

# How a form suffix reads in an entry's name, where its words capitalized
# would not: a symbol, a small word, a spelling of the games' own.
_FORM_SUFFIX_LABELS = {
    "EXCLAMATION_POINT": "!",
    "QUESTION_MARK": "?",
    "FAMILY_OF_FOUR": "Family of Four",
    "FAMILY_OF_THREE": "Family of Three",
    "POKEBALL": "Poké Ball",
    "TWO": "Two-Segment",
    "THREE": "Three-Segment",
}


@dataclasses.dataclass(frozen=True)
class BattleForm:
    """A form merged into an entry by an override, with base stats of its own."""

    form_id: str
    name: str
    # (attack, defense, stamina)
    stats: tuple[int, int, int]


@dataclasses.dataclass(frozen=True)
class CatalogEntry:
    entry_id: str
    dex_number: int
    name: str
    # The game master forms the entry stands for, its representative form first.
    form_ids: tuple[str, ...]
    # The suffix of each of those forms (None for the species itself), which
    # is how LeekDuck and the icons name a form.
    form_suffixes: tuple[str | None, ...]
    region: regions_m.Region
    is_variant: bool
    display_order: int
    # The class of its representative form.
    pokemon_class: game_master_m.PokemonClass | None
    # The (attack, defense, stamina) base stats of its representative form;
    # None for a species absent from the game master.
    base_stats: tuple[int, int, int] | None
    # The Mega and Primal evolutions of its representative form.
    temporary_evolutions: tuple[game_master_m.TemporaryEvolution, ...]
    # In game master order.
    battle_forms: tuple[BattleForm, ...]
    is_baby: bool
    # The entries it evolves into, in game master order.
    evolution_target_entry_ids: tuple[str, ...]
    # Released according to PvPoke or the release overrides. A released shiny
    # makes an entry released as well, see `is_entry_released`.
    is_released: bool
    # The earliest shiny release date known, possibly in the future.
    shiny_release_date: datetime.date | None


def is_entry_released(is_released, shiny_release_date, today):
    return is_released or is_shiny_released(shiny_release_date, today)


def is_shiny_released(shiny_release_date, today):
    return shiny_release_date is not None and shiny_release_date <= today


def build_temporary_evolution_name(entry_name, temporary_evolution_id):
    """Name a Mega or Primal evolution: MEGA_X of Charizard reads `Mega Charizard X`."""
    kind, *suffix_tokens = temporary_evolution_id.split("_")
    return " ".join([kind.capitalize(), entry_name, *suffix_tokens])


def build_catalog(
    national_dex_species,
    game_master,
    form_overrides,
    pvpoke_species,
    shiny_releases,
    release_overrides,
):
    drafts, evolution_edges = build_entry_drafts(
        national_dex_species, game_master, form_overrides
    )
    ordered_drafts = order_entry_drafts(drafts, evolution_edges)
    baby_dex_numbers = {
        species.dex_number for species in national_dex_species if species.is_baby
    }
    released_entry_ids = find_pvpoke_released_entry_ids(drafts, pvpoke_species)
    shiny_release_dates = find_shiny_release_dates(drafts, shiny_releases)
    # An override's date stands in for a shiny LeekDuck does not list.
    override_shiny_release_dates = {
        entry_id: shiny_release_date
        for entry_id, shiny_release_date in release_overrides.items()
        if shiny_release_date is not None
    }

    unknown_override_entry_ids = release_overrides.keys() - {
        draft.entry_id for draft in drafts
    }
    if unknown_override_entry_ids:
        logger.warning(
            "Release overrides naming no catalog entry: "
            f"{sorted(unknown_override_entry_ids)}"
        )

    return [
        CatalogEntry(
            draft.entry_id,
            draft.dex_number,
            draft.name,
            draft.form_ids,
            draft.form_suffixes,
            region,
            is_variant,
            display_order,
            draft.pokemon_class,
            draft.base_stats,
            draft.temporary_evolutions,
            draft.battle_forms,
            draft.dex_number in baby_dex_numbers,
            tuple(evolution_edges.get(draft.entry_id, [])),
            is_released=(
                draft.entry_id in released_entry_ids
                or draft.entry_id in release_overrides
            ),
            shiny_release_date=shiny_release_dates.get(
                draft.entry_id, override_shiny_release_dates.get(draft.entry_id)
            ),
        )
        for display_order, (draft, region, is_variant) in enumerate(ordered_drafts)
    ]


@dataclasses.dataclass(frozen=True)
class EntryDraft:
    """A catalog entry before it is ordered and given its statuses."""

    entry_id: str
    dex_number: int
    species_id: str
    name: str
    form_ids: tuple[str, ...]
    form_suffixes: tuple[str | None, ...]
    # -1 for the base entry, else the position of its representative form
    # among its species' entries, see `_SpeciesLayout.form_orders`.
    form_order: int
    # The region of the variant block it starts a line in, for a line root
    # candidate: a regional form, or a form an override assigns to a region.
    variant_region: regions_m.Region | None
    pokemon_class: game_master_m.PokemonClass | None
    base_stats: tuple[int, int, int] | None
    temporary_evolutions: tuple[game_master_m.TemporaryEvolution, ...]
    battle_forms: tuple[BattleForm, ...]


def build_entry_drafts(national_dex_species, game_master, form_overrides):
    """Return the entry drafts in National Pokédex order, and the evolution edges.

    The edges map an entry identifier to the identifiers of the entries it
    evolves into, in game master order.
    """
    forms_by_dex_number = collections.defaultdict(list)
    for form in game_master.forms:
        forms_by_dex_number[form.dex_number].append(form)

    layouts = [
        _lay_out_species(
            species,
            forms_by_dex_number.get(species.dex_number, []),
            game_master.costume_form_ids,
            form_overrides,
        )
        for species in national_dex_species
    ]
    entry_id_by_form_key = _classify_forms(layouts)

    drafts = []
    evolution_edges = collections.defaultdict(list)
    base_entry_ids_by_dex_number = {}
    for layout in layouts:
        layout_drafts = _build_layout_drafts(layout, entry_id_by_form_key)
        drafts.extend(layout_drafts)
        base_entry_ids_by_dex_number[layout.species.dex_number] = layout.species_id
        for form in layout.forms:
            source_entry_id = entry_id_by_form_key[(form.species_id, form.form_id)]
            for target_key in form.evolutions:
                target_entry_id = _resolve_evolution_target(
                    target_key, entry_id_by_form_key
                )
                # A form change within an entry is not an evolution between entries.
                if target_entry_id == source_entry_id:
                    continue
                if target_entry_id not in evolution_edges[source_entry_id]:
                    evolution_edges[source_entry_id].append(target_entry_id)

    # A species the game master does not hold yet is linked at species level.
    for layout in layouts:
        evolves_from_dex_number = layout.species.evolves_from_dex_number
        if layout.forms or evolves_from_dex_number is None:
            continue
        source_entry_id = base_entry_ids_by_dex_number[evolves_from_dex_number]
        evolution_edges[source_entry_id].append(layout.species_id)

    return drafts, dict(evolution_edges)


@dataclasses.dataclass(frozen=True)
class _SpeciesLayout:
    species: object
    species_id: str
    # Every non-costume form of the species, in game master order.
    forms: tuple
    base_form: object
    # Forms always distinct: regional ones, and those an override says so.
    distinct_forms: list
    # The form an override merges a form into, by form identifier; None for
    # the base form.
    merge_target_form_ids: dict
    # Forms whose evolutions decide whether they are distinct.
    undecided_forms: list
    # The variant region an override assigns to a form, by form identifier.
    override_variant_regions: dict
    # Whether an override chooses the base form.
    is_base_form_overridden: bool
    # The position of each form among its species' entries, by form
    # identifier: its game master position, or, for a species whose base form
    # an override chooses, the position of its override line.
    form_orders: dict


def _lay_out_species(species, species_forms, costume_form_ids, form_overrides):
    forms = tuple(
        form for form in species_forms if form.form_id not in costume_form_ids
    )
    if not forms:
        return _SpeciesLayout(
            species,
            species_id=species.identifier.upper().replace("-", "_"),
            forms=(),
            base_form=None,
            distinct_forms=[],
            merge_target_form_ids={},
            undecided_forms=[],
            override_variant_regions={},
            is_base_form_overridden=False,
            form_orders={},
        )

    species_id = forms[0].species_id
    formless_form = next(form for form in forms if form.form_id == species_id)
    normal_form = next(
        (form for form in forms if form.form_id == f"{species_id}_NORMAL"), None
    )
    overridden_base_form = next(
        (
            form
            for form in forms
            if form.form_id in form_overrides
            and form_overrides[form.form_id].decision == overrides_m.FormDecision.BASE
        ),
        None,
    )
    base_form = overridden_base_form or normal_form or formless_form

    distinct_forms = []
    merge_target_form_ids = {}
    undecided_forms = []
    override_variant_regions = {}
    for form in forms:
        if form is base_form or form is formless_form:
            continue
        override = form_overrides.get(form.form_id)
        if override is not None:
            if override.decision == overrides_m.FormDecision.DISTINCT:
                distinct_forms.append(form)
                if override.variant_region is not None:
                    override_variant_regions[form.form_id] = override.variant_region
            else:
                merge_target_form_ids[form.form_id] = override.target_form_id
        elif _find_form_region(form) is not None:
            distinct_forms.append(form)
        elif (form.stats, form.types) != (base_form.stats, base_form.types):
            distinct_forms.append(form)
        else:
            undecided_forms.append(form)

    return _SpeciesLayout(
        species,
        species_id,
        forms,
        base_form,
        distinct_forms,
        merge_target_form_ids,
        undecided_forms,
        override_variant_regions,
        is_base_form_overridden=overridden_base_form is not None,
        form_orders=_find_form_orders(
            forms, form_overrides, overridden_base_form is not None
        ),
    )


def _find_form_region(form):
    suffix = find_form_suffix(form.form_id, form.species_id)
    if suffix is None:
        return None
    return regions_m.find_regional_form_region(suffix.split("_"))


def find_form_suffix(form_id, species_id):
    """Return the form identifier without its species prefix, or None for the species itself."""
    if form_id == species_id:
        return None
    return form_id.removeprefix(f"{species_id}_")


def _find_form_orders(forms, form_overrides, is_base_form_overridden):
    if not is_base_form_overridden:
        return {form.form_id: form_index for form_index, form in enumerate(forms)}
    override_ranks = {
        form_id: override_rank for override_rank, form_id in enumerate(form_overrides)
    }
    # A form no override line names follows those that one names.
    return {
        form.form_id: override_ranks.get(form.form_id, len(override_ranks) + form_index)
        for form_index, form in enumerate(forms)
    }


def _classify_forms(layouts):
    """Map each (species, form) key to its entry identifier.

    An undecided form becomes distinct when it evolves into other entries than
    the base form does, which depends on how the target forms were classified,
    so the classification is repeated until it settles.
    """
    evolving_differently_form_keys = set()
    for _ in range(_MAX_CLASSIFICATION_PASSES_NB):
        entry_id_by_form_key = _group_forms(layouts, evolving_differently_form_keys)
        newly_found_form_keys = {
            (form.species_id, form.form_id)
            for layout in layouts
            for form in layout.undecided_forms
            if (form.species_id, form.form_id) not in evolving_differently_form_keys
            and _evolves_differently(form, layout.base_form, entry_id_by_form_key)
        }
        if not newly_found_form_keys:
            return entry_id_by_form_key
        evolving_differently_form_keys |= newly_found_form_keys
    raise RuntimeError(
        f"Form classification did not settle in {_MAX_CLASSIFICATION_PASSES_NB} passes"
    )


def _group_forms(layouts, evolving_differently_form_keys):
    """Map each (species, form) key to its entry: its own, or the one it merges into."""
    entry_id_by_form_key = {}
    for layout in layouts:
        for form in layout.forms:
            form_key = (form.species_id, form.form_id)
            if (
                form in layout.distinct_forms
                or form_key in evolving_differently_form_keys
            ):
                entry_id_by_form_key[form_key] = form.form_id
            else:
                entry_id_by_form_key[form_key] = layout.species_id
        # A form merged into another one joins that one's entry.
        for form_id, target_form_id in layout.merge_target_form_ids.items():
            if target_form_id is not None:
                entry_id_by_form_key[(layout.species_id, form_id)] = (
                    entry_id_by_form_key[(layout.species_id, target_form_id)]
                )
    return entry_id_by_form_key


def _evolves_differently(form, base_form, entry_id_by_form_key):
    if not form.evolutions or not base_form.evolutions:
        return False
    form_targets = {
        _resolve_evolution_target(target_key, entry_id_by_form_key)
        for target_key in form.evolutions
    }
    base_targets = {
        _resolve_evolution_target(target_key, entry_id_by_form_key)
        for target_key in base_form.evolutions
    }
    return form_targets != base_targets


def _resolve_evolution_target(target_key, entry_id_by_form_key):
    """Return the entry an evolution leads to; one naming no form leads to the base entry."""
    species_id, form_id = target_key
    return entry_id_by_form_key.get((species_id, form_id), species_id)


def _build_layout_drafts(layout, entry_id_by_form_key):
    species = layout.species
    if not layout.forms:
        return [
            EntryDraft(
                entry_id=layout.species_id,
                dex_number=species.dex_number,
                species_id=layout.species_id,
                name=species.name,
                form_ids=(layout.species_id,),
                form_suffixes=(None,),
                form_order=-1,
                variant_region=None,
                pokemon_class=None,
                base_stats=None,
                temporary_evolutions=(),
                battle_forms=(),
            )
        ]

    forms_by_entry_id = collections.defaultdict(list)
    # The base entry lists its base form first.
    forms_by_entry_id[layout.species_id].append(layout.base_form)
    for form in layout.forms:
        if form is not layout.base_form:
            entry_id = entry_id_by_form_key[(form.species_id, form.form_id)]
            forms_by_entry_id[entry_id].append(form)

    drafts = []
    for entry_id, entry_forms in forms_by_entry_id.items():
        representative_form = entry_forms[0]
        is_base_entry = entry_id == layout.species_id
        if is_base_entry:
            name = (
                f"{species.name} ({_build_form_label(representative_form)})"
                if layout.is_base_form_overridden
                else species.name
            )
            variant_region = None
        else:
            name = f"{species.name} ({_build_form_label(representative_form)})"
            variant_region = _find_form_region(representative_form) or next(
                (
                    layout.override_variant_regions[form.form_id]
                    for form in entry_forms
                    if form.form_id in layout.override_variant_regions
                ),
                None,
            )
        form_ids = tuple(form.form_id for form in entry_forms)
        form_suffixes = tuple(
            find_form_suffix(form.form_id, form.species_id) for form in entry_forms
        )
        form_order = (
            -1 if is_base_entry else layout.form_orders[representative_form.form_id]
        )
        drafts.append(
            EntryDraft(
                entry_id,
                species.dex_number,
                layout.species_id,
                name,
                form_ids,
                form_suffixes,
                form_order,
                variant_region,
                representative_form.pokemon_class,
                representative_form.stats,
                representative_form.temporary_evolutions,
                tuple(
                    BattleForm(
                        form.form_id,
                        f"{species.name} ({_build_form_label(form)})",
                        form.stats,
                    )
                    for form in entry_forms
                    if form.form_id in layout.merge_target_form_ids
                    and form.stats != representative_form.stats
                ),
            )
        )
    return drafts


def _build_form_label(form):
    return build_form_label(form.form_id, form.species_id)


def build_form_label(form_id, species_id):
    """Name a form from its suffix: `TAUROS_PALDEA_AQUA` reads `Paldean Aqua`."""
    suffix = find_form_suffix(form_id, species_id)
    if suffix in _FORM_SUFFIX_LABELS:
        return _FORM_SUFFIX_LABELS[suffix]
    suffix_tokens = suffix.split("_")
    words = [
        _REGIONAL_FORM_TOKEN_ADJECTIVES.get(token, token.capitalize())
        for token in suffix_tokens
    ]
    return " ".join(words)


def order_entry_drafts(drafts, evolution_edges):
    """Return (draft, region, is_variant) triples in display order."""
    drafts_by_entry_id = {draft.entry_id: draft for draft in drafts}
    predecessor_entry_ids = collections.defaultdict(set)
    for source_entry_id, target_entry_ids in evolution_edges.items():
        for target_entry_id in target_entry_ids:
            predecessor_entry_ids[target_entry_id].add(source_entry_id)

    candidate_root_drafts = [draft for draft in drafts if draft.variant_region]
    lines = {
        draft.entry_id: _collect_variant_line(
            draft.entry_id, evolution_edges, predecessor_entry_ids
        )
        for draft in candidate_root_drafts
    }
    nested_entry_ids = {entry_id for line in lines.values() for entry_id in line[1:]}
    root_drafts = [
        draft
        for draft in candidate_root_drafts
        if draft.entry_id not in nested_entry_ids
    ]
    line_member_entry_ids = {
        entry_id for draft in root_drafts for entry_id in lines[draft.entry_id]
    }

    def sort_key(draft):
        return (draft.dex_number, draft.form_order)

    ordered_drafts = []
    for region in regions_m.Region:
        main_list_drafts = sorted(
            (
                draft
                for draft in drafts
                if draft.entry_id not in line_member_entry_ids
                and regions_m.find_region(draft.dex_number) == region
            ),
            key=sort_key,
        )
        ordered_drafts.extend((draft, region, False) for draft in main_list_drafts)
        region_root_drafts = sorted(
            (draft for draft in root_drafts if draft.variant_region == region),
            key=sort_key,
        )
        for root_draft in region_root_drafts:
            ordered_drafts.extend(
                (drafts_by_entry_id[entry_id], region, True)
                for entry_id in lines[root_draft.entry_id]
            )
    return ordered_drafts


def _collect_variant_line(root_entry_id, evolution_edges, predecessor_entry_ids):
    """Return the root followed by its exclusive evolutions, each after its predecessor.

    An entry is an exclusive evolution when every entry evolving into it is in
    the line already, so membership grows until it settles before being ordered.
    """
    member_entry_ids = {root_entry_id}
    is_growing = True
    while is_growing:
        is_growing = False
        for entry_id in list(member_entry_ids):
            for target_entry_id in evolution_edges.get(entry_id, []):
                if (
                    target_entry_id not in member_entry_ids
                    and predecessor_entry_ids[target_entry_id] <= member_entry_ids
                ):
                    member_entry_ids.add(target_entry_id)
                    is_growing = True

    line = []

    def visit(entry_id):
        line.append(entry_id)
        for target_entry_id in evolution_edges.get(entry_id, []):
            if target_entry_id in member_entry_ids and target_entry_id not in line:
                visit(target_entry_id)

    visit(root_entry_id)
    return line


def find_pvpoke_released_entry_ids(drafts, pvpoke_species):
    """Return the entries PvPoke flags released.

    A PvPoke identifier matching none of a species' forms by name is taken
    for the species' base entry.
    """
    entry_ids_by_name_key = {}
    base_entry_ids_by_dex_number = {}
    for draft in drafts:
        if draft.form_order == -1:
            base_entry_ids_by_dex_number[draft.dex_number] = draft.entry_id
        for form_id in draft.form_ids:
            for name_candidate in build_pvpoke_name_candidates(form_id):
                entry_ids_by_name_key.setdefault(
                    (draft.dex_number, name_candidate), draft.entry_id
                )

    released_entry_ids = set()
    unmatched_species_ids = []
    for species in pvpoke_species:
        if not species.is_released:
            continue
        name_key = (species.dex_number, normalize_name(species.species_id))
        if name_key in entry_ids_by_name_key:
            released_entry_ids.add(entry_ids_by_name_key[name_key])
        else:
            released_entry_ids.add(base_entry_ids_by_dex_number[species.dex_number])
            unmatched_species_ids.append(species.species_id)
    logger.debug(f"PvPoke species taken for their base entry: {unmatched_species_ids}")
    return released_entry_ids


def build_pvpoke_name_candidates(form_id):
    """Return the normalized names PvPoke may give a game master form."""
    lowered_form_id = form_id.lower()
    variants = [
        lowered_form_id,
        lowered_form_id.replace("alola", "alolan"),
        lowered_form_id.replace("paldea_", ""),
        lowered_form_id.replace("paldea", "paldean"),
        lowered_form_id.removesuffix("_normal"),
        lowered_form_id.replace("_standard", ""),
        lowered_form_id.replace("_ten_percent", "_10"),
    ]
    return {normalize_name(variant) for variant in variants}


def normalize_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_shiny_release_dates(drafts, shiny_releases):
    """Return the earliest shiny release date of each entry LeekDuck lists a shiny of."""
    entry_ids_by_suffix_key = {}
    for draft in drafts:
        # LeekDuck names a form by its suffix, or now and then by its full identifier.
        for form_id, form_suffix in zip(draft.form_ids, draft.form_suffixes):
            entry_ids_by_suffix_key[(draft.dex_number, form_suffix)] = draft.entry_id
            entry_ids_by_suffix_key[(draft.dex_number, form_id)] = draft.entry_id
        if draft.form_order == -1:
            entry_ids_by_suffix_key[(draft.dex_number, None)] = draft.entry_id
            entry_ids_by_suffix_key[(draft.dex_number, "NORMAL")] = draft.entry_id

    shiny_release_dates = {}
    for shiny_release in shiny_releases:
        if shiny_release.is_costume:
            continue
        suffix_key = (shiny_release.dex_number, shiny_release.form_suffix)
        if suffix_key not in entry_ids_by_suffix_key:
            continue
        entry_id = entry_ids_by_suffix_key[suffix_key]
        if (
            entry_id not in shiny_release_dates
            or shiny_release.release_date < shiny_release_dates[entry_id]
        ):
            shiny_release_dates[entry_id] = shiny_release.release_date
    return shiny_release_dates
