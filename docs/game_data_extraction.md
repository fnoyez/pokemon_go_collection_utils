# Game data extraction — reading the game's own files

A plan for taking from the game's own files what the application now takes from third-party extractions of them, and the limits of what those files can give. What each current source holds, and lacks, is in [data_sources.md](data_sources.md); this document builds on it.

## The goal

The application's description of the game — which species, forms and costumes exist, their numbers, names, stats, evolutions and icons — comes from repositories maintained by others, which lag the game when their maintainers stop updating them. As of 2026-10-27, the PokeMiners `game_masters` repository has had no commit since 2026-08-29, and `pogo_assets` lacks the icons of the latest costumes.

Reading the game's files directly makes that description as fresh as the latest game version, and gives one reference list of the game's names that every other source is checked against.

## What the game's files can replace

| Current source | What it gives the application | What the game's files give instead |
|---|---|---|
| PokeMiners `game_masters` | Species, forms, stats, evolutions, the costume forms (`isCostume`), `allowNoevolveEvolution`, CP multipliers | The same game master, from the latest version |
| `pogo_assets` | Icons of species, forms and costumes, normal and shiny | The icons themselves, from the game's asset bundles |
| LeekDuck icon CDN | Icons `pogo_assets` lacks, on a padded canvas, and only for Pokémon with a shiny | No longer needed once the icons are extracted |
| Masterfile-Generator | The game's numbers of forms and costumes, which order the Costumed shundos tab | The same numbers, from the decoded protocol |
| PokeAPI | English names, evolution chains, the baby flag | Names from the game's text files; families and evolutions from the game master |

The game's text files also hold the names in every language of the game, French included, so the tabs could name Pokémon and costumes as the user's own game does, which eases checking the tabs against the inventory.

## What the game's files cannot replace

Whether and when something is released is decided on Niantic's servers, not shipped in the files: the files hold Pokémon, forms and costumes well ahead of their release, and some never released.

| Source | What it gives that the files lack |
|---|---|
| LeekDuck shiny data | Shiny release dates, and English costume labels |
| Bulbapedia, *Event Pokémon (GO)* | Release dates, from the events each costumed Pokémon appeared in |
| PvPoke game master | Whether a species or form is released |
| pogocoordinates.com | Live spawns, and the costumes spawning now |

So the extraction reduces the number of sources; it does not bring them down to one.

## The brittle parts it would make sturdier

- **`data/costume_matches.csv`**, about 330 lines matched by hand (see [costumes.md](costumes.md), *`data/costume_matches.csv`*). Bulbapedia names costumes by image codes of its own, so its dates have to be tied to the game's names by hand. With the game's full list of costumes, a match could be proposed automatically and reviewed, rather than written; Bulbapedia's dates still have to be tied to each costumed Pokémon.
- **The workarounds for a lagging game master**: lines of `data/costume_matches.csv` that make a form a costume form because the game master does not list it yet, with a form name that has to be guessed from Bulbapedia's code; the `#1025` identifier of a species the game master lacks; costumed Pokémon identified by a Bulbapedia code (`ZUBAT.TopHat`) because no source gives their game name.
- **Names that disagree between sources**: `pogo_assets` writes some costume names in lowercase (`May_2023`) and holds names the game does not use (`GOTOUR_2023_HAT` beside `GOTOUR_2023_HAT_NOEVOLVE`), which show up as extra unreleasable costumed Pokémon; LeekDuck renames its files when the game renames a costume. With the game's own list as the reference, every such name is caught at refresh.
- **The *Unreleasable* rule** (see [costumes.md](costumes.md), *Release dates*) is a heuristic on the costume's year. The game's files may hold sturdier signals, such as the costumes named `NOT_FOR_RELEASE_ALPHA`; whether they do is to be investigated.
- **Parsing Bulbapedia's wikitext** stays fragile to a change of the page's layout, whatever the extraction does.

## Before building the extraction

- **Look for a fresher maintained source first.** The Masterfile-Generator is regenerated within days of each game version, while PokeMiners lags by months; another maintained project may already publish a fresh game master, the text files and the icons. Switching to it costs a source module, where an extraction costs a pipeline to keep running.
- **The cost of an extraction is its upkeep.** Each game version has to be downloaded, its game master decoded with protocol definitions that match it (POGOProtos), and its asset bundles unpacked (with a tool such as UnityPy); field and message names change between versions. A lagging third-party extraction is exactly a pipeline whose upkeep stopped.
- **Data mining the game is against Niantic's terms of service.** For a personal tool the decision is the user's, but it is one to take knowingly before starting.
