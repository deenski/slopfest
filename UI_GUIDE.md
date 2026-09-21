# Slopfest v0.96 — Information UI

The flight view intentionally stays sparse. Extra information is opt-in.

## Quick tabs

Three small buttons live at the bottom-left of the flight screen:

- **Intel [N]** — persistent information drawer for the selected planet, or the current sub-sector when no planet is selected.
- **Ship [U]** — visual loadout drawer. The ship preview is assembled from the same hardware layers used on the flight sprite.
- **Sector [B]** — toggles the 1,000 × 1,000 world-unit sub-sector grid.

Only Intel or Ship opens as a drawer at once. The sector grid is independent.

## Inspecting without committing to travel

**Shift + click a planet** selects it and opens Intel without laying in a course.

Normal click still means “fly there.”

## Hover intel

When enabled in Settings, hovering a known planet shows a small card with:

- owner / diplomatic posture
- resource and richness
- local export purchase price
- sub-sector

Hover cards can be disabled under **Settings → Hover Intel**.

## Planet intel drawer

The drawer shows:

- ownership and hostility / treaty state
- strategic value
- resource / richness
- passive income
- garrison, defense and infrastructure
- range from the player
- specialization
- climate, habitability, traffic, population and government
- local export purchase price
- sell prices for every commodity, including difference from the average price across known peaceful markets

## Sub-sector intel

With no selected planet, Intel becomes a sub-sector summary with:

- known / owned / hostile world counts
- discoveries
- detected hostile ships and pirates
- risk rating
- the best known trade routes whose endpoints are inside that sub-sector

## Ship loadout drawer

Ship [U] shows:

- the live composed ship sprite
- current weapon and combat stats
- shield tier and capacity / regeneration
- engine tier and top speed
- radar tier and range
- cargo tier and capacity
- recovered unique technology

Upgrades are not merely UI values: shield emitters, engines, radar hardware, cargo pods and weapon hardpoints visibly alter the ship sprite.
