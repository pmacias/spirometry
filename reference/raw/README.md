# Raw reference caches

Responses cached unchanged by `spirometry.patch_history` and `spirometry.patch_notes`, so the
tables in `reference/` rebuild without new requests. The MIT license on this repository's
code does not cover these files.

| Path | Source | License | Redistributed here? |
|---|---|---|---|
| `wiki/` | [Slay the Spire Wiki](https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Patch_Notes): patch-note pages | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), as the wiki states; these files keep that license. The patch notes themselves are Mega Crit's | Yes, raw pages |
| `cards.json`, `enchantments.json` | [Spire Codex](https://spire-codex.com) API: `/api/cards`, `/api/enchantments` | No open license. Game data © Mega Crit Games. [API terms](https://github.com/ptrlrd/spire-codex/blob/main/API_TERMS.md): community use, attribution encouraged, no redistribution of the game | Yes, raw responses |
| `events.json`, `encounters.json`, `monsters.json`, and the folders of the same names (one file per beta build) | Spire Codex API: `/api/events`, `/api/encounters`, `/api/monsters`, plain and `?version=` | As above | Yes, raw responses |
| `changelogs.json`, `changelogs/` | Spire Codex API: `/api/changelogs`, `/api/changelogs/{tag}` | As above | Yes, raw responses |
| `update_history/` | Spire Codex API: `/api/update-history/cards/{id}` | As above | Yes, raw responses |

Spire Codex's own source code is under PolyForm Noncommercial 1.0.0; nothing here is taken
from that code. Run data is not in this folder or anywhere else in the repository.

Neither source is affiliated with Mega Crit, and neither is this project. If a rights holder
objects to any file here, open an issue and it will be removed.

**Permission:** the Spire Codex maintainer confirmed on Discord (#support, November 2026) that publishing these cached API responses is fine, and preferred.
