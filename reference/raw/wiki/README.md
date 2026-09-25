# Wiki patch-note cache

Raw wikitext (`?action=raw`) of the official Slay the Spire 2 patch notes as mirrored on the
Slay the Spire Wiki, fetched 2026-09-25 by `python -m spirometry.patch_notes fetch` (at most
10 requests per minute; reruns read this cache):

- `Slay_the_Spire_2__Patch_Notes.wikitext`: the index,
  <https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Patch_Notes>
- one file per early-access page, V0.98.1 through V0.111.0, e.g.
  <https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:V0.100.0_-_Beta_Patch>
  (file names replace `:` with `__`)

The notes are Mega Crit's; the wiki transcribes them and occasionally adds editor notes
(e.g. "(not mentioned in patch notes)"), which the parser flags in `wiki_only`.

**License.** Wiki text is available under the Creative Commons Attribution-ShareAlike 4.0
license (CC BY-SA 4.0, <https://creativecommons.org/licenses/by-sa/4.0/>). These files are
unmodified copies; attribution: the Slay the Spire Wiki contributors,
<https://slaythespire.wiki.gg>. Derived tables built from them
(`reference/patch_notes_cards.csv` and the cross-check files) are shared under the same
license.
