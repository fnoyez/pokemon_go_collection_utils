# Costumes — the costumed Pokémon

A costumed Pokémon is a Pokémon wearing an event costume, such as Pikachu in its Holiday hat, and is collected apart from the Pokémon of the catalog (see [catalog.md](catalog.md)). The list covers every costumed Pokémon a source knows of: released, announced, or found only in the game's files. No source holds them all, and the sources name them differently; [data_sources.md](data_sources.md), *Costumes*, describes what each one holds.

## What tells a costumed Pokémon apart

A costumed Pokémon is a Pokémon of a species, or of one of its forms, wearing a costume. The costume is either a costume attribute, named by the game (`HOLIDAY_2016`), or a costume form (`PIKACHU_FALL_2019`). Its identifier is built from the game's names:

- `PIKACHU.HOLIDAY_2016` for a costume attribute, `PUMPKABOO_SMALL.FALL_2022` for one worn on a form;
- `PIKACHU_FALL_2019`, the form's identifier, for a costume form;
- `ZUBAT.TopHat`, with Bulbapedia's code, for a costumed Pokémon whose game name no source gives yet.

The costume forms are those the game master flags `isCostume`, and those `data/costume_matches.csv` names without a costume, which the game master does not flag: the clones of the first movie, Psyduck's swim ring. A costume form an override makes a catalog entry, such as Armored Mewtwo, is no costumed Pokémon (see [catalog.md](catalog.md), *Catalog entries*).

## The sources merged

- **UICONS** gives the costumed Pokémon it has an icon of, with its normal icon and, unless it cannot be shiny, its shiny one. Its numbers are turned into the game's names through the Masterfile-Generator, an icon of a form or costume it does not number being left out, and the female icons are left out too.
- **LeekDuck** gives the costumed Pokémon it lists a shiny of, with that shiny's date and an English label.
- **Bulbapedia** gives the costumed Pokémon of its list of event Pokémon, through `data/costume_matches.csv`, with the events each appeared in.

### `data/costume_matches.csv`

Bulbapedia names a costume by an image code of its own, which may stand for different costumes on different species, so each of its sprites is matched by hand to a costumed Pokémon, one line per sprite: the National Pokédex number and the code, then the form and the game's costume name.

- A line with neither form nor costume stands for a costumed Pokémon whose game name no source gives yet; it is identified by the code.
- A line with a form and no costume makes that form a costume form.
- A sprite whose events cover two costumed Pokémon of the game, such as the 2019 and 2023 Detective Pikachus, has a line for each, and the line of the later one gives its release date.

## Release dates

- **Released**: the first Bulbapedia event the costumed Pokémon appeared in. An event noted `Pikachu only` leaves out the row's other species, and one noted `Festive Pichu debut` leaves Pichu out of the events before it. A Pokémon obtained only by evolution takes the date of its debut when an event notes one, and the first date of the Pokémon it evolves from otherwise. A date ahead of today is an announced release; a costumed Pokémon in no event has no release date.
- **Unreleasable**: a costumed Pokémon in no event whose costume belongs to a year before today's, which nothing suggests will be released: Pichu in the cap of fall 2018, Mewtwo in Pikachu's cap of the first anniversary. The costume's year is the one in its name (`FALL_2018`), or else the first year a Pokémon wore it in an event (`ONE_YEAR_ANNIVERSARY`, worn by Pikachu in 2017). A costumed Pokémon in no event and of no past year is not released yet, like any other.
- **Shiny released**: the date LeekDuck gives its shiny, or its release date when that is later, since LeekDuck dates some costumed shinies by their species' shiny. A costumed Pokémon LeekDuck lists no shiny of has none.

## Evolutions

A costumed Pokémon evolves into the costumed Pokémon of its evolution wearing the same costume, when the list holds it: a costume keeps through evolution, but a `_NOEVOLVE` one only on the forms the game master allows it on. A costume form evolves into the forms the game master's settings of it name, such as Top Hat Zubat into Top Hat Golbat. A costumed Pokémon identified by its Bulbapedia code evolves into the one of the same code.

## Names and order

A costumed Pokémon is named after its species and its costume: `Pikachu (Holiday Hat)`, `Pumpkaboo (Small, Halloween)`. The costume's label is LeekDuck's when it lists one, Bulbapedia's otherwise, unless that label covers several costumes (`Cosplay Pikachu`), and the costume's name otherwise. A Bulbapedia label naming a Pokémon keeps its costume part: `Charmander wearing Friede's goggles` reads `Friede's goggles`.

They are ordered as the game's inventory sorts them by *Number*: by National Pokédex number, then by the game's number of the form, then by that of the costume, from the Masterfile-Generator (see [data_sources.md](data_sources.md), *Masterfile-Generator*). A costume attribute is worn on its species' default form, numbered before its costume forms, so Pikachu's costume attributes all come before its costume forms. A costumed Pokémon whose form or costume the masterfile does not number, or which has no game name yet, comes after the others of its species, by release date, those without one last.

## Maintaining the matches

`scripts/report_costume_catalog.py` fetches the game master, UICONS, LeekDuck and Bulbapedia, writes the costumed Pokémon to a CSV file and prints how the sources cover them:

```bash
uv run python scripts/report_costume_catalog.py --output-file-path costumed_pokemons.csv
```

The report lists what calls for a change to `data/costume_matches.csv`:

- **Bulbapedia sprites without a line**: a costume new to Bulbapedia, to match.
- **Lines standing for no Bulbapedia sprite**: a sprite Bulbapedia renamed or removed.
- **Costumed Pokémon named by Bulbapedia only**: once the game master, UICONS or LeekDuck names one, its line takes the game's name.
- **Costumed Pokémon in no Bulbapedia event**, unreleasable or not released yet: those found only in the game's files, and those a source names differently from the line matching them, which then needs the new name.
