# PvP ranks — the best IV spreads for a league

The PvP ranks tab tells which IV spreads of a Pokémon are the best for a PvP league, and where given IV spreads stand among them. It serves three uses: knowing which spread to hunt for, sorting the specimens available, such as those of a raid exclusive, by how good they are for a league, and keeping track of what to hunt for in a whole evolutionary line.

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

The **rank** of an IV spread, for a Pokémon and a league, is its position in a list of spreads, ordered by decreasing stat product at their best level under the cap, then by decreasing IV sum, then by increasing attack, defense and stamina IV. Rank 1 is the best spread. Since HP is an integer, several spreads can have the same stat product; they still take consecutive ranks.

A spread has two ranks: its **absolute rank**, among all the spreads, from an IV floor of 0, and its **relative rank**, among the spreads whose three IVs are at least the minimum IV of how the specimen is obtained. The two are equal when the minimum IV is 0. The relative order of two spreads is the same in both rankings, since a spread's best level does not depend on the floor.

The level of a spread is chosen among the levels reachable with the level bonus: every half level from 1 to 50, then, up to 50 + the bonus, every half level when half levels above 50 are included, and only the whole ones when they are not.

## Pokémon

The Pokémon offered are the catalog's entries (see [catalog.md](catalog.md), *Catalog entries*) whose base form has stats in the game master: a Pokémon in the game master but not released yet is offered, so a spread can be chosen before its release. So are the Mega and Primal evolutions of their representative forms, with the stats the game master gives them: Mega Venusaur, Mega Charizard X and Mega Charizard Y, Primal Kyogre. So are the entries' battle forms (see [catalog.md](catalog.md), *Catalog entries*), whose stats are the ones a battle uses: Aegislash is met in its Shield Forme, but attacks in its Blade Forme, Aegislash (Blade). They are listed by National Pokédex number, the forms of a species in catalog order, its base form first, each entry followed by its battle forms, then by its Mega and Primal evolutions. An entry stands for its representative form's stats. A refresh stores, with each entry, those base stats, those of its battle forms and of its Mega and Primal evolutions, and the CP multipliers of every level.

## The tab

The tab has four sections. The first two share the following parameters:

| Parameter | Values | Default |
|---|---|---|
| Minimum IV | 0 (Wild), 2 (Purified), 6 (Shadow legendaries), 10 (Raid, eggs, quests) | 0 |
| Level bonus | +0 (No bonus), +1 (Best buddy), +2 (Mega Evolution "Super Max Level"), +3 (Best buddy + Mega Evolution "Super Max Level") | +0 |
| Include half levels above 50 | on, off | on |

Each of the first three sections computes only when its button is clicked, which reports any required parameter left empty. Its result stays shown until one of its parameters changes.

### Best ranks

One Pokémon, chosen from a list searched by name, and one league, both required. The section lists every spread whose IVs are at least the minimum IV by relative rank, with, for each, its absolute and relative ranks, its best level, its CP, its IVs, its attack, defense and HP, its stat product (in thousands), its stat product as a percentage of relative rank 1's, and its IV sum as a percentage of 45.

### Ranks of IV spreads

Several Pokémon, chosen from a list searched by name, several leagues, and IV spreads typed as text, one per line, its three IVs separated by spaces (`10 13 14`). The section shows one table per Pokémon and league, giving the ranks of each spread typed, with the same columns as *Best ranks*, the best rank first. The tables are ordered by Pokémon, then by league, from Little Cup to Ultra League. A spread with an IV below the minimum IV has no relative rank, and is left out.

### Rank-based names

One Pokémon, chosen from a list searched by name, and whether to show the Little Cup for evolved Pokémon (off by default). The section writes, for the Pokémon's evolutionary tree, a text to copy: the rank 1 IV spread of each member of the tree for each league, under a short name to label it with in the game, and the highest level at which a specimen of each member stays within each league's cap whatever its IVs, which is what matters when trading it. The minimum IV is 0 and there is no level bonus, whatever the parameters above say.

#### The evolutionary tree

The tree of a Pokémon is the set of entries connected to it through evolutions, in either direction, and through sharing its species, a regional form excepted: Rockruff (Dusk) is in Rockruff's tree, Alolan Meowth is not in Meowth's. Within a tree, entries of the same species with the same base stats count as one member, the first in catalog order standing for them: Rockruff and Rockruff (Dusk) are one Rockruff, and the four Deerling seasons are one Deerling.

- **Baby Pokémon are left out of a tree**: Pikachu's tree is Pikachu and Raichu, without Pichu.
- **A baby Pokémon, a Mega or Primal evolution, or a battle form**, chosen in the section, is a tree of its own, of which it is the only member.
- **A regional form no evolution leads to**, such as Alolan Exeggutor, is the only member of its tree as a consequence.

#### Names

A name is made of the league's prefix, the rank (1), one dash per stage below the member, and the member's code when it has one:

| League | Prefix |
|---|---|
| Little Cup | `PvPCE` |
| Great League | `PvPS` |
| Ultra League | `PvPH` |

- **Dashes.** A member's number of stages is the length of the longest chain of evolutions from it to a member evolving no further: none for Rhyperior, one for Rhydon, two for Rhyhorn, which gives `PvPS1`, `PvPS1-` and `PvPS1--`. Dipplin, below Hydrapple, has one.
- **Codes.** A member below a point where the tree branches has a code of two letters, as has a member of a tree with several first stages, and every member evolving from a member with a code. In Applin's tree, Flapple, Appletun, Dipplin and Hydrapple have codes, and Applin has none: `PvPS1Fl`, `PvPH1Ap`, `PvPS1-Di`, `PvPH1Hy`. A code is the first two letters of the member's name, its accents removed, the first upper case: `Ar` for Armarouge, `Ce` for Ceruledge. When another member with a code has the same species and the same number of stages, the member's form label stands for its name: the Lycanroc forms are named after Midday, Midnight and Dusk.
- **Distinct codes.** Two members with the same number of stages never share a code. When their first two letters are the same, their codes are their first letter followed by the letter at the first position where all the names concerned differ: Midday and Midnight give `Md` and `Mn`, and Dusk keeps `Du`.

#### The text

Two blocks of lines, separated by an empty line. In the first, for each member and league:

```
Max lvl to be sure for PvPH- trade: Lv27
```

with the member's name without its rank, and the highest whole level at which the member with the IV spread 15/15/15 is within the league's cap: a specimen of it at that level or below is within the cap whatever its IVs, which a trade draws again. Evolving keeps the level, so a specimen of an earlier stage is read against the line of the member it is meant to become. Whole levels, since wild specimens are caught at whole levels. A member within the cap at level 50 with 15/15/15 has no line for that league.

In the second, for each member and league:

```
Max Lvl PvPS1- (2/15/14): Lv17.5
```

with the member's name, its rank 1 IV spread, and the level that spread is ranked at, the highest within the cap. A member within the league's cap at level 50 with 15/15/15 has no line for that league, there being no spread to hunt for it beyond a perfect one; a 15/15/15 rank 1 under a cap it exceeds at level 50 has its line.

**Leagues.** Every member has Great League and Ultra League lines. The Little Cup is for Pokémon that evolve and are not an evolution themselves, babies included: a member has Little Cup lines when it evolves and no Pokémon of the catalog evolves into it, which leaves out Pikachu, an evolution of Pichu, and gives a baby chosen in the section its lines. Little Cup names have no dashes, the first stages being the only members concerned. When the Little Cup for evolved Pokémon is shown, every member has Little Cup lines, with dashes.

**Order.** The members are grouped into branches: a member with a code whose predecessor has none starts a branch, which holds it and the members evolving from it. The branches come in catalog order of the member starting them, then the members with no code. Within a group, the members go from the last stage to the first.

- In the first block, member by member in that order, Ultra League before Great League, then the Little Cup lines.
- In the second block, branch by branch, and within a group, Ultra League lines before Great League lines, each member by member; then the Little Cup lines.

For Rhyhorn's tree:

```
Max lvl to be sure for PvPH trade: Lv23
Max lvl to be sure for PvPS trade: Lv14
Max lvl to be sure for PvPH- trade: Lv27
Max lvl to be sure for PvPS- trade: Lv16
Max lvl to be sure for PvPS-- trade: Lv33
Max lvl to be sure for PvPCE trade: Lv10

Max Lvl PvPH1 (0/14/14): Lv25
Max Lvl PvPH1- (0/14/14): Lv29.5
Max Lvl PvPS1 (0/14/14): Lv15
Max Lvl PvPS1- (2/15/14): Lv17.5
Max Lvl PvPS1-- (0/13/15): Lv41
Max Lvl PvPCE1 (0/13/9): Lv12
```

The text is shown in a box with a button copying it.

### Base stats

A name, or a part of it, typed as text, case and accents aside: `flabebe` finds Flabébé. The section lists the Pokémon offered in the tab whose name contains it, in the order above, with their National Pokédex number and their attack, defense and stamina base stats. `minior` finds Minior and its eight Meteor Forms. It has no button: the list shows as soon as the text is entered.
