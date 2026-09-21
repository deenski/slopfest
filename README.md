# Slopfest v0.96.5 — Intel, Assets & Distribution Foundation

**Slopfest** is an original pygame-ce real-time space strategy game built to recover the fast, strange, tactile feeling of 1990s PC space games on modern hardware.

It started from one very specific memory of Synthetic Reality's _Warpath_ (1994), but Slopfest is independently implemented and has grown into its own factions, economy, lore, visual language, exploration systems, diplomacy, invasion model, and ship customization. No original Warpath source code or game assets are included.

## License, attribution, and provenance

Project-authored Slopfest material is offered under the MIT license to the extent licensable rights exist; see `ATTRIBUTION.md` for the explicit AI-generation provenance statement. Third-party dependencies and any future imported assets remain under their own licenses.

Start here:

- `LICENSE` — project MIT license
- `ATTRIBUTION.md` — explicit ChatGPT-generation/development provenance
- `SOURCES.md` — citations for historical, gameplay, visual, dependency, and release references
- `CREDITS.md` — project/inspiration credits
- `THIRD_PARTY_NOTICES.md` — dependency licenses and redistribution notes
- `ASSET_SOURCES.md` — file-level asset provenance policy
- `LEGAL.md` — independence and historical-inspiration note
- `DISTRIBUTION.md` — release/distribution model

## Current build: v0.96.5

### Optional information UI

The main flight view stays uncluttered, with optional layers when you want them:

- **N — Intel:** selected planet or current sub-sector information
- **U — Ship:** visual loadout and installed hardware
- **B — Sector:** 1,000-unit sub-sector grid overlay
- **Shift + click planet:** inspect without travelling

Hover Intel can be disabled in Settings.

### Planet and sub-sector intelligence

Planet Intel exposes owner/treaty posture, trade prices, resource richness, passive income, garrison, defenses, infrastructure, distance, specialization, climate, habitability, traffic, population, government, and strategic value.

When no planet is selected, the drawer becomes a sub-sector report with known/friendly/hostile worlds, detected hostiles, pirates, discoveries, risk level, and local trade routes.

### Visible ship upgrades

The flight sprite and loadout preview are composed from installed hardware:

- weapon hardpoints
- engine/thruster packages
- shield emitters
- radar hardware
- cargo pods
- unique-artifact modules

Refits therefore change the ship visually as well as numerically.

### Original pixel asset library

The current asset library includes original UI icons, mineral art, specialization icons, weapon icons, module tiers, unique-tech icons, faction insignias, and composable ship hardware. See `ASSET_ATLAS_PREVIEW.png` and `src/slopfest/assets/manifest.json`.

No third-party graphics are bundled in v0.96.5.

## Install from source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
slopfest
```

The Python package and public executable are both named `slopfest`.

## Controls

- click world/site: travel
- **Shift + click planet:** inspect without travelling
- **N:** Intel drawer
- **U:** Ship/loadout drawer
- **B:** sub-sector grid
- **F1:** quickstart
- **F5 / F9:** save / load
- **P:** diplomacy
- **K:** trade computer
- **Q:** contracts
- **J:** discovery journal
- **E:** interact nearby
- **Space:** fire
- **Tab:** refit
- **Esc:** close / pause

## Distribution

The intended model is source-first GitHub plus tagged portable Windows ZIP releases containing project notices, collected dependency licenses, and SHA-256 checksums. See `DISTRIBUTION.md`.

The pygame-family runtime dependency is **pygame-ce only**.
