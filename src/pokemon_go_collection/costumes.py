"""The costumed Pokémon, built from their sources as docs/costumes.md describes."""

import collections
import dataclasses
import datetime
import re

from pokemon_go_collection import catalog as catalog_m


@dataclasses.dataclass(frozen=True)
class CostumedPokemonKey:
    """What tells a costumed Pokémon apart across the sources."""

    dex_number: int
    # The form the costume is worn on, or the costume form itself when
    # `costume` is None; None for the species itself.
    form_suffix: str | None
    # The game's costume name; None for a costume form.
    costume: str | None
    # Bulbapedia's code, for a costumed Pokémon identified by it, as
    # docs/costumes.md describes; None otherwise.
    bulbapedia_code: str | None = None


@dataclasses.dataclass(frozen=True)
class CostumedPokemon:
    costumed_pokemon_id: str
    key: CostumedPokemonKey
    name: str
    # The first event it could be caught or evolved in, which may be ahead of
    # today; None when Bulbapedia lists no event of it.
    release_date: datetime.date | None
    # LeekDuck's date of its shiny, or its release date when later: LeekDuck
    # dates some costumed shinies by their species' shiny. It may be ahead of
    # today; None when LeekDuck lists no shiny of it.
    shiny_release_date: datetime.date | None
    # The pogo_assets icon files, normal and shiny, the shiny being None for a
    # costumed Pokémon that cannot be shiny; None when it has no icon.
    pogo_assets_icon_file_names: tuple[str, str | None] | None
    # LeekDuck's name of its icon files; None when LeekDuck lists no shiny of it.
    leekduck_asset_name: str | None
    # The codes of the Bulbapedia sprites standing for it.
    bulbapedia_codes: tuple[str, ...]
    # The year its costume belongs to: the one in the costume's name, or the
    # first one another Pokémon wore it in; None when neither gives one.
    costume_year: int | None
    # The costumed Pokémon it evolves into, keeping its costume.
    evolution_target_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class CostumeCatalog:
    # By National Pokédex number, then release date, the unreleased last.
    costumed_pokemons: tuple[CostumedPokemon, ...]
    # Bulbapedia sprites `data/costume_matches.csv` has no line for.
    unmatched_sprites: tuple
    # Lines of `data/costume_matches.csv` standing for no Bulbapedia sprite.
    unused_matches: tuple


def build_costume_catalog(
    national_dex_species,
    game_master,
    form_overrides,
    icons,
    shiny_releases,
    event_pokemon_rows,
    costume_matches,
):
    """Merge the costumed Pokémon of every source, following docs/costumes.md."""
    species_ids = {form.dex_number: form.species_id for form in game_master.forms}
    species_names = {
        species.dex_number: species.name for species in national_dex_species
    }
    costume_form_keys = _find_costume_form_keys(
        game_master, species_ids, form_overrides, costume_matches
    )

    icon_file_names = _find_icon_file_names(icons, costume_form_keys)
    leekduck_shiny_releases = _find_leekduck_shiny_releases(
        shiny_releases, costume_form_keys
    )
    sprite_release_dates = find_sprite_release_dates(event_pokemon_rows)
    row_labels = find_costume_labels(event_pokemon_rows)

    release_dates = {}
    bulbapedia_codes = collections.defaultdict(list)
    bulbapedia_labels = {}
    for match in costume_matches:
        sprite_key = (match.dex_number, match.bulbapedia_code)
        if sprite_key not in sprite_release_dates:
            continue
        key = _build_match_key(match)
        # A form a match names without a costume, which an override makes a
        # catalog entry, is no costumed Pokémon: Armored Mewtwo.
        if (
            key.form_suffix is not None
            and key.costume is None
            and (key.dex_number, key.form_suffix) not in costume_form_keys
        ):
            continue
        release_date = match.release_date or sprite_release_dates[sprite_key]
        if release_date is not None and (
            key not in release_dates
            or release_dates[key] is None
            or release_date < release_dates[key]
        ):
            release_dates[key] = release_date
        else:
            release_dates.setdefault(key, None)
        bulbapedia_codes[key].append(match.bulbapedia_code)
        if sprite_key in row_labels:
            bulbapedia_labels.setdefault(key, row_labels[sprite_key])

    keys = set(icon_file_names) | set(leekduck_shiny_releases) | set(release_dates)
    costume_years = find_costume_years(keys, release_dates)
    evolution_target_keys = find_evolution_target_keys(keys, game_master)
    costumed_pokemons = [
        CostumedPokemon(
            costumed_pokemon_id=build_costumed_pokemon_id(key, species_ids),
            key=key,
            name=_build_name(
                key,
                species_names[key.dex_number],
                leekduck_shiny_releases.get(key),
                bulbapedia_labels.get(key),
            ),
            release_date=release_dates.get(key),
            shiny_release_date=(
                max(
                    leekduck_shiny_releases[key].release_date,
                    release_dates.get(key) or datetime.date.min,
                )
                if key in leekduck_shiny_releases
                else None
            ),
            pogo_assets_icon_file_names=icon_file_names.get(key),
            leekduck_asset_name=(
                leekduck_shiny_releases[key].asset_name
                if key in leekduck_shiny_releases
                else None
            ),
            bulbapedia_codes=tuple(bulbapedia_codes[key]),
            costume_year=costume_years[key],
            evolution_target_ids=tuple(
                build_costumed_pokemon_id(target_key, species_ids)
                for target_key in evolution_target_keys[key]
            ),
        )
        for key in keys
    ]

    matched_sprite_keys = {
        (match.dex_number, match.bulbapedia_code) for match in costume_matches
    }
    return CostumeCatalog(
        costumed_pokemons=tuple(sorted(costumed_pokemons, key=_sort_key)),
        unmatched_sprites=tuple(
            sprite
            for row in event_pokemon_rows
            for sprite in row.caught_sprites + row.evolution_only_sprites
            if (sprite.dex_number, sprite.code) not in matched_sprite_keys
        ),
        unused_matches=tuple(
            match
            for match in costume_matches
            if (match.dex_number, match.bulbapedia_code) not in sprite_release_dates
        ),
    )


def _find_costume_form_keys(game_master, species_ids, form_overrides, costume_matches):
    """Return the (dex number, form suffix) of every costume form.

    They are the forms the game master flags as costumes, and those a match
    names without a costume, which the game master does not flag, but for the
    forms an override makes catalog entries.
    """
    dex_numbers = {form.form_id: form.dex_number for form in game_master.forms}
    costume_form_keys = {
        (
            dex_numbers[form_id],
            catalog_m.find_form_suffix(form_id, species_ids[dex_numbers[form_id]]),
        )
        for form_id in game_master.costume_form_ids
        if form_id in dex_numbers
    }
    costume_form_keys.update(
        (match.dex_number, match.form_suffix)
        for match in costume_matches
        if match.form_suffix is not None and match.costume is None
    )
    return {
        (dex_number, form_suffix)
        for dex_number, form_suffix in costume_form_keys
        if dex_number not in species_ids
        or f"{species_ids[dex_number]}_{form_suffix}" not in form_overrides
    }


def _find_icon_file_names(icons, costume_form_keys):
    """Return the normal and shiny icon files of each costumed Pokémon pogo_assets has an icon of."""
    file_names = collections.defaultdict(dict)
    for icon in icons:
        if icon.is_female:
            continue
        key = _build_source_key(
            icon.dex_number, icon.form_suffix, icon.costume, costume_form_keys
        )
        if key is not None:
            file_names[key][icon.is_shiny] = icon.file_name
    return {
        key: (by_shininess[False], by_shininess.get(True))
        for key, by_shininess in file_names.items()
        if False in by_shininess
    }


def _build_source_key(dex_number, form_suffix, costume, costume_form_keys):
    """Return the key of a costumed Pokémon from a source's names, or None for another Pokémon.

    pogo_assets spells some costume names in lowercase, `May_2023`.
    """
    form_suffix = form_suffix.upper() if form_suffix is not None else None
    if costume is not None:
        return CostumedPokemonKey(dex_number, form_suffix, costume.upper())
    if (dex_number, form_suffix) in costume_form_keys:
        return CostumedPokemonKey(dex_number, form_suffix, None)
    return None


def _find_leekduck_shiny_releases(shiny_releases, costume_form_keys):
    leekduck_shiny_releases = {}
    for shiny_release in shiny_releases:
        key = _build_source_key(
            shiny_release.dex_number,
            shiny_release.form_suffix,
            shiny_release.costume,
            costume_form_keys,
        )
        if key is not None and (
            key not in leekduck_shiny_releases
            or shiny_release.release_date < leekduck_shiny_releases[key].release_date
        ):
            leekduck_shiny_releases[key] = shiny_release
    return leekduck_shiny_releases


def find_sprite_release_dates(event_pokemon_rows):
    """Return the first event date of each sprite, by (dex number, code).

    A caught sprite takes the first event that does not leave it out: an event
    noted `Pikachu only` leaves out the row's other species, and an event noted
    `Festive Pichu debut` leaves Pichu out of the events before it. An
    evolution-only sprite takes the date of its debut when an event notes one,
    and the first date of the row's caught sprites otherwise. A sprite without
    a dated event has None.
    """
    release_dates = {}
    for row in event_pokemon_rows:
        species_names = {sprite.name for sprite in row.caught_sprites}
        caught_dates = []
        for sprite in row.caught_sprites:
            release_date = min(
                (
                    event.start_date
                    for event in _find_sprite_events(
                        row.events, sprite.name, species_names
                    )
                    if event.start_date is not None
                ),
                default=None,
            )
            _keep_earliest(
                release_dates, (sprite.dex_number, sprite.code), release_date
            )
            if release_date is not None:
                caught_dates.append(release_date)
        for sprite in row.evolution_only_sprites:
            debut_events = _find_debut_events(row.events, sprite.name)
            _keep_earliest(
                release_dates,
                (sprite.dex_number, sprite.code),
                (
                    debut_events[0].start_date
                    if debut_events
                    else min(caught_dates, default=None)
                ),
            )
    return release_dates


def _find_sprite_events(events, species_name, species_names):
    debut_events = _find_debut_events(events, species_name)
    first_index = events.index(debut_events[0]) if debut_events else 0
    sprite_events = []
    for event in events[first_index:]:
        only_names = {
            name
            for note in event.notes
            if note.endswith(" only")
            for name in species_names
            if re.search(rf"\b{re.escape(name)}\b", note)
        }
        if not only_names or species_name in only_names:
            sprite_events.append(event)
    return sprite_events


def _find_debut_events(events, species_name):
    return [
        event
        for event in events
        if any(
            note.endswith(" debut")
            and re.search(rf"\b{re.escape(species_name)}\b", note)
            for note in event.notes
        )
    ]


def _keep_earliest(dates, key, date):
    if (
        key not in dates
        or dates[key] is None
        or (date is not None and date < dates[key])
    ):
        dates[key] = date


def find_costume_labels(event_pokemon_rows):
    """Return the label of each sprite, by (dex number, code), when it names its costume.

    A label shared by sprites of several codes names a group of costumes
    (`Cosplay Pikachu`), not one, and is left out. A label naming a Pokémon
    keeps its costume part: `Charmander wearing Friede's goggles` reads
    `Friede's goggles`.
    """
    codes_by_label = collections.defaultdict(set)
    for row in event_pokemon_rows:
        for sprite in row.caught_sprites + row.evolution_only_sprites:
            codes_by_label[row.label].add(sprite.code)
    return {
        (sprite.dex_number, sprite.code): re.sub(
            r"^.* wearing (?:an? )?", "", row.label
        )
        for row in event_pokemon_rows
        if len(codes_by_label[row.label]) == 1
        for sprite in row.caught_sprites + row.evolution_only_sprites
    }


def _build_match_key(match):
    if match.form_suffix is None and match.costume is None:
        return CostumedPokemonKey(match.dex_number, None, None, match.bulbapedia_code)
    return CostumedPokemonKey(match.dex_number, match.form_suffix, match.costume)


def find_costume_years(keys, release_dates):
    """Return the year each costumed Pokémon's costume belongs to.

    It is the year in the costume's name (`FALL_2018`), or the first year a
    costumed Pokémon wore that costume in an event (`ONE_YEAR_ANNIVERSARY`,
    2017 for Pikachu), or None.
    """
    event_years = collections.defaultdict(list)
    for key, release_date in release_dates.items():
        if release_date is not None and _find_costume_name(key) is not None:
            event_years[_find_costume_name(key)].append(release_date.year)
    costume_years = {}
    for key in keys:
        costume_name = _find_costume_name(key)
        name_year_match = (
            re.search(r"20\d\d", costume_name) if costume_name is not None else None
        )
        if name_year_match is not None:
            costume_years[key] = int(name_year_match[0])
        elif event_years[costume_name]:
            costume_years[key] = min(event_years[costume_name])
        else:
            costume_years[key] = None
    return costume_years


def _find_costume_name(key):
    """Return the game's name of the costume, or of the costume form; None when no source gives it."""
    return key.costume or (key.form_suffix if key.bulbapedia_code is None else None)


def find_evolution_target_keys(keys, game_master):
    """Return the costumed Pokémon each one evolves into, keeping its costume.

    A costume evolves with its Pokémon, but a `_NOEVOLVE` one only on the forms
    the game master allows it on; a costume form does not evolve. A costumed
    Pokémon no source names the game name of evolves into the one of the same
    Bulbapedia code.
    """
    forms = {form.form_id: form for form in game_master.forms}
    dex_numbers = {form.species_id: form.dex_number for form in game_master.forms}
    species_ids = {form.dex_number: form.species_id for form in game_master.forms}
    evolution_target_keys = {}
    for key in keys:
        source_form = (
            forms.get(_build_form_id(key, species_ids))
            if key.dex_number in species_ids
            and (key.costume is not None or key.bulbapedia_code is not None)
            else None
        )
        if source_form is None or (
            key.costume is not None
            and "NOEVOLVE" in key.costume
            and key.costume not in source_form.noevolve_costumes_allowed
        ):
            evolution_target_keys[key] = ()
            continue
        target_keys = []
        for target_species_id, target_form_id in source_form.evolutions:
            target_form_suffix = (
                catalog_m.find_form_suffix(target_form_id, target_species_id)
                if target_form_id is not None
                else None
            )
            target_key = CostumedPokemonKey(
                dex_numbers[target_species_id],
                None if target_form_suffix == "NORMAL" else target_form_suffix,
                key.costume,
                key.bulbapedia_code,
            )
            if target_key in keys:
                target_keys.append(target_key)
        evolution_target_keys[key] = tuple(target_keys)
    return evolution_target_keys


def _build_form_id(key, species_ids):
    """Return the game master form a costumed Pokémon wears its costume on.

    A species the game master does not list yet, its repository lagging the
    game, is named by its number: `#1025`.
    """
    species_id = species_ids.get(key.dex_number, f"#{key.dex_number}")
    if key.form_suffix is None:
        return species_id
    return f"{species_id}_{key.form_suffix}"


def build_costumed_pokemon_id(key, species_ids):
    """Return `PIKACHU.HOLIDAY_2016`, `PIKACHU_FALL_2019` for a costume form, or
    `ZUBAT.TopHat` from Bulbapedia's code for a costumed Pokémon no other source
    names yet."""
    form_id = _build_form_id(key, species_ids)
    if key.costume is not None:
        return f"{form_id}.{key.costume}"
    if key.bulbapedia_code is not None:
        return f"{form_id}.{key.bulbapedia_code}"
    return form_id


def _build_name(key, species_name, leekduck_shiny_release, bulbapedia_label):
    """Name a costumed Pokémon after its species and its costume: `Pikachu (Party Hat)`."""
    if leekduck_shiny_release is not None and leekduck_shiny_release.label is not None:
        costume_label = leekduck_shiny_release.label
    elif bulbapedia_label is not None:
        costume_label = bulbapedia_label
    else:
        costume_label = (
            (key.costume or key.form_suffix).replace("_", " ").title()
            if key.bulbapedia_code is None
            # `Anniversary2026Thailand01` reads `Anniversary 2026 Thailand 01`.
            else re.sub(
                r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z])", " ", key.bulbapedia_code
            )
        )
    label_parts = []
    if key.form_suffix is not None and key.costume is not None:
        label_parts.append(key.form_suffix.replace("_", " ").title())
    label_parts.append(costume_label)
    return f"{species_name} ({', '.join(label_parts)})"


def _sort_key(costumed_pokemon):
    return (
        costumed_pokemon.key.dex_number,
        costumed_pokemon.release_date or datetime.date.max,
        costumed_pokemon.name,
    )


def is_unreleasable(release_date, costume_year, today):
    """Tell whether nothing suggests a costumed Pokémon will be released.

    It is in no event, and its costume belongs to a year before today's.
    """
    return (
        release_date is None and costume_year is not None and costume_year < today.year
    )
