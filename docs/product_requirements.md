# Product requirements — Pokémon GO Collection Utils

## Goal

A local, single-user web application to record and monitor the state of a Pokémon GO collection. Its first feature is shundo tracking: recording, for each Pokémon, whether the collection holds a shundo — a shiny specimen whose three IVs are all at their maximum value (a shiny "hundo") — and seeing at a glance which Pokémon still lack one.

More features will follow, each as its own tab of the same application.

## Requirements

### Shundo tracking

- Every Pokémon of the main series games is listed, including those not yet released in Pokémon GO.
- A Pokémon not yet released in Pokémon GO, or whose shiny has not been released yet, is shown greyed out and cannot be marked as owned.
- The Pokémon still lacking a shundo can be listed on their own.
- Entering the existing state of a large collection has to be fast: a Pokémon is marked as owned, or unmarked, by a single click on its icon, in a grid dense enough to show many Pokémon at once. A dropdown list or a form per Pokémon does not meet this.

### Costumed shundo tracking

- A Costumed shundos tab, next to the Shundos tab, tracks the costumed shundos the same way: the same grid, grouping by region and marking by a click.
- Every costumed Pokémon known is listed: released, announced, or found only in the game's files, as are the Pokémon of the Shundos tab.
- Within a species, costumed Pokémon are ordered by the release date of the costumed Pokémon itself, not of its shiny.
- A costumed Pokémon found only in the game's files, with a costume of a past year, is not expected to be released: it is shown as unreleased in an *Unreleasable* section at the bottom of the tab, apart from those awaiting their release.

The design is in [costumes.md](costumes.md).

### Shundo hunt list

The Pokémon to look for, to fill the collection's missing shundos, are downloaded from the Shundos tab as a CSV file, `pokemons_to_shundo_hunt.csv`, with two columns: `dex number` and `name`.

- A Pokémon is listed when a shundo of it, once caught, fills a missing shundo: the missing Pokémon itself, or any Pokémon evolving into it, directly or through other stages. A missing Gyarados lists Gyarados and Magikarp, since a shundo Magikarp evolves into a shundo Gyarados. A Pokémon already owned is still listed when it evolves into a missing one, since a second shundo of it is the way to the missing one.
- Only Pokémon whose shiny is released are listed, since no other can be caught as a shundo.
- Legendary, mythical and ultra beast Pokémon are left out, since they are not usually found in the wild; the game master's class of each Pokémon decides which these are. Baby Pokémon, such as Pichu, are left out for the same reason, since they hatch from eggs; the National Pokédex seed says which these are.
- The list follows the order of the Shundos tab.

### Spawn watch

- While turned on, the application checks at a set interval for live spawns that will be shundos for the user's account and are on the shundo hunt list, using the pogocoordinates.com service, and sends a Discord message for each such spawn.
- The service is a third party whose terms allow automated use only within what a single human user would generate: a check is one search, checks are at least 5 minutes apart, and the coordinates are requested once per spawn alerted. Spawns despawning sooner than the interval may be missed.
- A spawn is alerted once.
- The watch searches for the costumed shundos missing too when its costume search is turned on: costumed Pokémon spawn during events only, and a search kept to the costumes spawning now holds nothing else.
- The watch is turned on and off, and its interval set, from the application, without restarting it. The login to the service is renewed from the application as well.
- The record of checks and alerts is kept for a bounded time.

The design is in [spawn_watch.md](spawn_watch.md).

### PvP ranks

- For a Pokémon and a PvP league, the application lists the IV spreads by rank, the best first, so the one to hunt for is known, including for a Pokémon not released yet.
- For several Pokémon and leagues, it gives the rank of IV spreads typed in, such as those of the specimens available, in one table per Pokémon and league.
- For a Pokémon's evolutionary tree, it writes a text to copy, giving each member's rank 1 IV spread for each league under a short name to label it with in the game, and the highest level at which a specimen stays within each league's cap whatever its IVs, for trades.
- For a name or a part of it, it lists the matching Pokémon with their base stats, including the forms a Pokémon takes in battle, such as Minior's cores, whose stats are the ones that count in PvP.
- The ranks follow the stat product under the league's CP cap, and take into account the minimum IV of how the specimen is obtained and the level bonuses beyond level 50.

The concepts and the design are in [pvp_ranks.md](pvp_ranks.md).

### What counts as a distinct Pokémon

- Regional forms (Alolan, Galarian, Hisuian, Paldean) are distinct Pokémon: they have their own stats and types, and some start evolutionary lines of their own (Galarian Farfetch'd evolves into Sirfetch'd).
- Other forms whose stats, types or evolutions differ from the species' base form are distinct Pokémon as well (Deoxys's Attack Forme, Midnight Lycanroc, the Wormadam cloaks).
- A costumed Pokémon (Pikachu in a Holiday hat) is not a Pokémon of its species' catalog: costumed shundos are collected apart, on a board of their own (see *Costumed shundo tracking*). A form the game calls a costume but that is a Pokémon of its own, such as Armored Mewtwo, with its own stats, is a distinct Pokémon.

The rules implementing this are in [catalog.md](catalog.md), *Catalog entries*.

### Browsing

- Pokémon are grouped by the region of the main series generation that introduced them (Kanto, Johto, …), Hisui forming its own group after Galar.
- Within a group, Pokémon are ordered by increasing National Pokédex number.
- An evolutionary line started by a regional form reads in one place: the regional form and the evolutions only it can reach are gathered at the end of the group of the region that introduced the form.

The ordering rules are in [catalog.md](catalog.md), *Grouping and ordering*.

### Data

- Which Pokémon exist in Pokémon GO, and their stats, come from the game master in the `game_masters` repository, which always sits next to this one. It is pulled automatically from time to time, to stay current.
- The list of main series Pokémon is seeded once from a community resource, after which the application does not depend on it until a new main series game introduces new Pokémon.

The sources and how they are combined are in [catalog.md](catalog.md), *Data sources*.

### Technical constraints

- Python is the main language, at least for the backend.
- Streamlit serves the interface, as a single page with one tab per feature.
- The collection is stored in a SQLite database kept outside the repository, in a folder of the user's home, so that working on the code never touches the data.
- The database is backed up automatically, to a separate folder, with a retention policy bounding the number of backups kept; a backup can also be taken on demand, and the database is backed up before any change to its schema.

Where the database and its backups live, and the retention policy, are in [architecture.md](architecture.md), *Storage and configuration* and *Backups*.
