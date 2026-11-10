# WP9 — Lifeline view and migration map

From [Update 1](updates/UPDATE-1_Build_Specification.pdf) (ADR-048). Open it from a family tree: **Lifeline**, at `/projects/{id}/lifeline`.

## What was built (10 Nov 2026)

- **One bar per person**, virtualised with TanStack Virtual (MIT), so only the rows on screen are drawn. Solid where the records place someone alive; faded where a date is "about", "before", a range, from a baptism or burial, or not recorded. A recorded residence counts as proof of life that year.
- **Year line**: drag along the axis, click a row, use the slider or type a year. **Autoplay** forwards or backwards at 1, 5 or 10 years a second, stopping at either end.
- **Alive each year** chart above the bars: solid for those placed alive, pale for those possibly alive.
- **Alive in [year]** panel: who the records place alive, who was possibly alive and why ("death not recorded", "born about 1850"), and who died or was born within five years.
- **Event layers**, switched on and off and remembered per person and project: wars, censuses and registration, laws, the calendar change, family events (recorded places as dots on the bars) and your own markers. Built-in events carry a checked source (National Army Museum, The National Archives, University of Nottingham) and say where they applied.
- **Your own markers**, such as the year you were born: added and removed by editors of the project.
- **Grouping and filters**: by surname or generation; a person's direct line (ancestors and descendants); find by name or place.
- **Linked map**: each person's last recorded place by the chosen year, with dashed lines joining their recorded places in date order. The map is made once and its data swapped as the year moves. It frames the family's places on first load. Faint points are suggested locations not yet checked.
- **Residences**: GEDCOM RESI records are imported in file order (`Residence`), and their places are located like other tree places.
- **Print** for a paper copy, and **Save as image** (PNG, or SVG if the browser can't draw it) for sharing or a poster. The image leaves living relatives out and says how many.
- **Phones**: controls, bars and map stack, with the map behind one button. Drag sideways along the bars with a finger to move through the years; vertical swipes still scroll.
- **Chat**: the assistant's `lifeline` tool answers "who was alive in 1985?" or "show both World Wars" from the chat's family tree, saying who was only possibly alive and why, and cites a link that opens the Lifeline at that year with those layers (`?year=1985&layers=war`). Living relatives are counted, never named. The same rules run on the server and the page, tested with the same cases.

## Rules kept

- Living people (and anyone whose status isn't known) are listed but never placed in time. Their dates and places never leave the server, so nothing printed or shared can show them.
- Nothing is guessed. An open-ended date is bounded only by the other end of the life and the longest life we assume (105 years), and is labelled "possibly alive".
- Wars and laws are context: the page says they don't show anyone took part.
- Moves are never invented: lines join recorded places, and the page says when and how people moved isn't known.
- No code was copied from Time Travel Map (GPL-3.0) or any other repo.

## Acceptance tests (Update 1)

| # | Test | Status |
|---|---|---|
| 1 | A 200-person tree renders and scrolls smoothly | Passes in tests: only the visible rows are drawn. Not yet timed on a mid-range laptop with a real 200-person tree |
| 2 | Slider at 1985 lists exactly those whose records place them alive, uncertain cases labelled | Passes (web tests, and checked in the browser at 1945 and 1960) |
| 3 | Turning off "wars" removes only war overlays | Passes |
| 4 | An estimated birth shows a faded start, not a sharp one | Passes |
| 5 | Moving the slider updates the map without a full reload | Passes: the map is mounted once and its data swapped |
| 6 | A shared export has no details of living people unless the owner allows it | Passes: living people's details never reach the page, and the shared image leaves them out with a note. An owner option to include them isn't built |

## Still to do in WP9

- An owner option to include living relatives in a private export.
- The assistant can't yet change a Lifeline that's already open; it links to a new view.
- Timing with a real 200-person tree on a mid-range laptop; the owner's sister's exported tree is the first real test (Update 1).
- Migration paths for a whole household or branch side by side.

## Running it

Load the built-in events with `python manage.py load_reference_data` (they're in `genealogy/data/overlays.json`; each has its source and checked date). Run `python manage.py migrate` for the new tables.
