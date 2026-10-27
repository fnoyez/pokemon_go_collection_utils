# Data sources — what each external source holds

A reference to the external sources about Pokémon GO: where each one is, how it names a Pokémon, what it holds, and what it lacks. What a feature takes from them is described with the feature: the catalog in [catalog.md](catalog.md), *Data sources*, the spawn watch in [spawn_watch.md](spawn_watch.md), *The service*.

## Overview

| Source | Access | Names a Pokémon by | Holds | Lacks |
|---|---|---|---|---|
| Game master (PokeMiners `game_masters`) | Local clone, `../game_masters`, `latest/latest.json` | Template and form identifiers: `V0025_POKEMON_PIKACHU`, `PIKACHU_FALL_2019` | Every species and form in the game's data, with stats, types, evolutions, Mega and Primal evolutions, the costumes that are forms, and which costumes may evolve | Release and shiny information; the costumes that are not forms |
| PvPoke game master | `raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster.json` | Lowercase species and form identifiers: `pikachu`, `raichu_alolan` | Whether a species or form is released | Costumes; Pokémon that cannot battle count as unreleased |
| LeekDuck shiny data | `leekduck.com/shiny/pms.json` | `aa_fn`, the pogo_assets file stem: `pm25.fFALL_2019`, `pm1.cJAN_2020_NOEVOLVE` | The shiny release date of every shiny species, form and costume, announced ones included | Pokémon without a shiny |
| pogo_assets (PokeMiners) | Local clone, `../pogo_assets`; also `raw.githubusercontent.com/PokeMiners/pogo_assets/master/` | File names: `pm25.cHOLIDAY_2016.s.icon.png` | The icon of every species, form and costume found in the game's files, normal and shiny, unreleased ones included | Dates; some costumes |
| LeekDuck icons | `cdn.leekduck.com/assets/img/pokemon_icons/{aa_fn}.icon.png`, `.s.icon.png` for the shiny | `aa_fn`, as in its shiny data | An icon, normal and shiny, for every Pokémon of its shiny data, drawn on a 256-pixel canvas the Pokémon fills only part of | Pokémon without a shiny |
| PokeAPI | `pokeapi.co` API; sprites at `raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon` | National Pokédex number and English name | Main series species: names, evolution chains, baby flag; main series sprites | Anything specific to Pokémon GO |
| pogocoordinates.com | JSON API, `coordinates-api.pokemongopro.com` | Pokédex number, numeric form identifier, numeric costume identifier | Live spawns; the forms it can search, and the costumes spawning now | Costumes not spawning now |
| Bulbapedia, *Event Pokémon (GO)* | `bulbapedia.bulbagarden.net/w/index.php?title=Event_Pok%C3%A9mon_(GO)&action=raw`, the page's wikitext | English costume label and its own image code: `Festive hat`, `0025Holiday2016` | Every costume released, with the Pokémon wearing it, those obtained only by evolution, and each event it appeared in, with dates and whether a shiny was possible | Costumes not released yet; the game's costume names |

## Costumes

A costume is either of two things in the game's data, and the sources split along the same line:

- **A form flagged `isCostume`** in the game master, such as `PIKACHU_FALL_2019` or the Flying Pikachus: 97 of them, 67 of which are Pikachu's. pogo_assets and LeekDuck write it as a form, `pm25.fFALL_2019`, and pogocoordinates lists it as a form, with its form identifier.
- **A costume attribute** on an ordinary form, named by the game's costume enum: `HOLIDAY_2016`, `JAN_2020_NOEVOLVE`. The game master does not list these, beyond the `allowNoevolveEvolution` of the species allowed to evolve while wearing a `_NOEVOLVE` one. pogo_assets and LeekDuck write it after the form, `pm1.cJAN_2020_NOEVOLVE`, `pm710.fSMALL.cFALL_2022`; pogocoordinates gives its numeric identifier (`57` for `FALL_2022`) only while it spawns.

The game's costume name, with the form, is what identifies a costumed Pokémon across the sources; no source maps those names to numeric identifiers except pogocoordinates, for the live costumes. A costume without `_NOEVOLVE` keeps its costume when it evolves; a `_NOEVOLVE` one does so only for the species whose `allowNoevolveEvolution` lists it.

The sources' costume lists overlap without matching:

- pogo_assets and LeekDuck each hold about 210 costumed Pokémon with a costume attribute, and share about 200: pogo_assets lacks some LeekDuck has (the Halloween 2025 Teddiursa line, the evolutions in Pikachu visor of the Kanto starters), and holds others LeekDuck does not list, or under a spelling of their own (`May_2023`, `GOTOUR_2023_HAT_NOEVOLVE` beside LeekDuck's `GOTOUR_2023_HAT`).
- Bulbapedia's list has about 330 costumed Pokémon in about 200 rows, costume forms included. Its image codes follow the game's names loosely (`Holiday2016`, `Jan2020`, `O` for the Original Cap) and one code may stand for different costumes on different species (`Halloween`), so it is matched Pokémon by Pokémon.

## Notes per source

### Game master

- The forms of a species are in its `formSettings` template; `pokemonSettings` templates, one per form, hold stats, types, `evolutionBranch`, `pokemonClass`, `tempEvoOverrides` and `allowNoevolveEvolution`.
- Its upstream repository may go weeks without an update, during which the newest forms are missing from it.
- It holds Pokémon ahead of their release; see [catalog.md](catalog.md), *Data sources*, for how this and the other sources' limits shape the catalog.

### pogo_assets

- `Images/Pokemon/Addressable Assets/` holds the icons named `pm{dex}[.f{FORM}][.c{COSTUME}][.g2][.s].icon.png`: `.g2` is the female icon, `.s` the shiny. The form and costume are the game's names, the form without its species prefix.
- `Images/Pokemon/` holds older icons named by numbers, `pokemon_icon_{dex}_{form}_{costume}[_shiny].png`, the costume being the enum's numeric value; no file there is the same image as one of the named icons, so they do not map numbers to names.
- It is updated by hand, a few times a month, as the game's files change.

### LeekDuck shiny data

- One row per shiny Pokémon: `dex`, `family`, `released_date` (`YYYY/MM/DD`, which may be in the future for an announced release), `aa_fn`, and for a form or costume `name_suffix`, its English label with line breaks (`Party\nHat`).
- The `released_date` of some costumed Pokémon is that of their species' shiny, earlier than the costume itself: Shinx's Top Hat is dated 2018, two years before the costume.
- The costume name in `aa_fn` may change from one fetch to the next, following the game's own naming: `pm25.cGOTOUR_2023_HAT` became `pm25.cGOTOUR_2023_HAT_NOEVOLVE`.

### pogocoordinates.com

- Its form catalog lists a costume only while it spawns, flagged `live`, with `costume_id` and `costume_name`; the costume forms are listed all the time, with `live` telling which spawn now. A search asks for a costume by `costume_id` on the form, and each spawn found holds `costume_id` and `costume`. The calls themselves are in [spawn_watch.md](spawn_watch.md), *The service*.

### Bulbapedia, *Event Pokémon (GO)*

- One table row per costume, sometimes spanning several rows for several families: the label, the Pokémon caught wearing it and those only obtained by evolution as `{{MSP/GO|size=80|<dex><code>|<name>}}` templates, and the events as a list of `* <event>: <dates>`, with `{{Shinystar/GO|Shiny possible}}` on those where a shiny was possible and notes such as `** Pikachu only`.
- An event without an end gives its date in its text instead, `Since February 28, 2020, Pikachu Libre has served...`, and an announced one may give none, `''To be announced''`.
- A sprite whose image is not uploaded yet has its code in a comment, `0025<!--0025Anniversary2026Thailand01-->`.
- A costume released twice may count as two costumed Pokémon in the game, under one code: the 2019 and 2023 Detective Pikachus.
- Its content is under the CC BY-NC-SA 2.5 licence.
