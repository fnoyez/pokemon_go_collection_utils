# Data sources — what each external source holds

A reference to the external sources about Pokémon GO: where each one is, how it names a Pokémon, what it holds, and what it lacks. What a feature takes from them is described with the feature: the catalog in [catalog.md](catalog.md), *Data sources*, the spawn watch in [spawn_watch.md](spawn_watch.md), *The service*.

## Overview

| Source | Access | Names a Pokémon by | Holds | Lacks |
|---|---|---|---|---|
| Game master (alexelgt `game_masters`) | `raw.githubusercontent.com/alexelgt/game_masters/master/GAME_MASTER.json`, with `timestamp.json` | Template and form identifiers: `V0025_POKEMON_PIKACHU`, `PIKACHU_FALL_2019` | Every species and form in the game's data, with stats, types, evolutions, Mega and Primal evolutions, the costumes that are forms, and which costumes may evolve | Release and shiny information; the costumes that are not forms |
| PvPoke game master | `raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster.json` | Lowercase species and form identifiers: `pikachu`, `raichu_alolan` | Whether a species or form is released | Costumes; Pokémon that cannot battle count as unreleased |
| LeekDuck shiny data | `leekduck.com/shiny/pms.json` | `aa_fn`, an icon file stem: `pm25.fFALL_2019`, `pm1.cJAN_2020_NOEVOLVE` | The shiny release date of every shiny species, form and costume, announced ones included | Pokémon without a shiny |
| UICONS (WatWowMap `wwm-uicons`) | `raw.githubusercontent.com/WatWowMap/wwm-uicons/main/`: `index.json` lists the files, `pokemon/` holds the icons | File names made of the game's numbers: `25_c1_s.png` | The icon of every species, form and costume found in the game's files, normal and shiny, unreleased ones included, cropped to the Pokémon | Dates; the newest costumes, for the first days after the game adds them |
| PokeAPI | `pokeapi.co` API; sprites at `raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon` | National Pokédex number and English name | Main series species: names, evolution chains, baby flag; main series sprites | Anything specific to Pokémon GO |
| pogocoordinates.com | JSON API, `coordinates-api.pokemongopro.com` | Pokédex number, numeric form identifier, numeric costume identifier | Live spawns; the forms it can search, and the costumes spawning now | Costumes not spawning now |
| Masterfile-Generator (WatWowMap) | `raw.githubusercontent.com/WatWowMap/Masterfile-Generator/master/master-latest-raw.json` | The game's form and costume names, with their numbers: `PIKACHU_FALL_2019` is 894, `HOLIDAY_2016` 1 | The number of every form and costume of the game's decoded protocol (POGOProtos), and each species' default form | Release information |
| Bulbapedia, *Event Pokémon (GO)* | `bulbapedia.bulbagarden.net/w/index.php?title=Event_Pok%C3%A9mon_(GO)&action=raw`, the page's wikitext | English costume label and its own image code: `Festive hat`, `0025Holiday2016` | Every costume released, with the Pokémon wearing it, those obtained only by evolution, and each event it appeared in, with dates and whether a shiny was possible | Costumes not released yet; the game's costume names |

## Costumes

A costume is either of two things in the game's data, and the sources split along the same line:

- **A form flagged `isCostume`** in the game master, such as `PIKACHU_FALL_2019` or the Flying Pikachus: 108 of them, 70 of which are Pikachu's. LeekDuck writes it as a form, `pm25.fFALL_2019`, UICONS by its form number, `25_f894.png`, and pogocoordinates lists it as a form, with its form identifier.
- **A costume attribute** on an ordinary form, named by the game's costume enum: `HOLIDAY_2016`, `JAN_2020_NOEVOLVE`. The game master does not list these, beyond the `allowNoevolveEvolution` of the species allowed to evolve while wearing a `_NOEVOLVE` one. LeekDuck writes it after the form, `pm1.cJAN_2020_NOEVOLVE`, `pm710.fSMALL.cFALL_2022`, and UICONS by the numbers of both, `1_c11.png`, `710_c57.png`; pogocoordinates gives its numeric identifier (`57` for `FALL_2022`) only while it spawns.

The game's costume name, with the form, is what identifies a costumed Pokémon across the sources; the Masterfile-Generator maps every form and costume name to the game's number, which is what UICONS names its icons by, and pogocoordinates does for the costumes spawning now. A costume without `_NOEVOLVE` keeps its costume when it evolves; a `_NOEVOLVE` one does so only for the species whose `allowNoevolveEvolution` lists it.

The sources' costume lists overlap without matching:

- UICONS holds about 215 costumed Pokémon with a costume attribute, and LeekDuck about 210, every one of which UICONS holds too; the others are costumed Pokémon LeekDuck lists no shiny of.
- Bulbapedia's list has about 330 costumed Pokémon in about 200 rows, costume forms included. Its image codes follow the game's names loosely (`Holiday2016`, `Jan2020`, `O` for the Original Cap) and one code may stand for different costumes on different species (`Halloween`), so it is matched Pokémon by Pokémon.

## Notes per source

### Game master

- The forms of a species are in its `formSettings` template; `pokemonSettings` templates, one per form, hold stats, types, `evolutionBranch`, `pokemonClass`, `tempEvoOverrides` and `allowNoevolveEvolution`.
- It is decoded from each game version within days of it. A form the decoder's protocol definitions do not name yet is given by its number, `3362`, in the species' `formSettings` and in the `evolutionBranch` leading to it; the template identifier of its own `pokemonSettings` carries its name, `V0041_POKEMON_ZUBAT_HALLOWEEN_2026_01`.
- It holds Pokémon ahead of their release; see [catalog.md](catalog.md), *Data sources*, for how this and the other sources' limits shape the catalog.

### UICONS

- `pokemon/` holds the icons named `{dex}[_f{form}][_c{costume}][_g2][_s].png`, following the [UICONS](https://github.com/UIcons/UIcons) convention: the form and costume are the game's numbers, `_g2` is the female icon, `_s` the shiny. An icon without `_f` is that of the species' default form, which the Masterfile-Generator gives: `710_c57.png` is the Small Size Pumpkaboo's.
- Icons with other parts, such as `_a1` for a Shadow Pokémon, stand for other states of the Pokémon.
- `index.json` lists every file, by folder.
- It is updated by hand, as the game's files change.

### LeekDuck shiny data

- One row per shiny Pokémon: `dex`, `family`, `released_date` (`YYYY/MM/DD`, which may be in the future for an announced release), `aa_fn`, and for a form or costume `name_suffix`, its English label with line breaks (`Party\nHat`).
- The `released_date` of some costumed Pokémon is that of their species' shiny, earlier than the costume itself: Shinx's Top Hat is dated 2018, two years before the costume.
- The costume name in `aa_fn` may change from one fetch to the next, following the game's own naming: `pm25.cGOTOUR_2023_HAT` became `pm25.cGOTOUR_2023_HAT_NOEVOLVE`.

### pogocoordinates.com

- Its form catalog lists a costume only while it spawns, flagged `live`, with `costume_id` and `costume_name`; the costume forms are listed all the time, with `live` telling which spawn now, except a few it lists as ordinary forms, without the costume flag or `live`: `ZUBAT_HALLOWEEN_2026_01`, the clones of the first movie, Psyduck's swim ring, the Goggles Charmander line. A search asks for a costume by `costume_id` on the form, and each spawn found holds `costume_id` and `costume`. The calls themselves are in [spawn_watch.md](spawn_watch.md), *The service*.

### Masterfile-Generator

- `pokemon` gives each species' `defaultFormId`, the form of its Pokémon that have no other (`PIKACHU_NORMAL`, 598); `forms` and `costumes` give each form's `formId` and each costume's `id` by their `proto`, the game's name.
- The numbers follow the order the game added its forms and costumes in, not their release: the Summer 2023 Pikachus are numbered after the GO Fest 2025 ones.
- It is regenerated from the decoded protocol of each game version, within days of it, and so holds forms the game master lacks while its repository lags.

### Bulbapedia, *Event Pokémon (GO)*

- One table row per costume, sometimes spanning several rows for several families: the label, the Pokémon caught wearing it and those only obtained by evolution as `{{MSP/GO|size=80|<dex><code>|<name>}}` templates, and the events as a list of `* <event>: <dates>`, with `{{Shinystar/GO|Shiny possible}}` on those where a shiny was possible and notes such as `** Pikachu only`.
- An event without an end gives its date in its text instead, `Since February 28, 2020, Pikachu Libre has served...`, and an announced one may give none, `''To be announced''`.
- A sprite whose image is not uploaded yet has its code in a comment, `0025<!--0025Anniversary2026Thailand01-->`.
- A costume released twice may count as two costumed Pokémon in the game, under one code: the 2019 and 2023 Detective Pikachus.
- Its content is under the CC BY-NC-SA 2.5 licence.
