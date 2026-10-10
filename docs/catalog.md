# Catalog — the Pokémon the application lists

The catalog is the reference list every feature works on: one entry per distinct Pokémon, with its place in the display order and its release status in Pokémon GO. It is built from external data by the refresh (see [architecture.md](architecture.md), *Data refresh*) and stored in the `POKEMON_ENTRY` table. The collection itself — which entries are owned as a shundo — is stored apart from it, in the `SHUNDO` table, and refers to entries by their identifier.

## Data sources

| Source | Provides | Fetched |
|---|---|---|
| Game master, `../game_masters/latest/latest.json` (PokeMiners) | The forms each species has in Pokémon GO, with their stats, types and evolutions; the costume flag of each form. Form identifiers (`FARFETCHD_GALARIAN`) are the catalog's entry identifiers. | `git pull` of the sibling repository |
| National Pokédex seed, `data/national_dex.csv` (from PokeAPI) | Every main series species, with its National Pokédex number, English name, and the species it evolves from. | Once, by `scripts/seed_national_dex.py`; re-run when a main series game introduces new species |
| PvPoke game master (`pvpoke/pvpoke`, `src/data/gamemaster.json`) | Whether a species or form is released in Pokémon GO. | Each refresh |
| LeekDuck shiny checklist data (`leekduck.com/shiny/pms.json`) | The date each shiny species or form is, or will be, released in Pokémon GO. | Each refresh |
| Icons, PokeMiners `pogo_assets` | The Pokémon GO icon of each form, normal and shiny. PokeAPI's sprite stands in for a Pokémon with no Pokémon GO icon. | Each refresh, for the icons not cached yet |
| `data/form_overrides.csv`, `data/release_overrides.csv` | Corrections maintained by hand, described below. | Committed |

Two limits of the sources shape the rules below:

- **The game master lists Pokémon that are not released.** Niantic ships the data of species and forms ahead of their release, so its presence says nothing about availability, and it carries no shiny information at all. Release statuses come from PvPoke and LeekDuck instead.
- **PvPoke flags a Pokémon as unreleased when it cannot battle**, Ditto, Shedinja or Cosmog among them, since its subject is battling. A shiny release seen on LeekDuck, or an entry of `data/release_overrides.csv`, marks such a Pokémon released.

## Catalog entries

An entry is a species, or one of its forms that is a distinct Pokémon. Every species of the National Pokédex seed has a base entry; the game master then decides which of its forms are entries of their own.

- **The base form** of a species is its `<SPECIES>_NORMAL` form when the game master has one, its formless settings otherwise. The base entry's identifier is the species identifier (`FARFETCHD`).
- **Costumes are ignored**: a form the game master flags `isCostume` belongs to no entry.
- **A regional form is always an entry.** A form is regional when its identifier carries a region token: `ALOLA`, `GALARIAN`, `HISUIAN`, `PALDEA`. The three Paldean Tauros breeds are three entries.
- **Any other form is an entry when it differs from the base form** in its stats, its types, or the entries it evolves into (a form with no evolution at all does not count as differing by it). Each such form is an entry of its own, even when two of them share their stats and types: Black and White Kyurem do. A form not differing from the base form belongs to the base entry: Unown's letters, Spinda's patterns and Vivillon's wing patterns are all one entry.
- **`data/form_overrides.csv` corrects these rules form by form**, each line stating its reason:
  - `merge` makes a form part of another entry: the base entry, or the entry of the form it names. It is for forms that are not Pokémon of their own, such as transformations that only exist during a battle (Aegislash's Blade Forme, Darmanitan's Zen Mode), and for game master settings that make the usual form look distinct (Zacian's Hero of Many Battles, whose second type is missing).
  - `distinct` makes an entry of a form the rules would merge into the base entry, and may assign it to the variant block of a region (see below): white-striped Basculin, which evolves into the Hisuian Basculegion.
- **A species absent from the game master** has its base entry only, unreleased.

Each entry also holds the forms merged into it, which is what matching it against LeekDuck and the icons relies on.

## Grouping and ordering

### Groups

An entry belongs to the group of the region where its species was introduced, by National Pokédex number: Kanto, Johto, Hoenn, Sinnoh, Unova, Kalos, Alola, Galar, Hisui, Paldea. Hisui, introduced by *Pokémon Legends: Arceus* within the eighth generation, is a group of its own after Galar. The number ranges are declared in `src/pokemon_go_collection/regions.py`.

A variant line, described next, is the exception: it belongs to the group of the region that introduced its first form.

### Variant lines

A variant line is a form that starts an evolutionary line of its own, followed by the evolutions only that form can reach. It is ordered as a whole, so the line reads in one place:

- Its **root** is a regional form, or a form `data/form_overrides.csv` assigns to a region. Its region is the one named by the form's region token, or by the override.
- Its **exclusive evolutions** are the entries every evolution path into which starts from the line: Sirfetch'd evolves only from Galarian Farfetch'd, Obstagoon only from Galarian Linoone. An entry the base form can reach as well stays where its species puts it: Kleavor evolves from ordinary Scyther.
- A regional form that is itself an exclusive evolution of another root, such as Galarian Linoone, is part of that root's line rather than a root.

Evolutions are read from the game master. The seed's species-level link stands in for a species the game master does not hold yet, and attaches it to the base entry of the species it evolves from.

### Order within a group

1. The group's **main list**: the entries of the species the region introduced, minus those belonging to a variant line, by National Pokédex number. A species' base entry comes first, then its distinct forms in game master order.
2. The group's **variant block**, at its end: its variant lines, by the National Pokédex number of their root, then by game master form order. Within a line, the root comes first and each exclusive evolution follows the entry it evolves from.

Galar thus ends with Galarian Meowth → Perrserker, Galarian Ponyta → Galarian Rapidash, …, Galarian Farfetch'd → Sirfetch'd, and Hisui ends with Hisuian Growlithe → Hisuian Arcanine, …, Hisuian Sneasel → Sneasler.

## Release statuses

Each entry carries two statuses, which decide whether it can be marked as owned:

- **Released**: PvPoke flags one of the entry's forms as released, a shiny of it has been released, or `data/release_overrides.csv` names it. PvPoke's species identifiers are matched to the game master's form identifiers by name.
- **Shiny released**: LeekDuck lists a shiny of one of the entry's forms with a release date no later than today. LeekDuck's own costume entries never match. The earliest such date is kept as the shiny release date. LeekDuck lists announced releases ahead of time, which is why the date is compared rather than the listing alone.

An entry is shown according to the first of these that applies:

| State | Shown | Can be marked |
|---|---|---|
| Not released | Silhouette | No |
| Released, shiny not released | Greyed out | No |
| Shiny released, not owned | Faded | Yes |
| Owned | Full colour, checked | Yes, to unmark |

An entry owned before its status changes (a source corrects itself) stays owned and is shown as owned.
