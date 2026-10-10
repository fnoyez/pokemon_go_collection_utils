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

### What counts as a distinct Pokémon

- Regional forms (Alolan, Galarian, Hisuian, Paldean) are distinct Pokémon: they have their own stats and types, and some start evolutionary lines of their own (Galarian Farfetch'd evolves into Sirfetch'd).
- Other forms whose stats, types or evolutions differ from the species' base form are distinct Pokémon as well (Deoxys's Attack Forme, Midnight Lycanroc, the Wormadam cloaks).
- Costumes do not exist for this application: a costumed Pokémon is neither a distinct Pokémon nor a specimen of its species.

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
- Streamlit serves the interface, as in the `activity_management` application, with the same tab-based layout.
- The collection is stored in a SQLite database, whose location and backups are managed as in `activity_management`.
