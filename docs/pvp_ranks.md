# PvP ranks — the best IV spreads for a league

The PvP ranks tab tells which IV spreads of a Pokémon are the best for a PvP league, and where given IV spreads stand among them. It serves two uses: knowing which spread to hunt for, and sorting the specimens available, such as those of a raid exclusive, by how good they are for a league.

## Concepts

### Stats, IVs and levels

- **Base stats.** Each Pokémon has three base stats, attack, defense and stamina, the same for every specimen of it. They come from the game master.
- **IVs.** Each specimen adds to each base stat an individual value, its IV, from 0 to 15. An IV spread is written attack/defense/stamina, `0/14/13`. How a specimen was obtained sets a floor on its IVs: 0 in the wild, 2 when purified, 6 for a shadow legendary, 10 from a raid, an egg or a research reward.
- **Level.** A specimen is powered up by half levels, from 1 to 50. A level bonus raises the level beyond that, and applies to the specimen's current level, so a level 49.5 specimen with a bonus of 1 is at level 50.5:
  - +1, a best buddy;
  - +2, a Mega Evolution's "Super Max Level";
  - +3, both.
- **CP multiplier.** Each level has a CP multiplier, which scales the stats. The game master gives it for every whole level; the multiplier of a half level is derived from those of the two whole levels around it, `sqrt((m(L)² + m(L+1)²) / 2)` up to level 40.5 and `(m(L) + m(L+1)) / 2` from level 41.5 on.

### Stats of a specimen

At level `L`, with CP multiplier `m`:

- attack = (base attack + attack IV) × m, and defense likewise, both rounded to 5 decimals;
- HP = ⌊(base stamina + stamina IV) × m⌋, an integer, since only the integer part counts in battle;
- CP = max(10, ⌊0.1 × attack × √(defense × stamina)⌋), with stamina here the unfloored (base stamina + stamina IV) × m, rounded to 5 decimals. Attack weighs twice as much as the other two stats in it.

### Leagues and ranks

A PvP league admits only the specimens whose CP is at most its cap:

| League | CP cap |
|---|---|
| Little Cup | 500 |
| Great League | 1500 |
| Ultra League | 2500 |

A specimen entering a league is powered up to the highest level that keeps it within the cap. What it is worth there is measured by its **stat product**, attack × defense × HP, at that level. Since attack weighs more in CP than in the stat product, a low attack IV lets a specimen reach a higher level under the cap, which is why the best spreads for a league are rarely 15/15/15.

The **rank** of an IV spread, for a Pokémon and a league, is its position in the list of all spreads within the IV range, ordered by decreasing stat product at their best level under the cap, then by decreasing IV sum, then by increasing attack, defense and stamina IV. Rank 1 is the best spread. Since HP is an integer, several spreads can have the same stat product; they still take consecutive ranks.

The level of a spread is chosen among the levels reachable with the level bonus: every half level from 1 to 50, then, up to 50 + the bonus, every half level when half levels above 50 are included, and only the whole ones when they are not.

## Pokémon

The Pokémon offered are the catalog's entries (see [catalog.md](catalog.md), *Catalog entries*) whose base form has stats in the game master: a Pokémon in the game master but not released yet is offered, so a spread can be chosen before its release. They are listed by National Pokédex number, the forms of a species in catalog order, its base form first. An entry stands for its representative form's stats. A refresh stores, with each entry, those base stats, and the CP multipliers of every level.

## The tab

The tab has two sections, sharing the following parameters:

| Parameter | Values | Default |
|---|---|---|
| Minimum IV | 0 (Wild), 2 (Purified), 6 (Shadow legendaries), 10 (Raid, eggs, quests) | 0 |
| Maximum IV | 0 to 15, at least the minimum IV | 15 |
| Level bonus | +0 (No bonus), +1 (Best buddy), +2 (Mega Evolution "Super Max Level"), +3 (Best buddy + Mega Evolution "Super Max Level") | +0 |
| Include half levels above 50 | on, off | on |

A ranking takes a few seconds, so each section ranks only when its *Rank* button is clicked, which reports any required parameter left empty. Its table stays shown until one of its parameters changes.

### Best ranks

One Pokémon, chosen from a list searched by name, and one league, both required. The section lists every spread of the IV range by rank, with, for each, its best level, its CP, its IVs, its attack, defense and HP, its stat product (in thousands), its stat product as a percentage of rank 1's, and its IV sum as a percentage of 45.

### Ranks of IV spreads

Several Pokémon, chosen from a list searched by name, several leagues, and IV spreads typed as text, one per line, its three IVs separated by spaces (`10 13 14`). The section shows one table per Pokémon and league, giving the rank of each spread typed, with the same columns as *Best ranks*, the best rank first. The tables are ordered by Pokémon, then by league, from Little Cup to Ultra League. A spread outside the IV range has no rank, and is left out.
