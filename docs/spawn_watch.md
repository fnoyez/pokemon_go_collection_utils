# Spawn watch — alerts for shundos spawning now

The spawn watch searches, at a fixed interval, for spawns that will be shundos for the user's account and are on the shundo hunt list (see [product_requirements.md](product_requirements.md), *Shundo hunt list*), and sends a Discord message for each one not alerted yet. It is controlled from the Spawn watch tab.

## The service

[pogocoordinates.com](https://pogocoordinates.com) lists live Pokémon GO spawns, and tells which of them will be shiny for a linked trainer account. Its pages call a JSON API, `https://coordinates-api.pokemongopro.com`, which the watch calls the same way:

| Call | Use |
|---|---|
| `GET /pokemon/catalog?costumes=true` | The service's forms, each with its Pokédex number, its numeric identifier and its game master form name (`TAUROS_PALDEA_AQUA`). Public. |
| `POST /search` | The spawns matching a search, at most 10 for a logged-in account. Each holds an `encounter_id`, the Pokédex number and form, CP, level, IVs, the town, the despawn time and a `reveal_code`. |
| `GET /reveal/<reveal_code>` | The spawn's coordinates. Public, rate limited per hour. |
| `GET /users/me` | The logged-in account, which is how a token is checked. |

The site's terms forbid automated requests beyond what a single human user would generate. The watch stays within that: one search per check, with checks never closer than 5 minutes apart, and it never asks for coordinates itself.

## Login

A search for shinies of the user's account needs the account's login token, which the site keeps in the browser's `localStorage` under `jwt` and sends as a `Bearer` header. The token carries no expiry.

- The Spawn watch tab's *Log in* button opens Chrome on a browser profile kept for this purpose, where the user logs in with Discord. The login completes only with the user approving the authorization on Discord's page, which is why it is not automated.
- The token is taken from the profile once the site accepts it, checked by `GET /users/me`, and stored in a file. A token merely present in the profile is not taken: one left by an interrupted login is not valid.
- A search refused for want of a valid token (401) turns the watch off and sends a Discord message asking to log in again.

## A check

1. Build the search from the hunt list: `species_forms` holds the service's identifier of every form the hunt list's entries stand for, matched by Pokédex number and game master form name; a species having an entry none of whose forms the service lists is asked for whole, in `pokemon_ids`. The search asks for shinies of the account (`shiny_only`), a 100% minimum IV, sorted by IV. A search on a form matches the spawns the service reports without a form, such as every ordinary Zorua for `ZORUA_NORMAL`.
2. Search.
3. Match each spawn to a hunt list entry. A spawn without a form is the form whose service name ends in `_NORMAL`, or the species' only form; one with a form is matched through the service's catalog by form name, suffix or identifier. A spawn matching no hunt list entry is dropped, and so is one despawning within a minute. A spawn whose form matches nothing in the service's catalog is kept when its species has an entry on the hunt list, with the form as the service gives it in the alert, rather than being dropped on a form name the matching does not know.
4. Leave out the spawns already alerted, by `encounter_id`.
5. Send one Discord message listing the new spawns, each with its Pokémon, IVs, CP, level, town, time left and the `/reveal/` link, and record them as alerted. A message that fails to send records nothing, so the next check alerts them again.
6. Record the check, and delete the checks and alerts older than the retention period (7 days).

The service's catalog is kept as a snapshot in the source snapshots folder, fetched again when it is a day old.

## Timing

- The interval is set in the tab, in minutes, and is refused below 5.
- A check runs when the watch is on and the interval has passed since the last one, plus a random delay of up to 30 seconds.
- A search refused for its rate (429) postpones the next check by the wait the service asks for, when that is longer than the interval.
- The watch runs in a background thread of the application server, started by the first page load after the server starts, and reads its settings at every wake-up, every 30 seconds: turning it off stops the checks without restarting the server.

## Storage

- `SPAWN_WATCH_CONFIG` — one row: whether the watch is on, and the interval.
- `SPAWN_CHECK` — one row per check: its time, status, spawns found and alerts sent, and a note on failure.
- `SPAWN_ALERT` — one row per spawn alerted, by `encounter_id`: the entry, the spawn's details, its despawn time and when it was alerted.
- `~/.pokemon_go_collection/pogocoordinates_browser_profile/` — the browser profile used to log in.
- `~/.pokemon_go_collection/secrets/` — the login token and the Discord webhook URL, one file each, readable by the user alone. The webhook URL is set from the tab.
