# Slopfest 1.0 QA Gate

A 1.0 label should wait until these pass on the target Windows build.

## Launch / persistence
- fresh install launches from `python -m warpath_ce`
- packaged EXE launches without a console
- New Game setup works with 26, 34, and 44 worlds
- identical seed/settings produce identical initial galaxy
- F5 save succeeds
- F9 restores ship, worlds, treaties, markets, contracts, discoveries, pirates, and unique tech
- title-screen Continue restores the same save
- malformed save fails without crashing
- 90-second autosave does not hitch noticeably

## Economy / missions
- cargo stays whole-number only
- buy/sell leaves no residue
- trade route computer updates after market shifts
- courier, delivery, and bounty contracts complete and pay once
- hostile markets refuse service

## Combat / conquest
- shields recharge after delay
- replacement ship appears at surviving Shipyard
- no Shipyard + destroyed ship loses the match
- bombardment weakens garrison/infrastructure
- invasion troop requirements make sense
- failed invasion consumes forces
- successful invasion changes ownership

## Diplomacy / AI
- attacks start wars and reduce reputation
- gifts, ceasefires, trade pacts, alliances behave consistently
- AI does not attack during peace
- pirates remain hostile to everyone
- AI spending does not create sudden impossible early-game power spikes

## Exploration
- discovery contacts appear only in radar coverage
- derelicts/relays/anomalies/stations resolve once
- all unique modules visibly affect their intended stat
- discovery journal records visited sites
- Wayline victory can actually be achieved on every galaxy size

## UX / audio
- F1 guide opens/closes
- sound volume 0–100 works
- game still runs when mixer/audio device initialization fails
- fullscreen toggles safely
- pause/settings/title navigation never strands input
- 1280×720 and common larger resolutions remain readable

## Victory
- conquest victory
- economic victory
- Wayline victory
- supremacy victory
- end screen clearly states why the match ended

## Intel / assets (0.96)
- N opens/closes planet or sub-sector Intel without pausing simulation
- U opens/closes the ship drawer and never overlaps Intel
- B grid aligns with sub-sector labels while crossing boundaries
- Shift+click selects a planet without changing destination
- hover cards disappear over persistent drawers and can be disabled in Settings
- market prices in Intel match actual buy/sell transactions
- diplomatic posture in Intel matches Diplomacy screen
- every shield/engine/radar/cargo tier produces a visible ship-hardware change
- each weapon produces a different visible hardpoint
- unique modules appear in both ship drawer and flight sprite
- missing asset path falls back to placeholder rather than crashing
- packaged Windows build contains `warpath_ce/assets` PNG data
