# Sources and References

Slopfest keeps a citation ledger for material that informed the project even when none of that material is redistributed.

A source belongs here when it was used as a meaningful reference for game history, gameplay feel, visual research, dependency/licensing decisions, packaging, or release engineering. Redistribution of third-party material is tracked separately in `THIRD_PARTY_NOTICES.md` and `ASSET_SOURCES.md`.

Access dates below are **2026-09-21** unless otherwise noted.

## Historical and gameplay references

### Synthetic Reality — Warpath / WarPath

1. **MobyGames — _Warpath_ (1994)**
   - https://www.mobygames.com/game/7846/warpath/
   - Used to verify the 1994 Windows release, Synthetic Reality credit, real-time 4X/strategy classification, player count, and historical context.
   - No source code, text, graphics, audio, or other assets were copied from this page or from the original game.

2. **Google Play — Synthetic Reality, _WarPath_**
   - https://play.google.com/store/apps/details?id=com.synthetic_reality.warpath
   - Used as a current first-party/developer-linked reference for the continuing WarPath lineage, gameplay features, and Synthetic Reality attribution.
   - No app assets or text are redistributed.

3. **Gameplay video supplied by the project owner at project kickoff**
   - https://www.youtube.com/watch?v=RD_atcMUVGA
   - Used as a visual/gameplay-feel reference for the original project brief.
   - No video frames, audio, thumbnails, or other media are redistributed.

Slopfest is an independent implementation and now has its own public identity, lore, art, factions, economy, UI, and systems.

## Runtime / dependency references

4. **pygame Community Edition — official repository / README**
   - https://github.com/pygame-community/pygame-ce
   - Used for package identity, installation behavior (`pip install pygame-ce`, `import pygame`), dependency context, and the upstream license identifier `LGPL-2.1-or-later`.

5. **pygame-ce on PyPI**
   - https://pypi.org/project/pygame-ce/
   - Used during development to verify the package/release that the project intentionally depends on rather than upstream `pygame`.

6. **Python 3.13 — History and License**
   - https://docs.python.org/3.13/license.html
   - Used for release/compliance planning for portable builds that may include CPython.

7. **Python Software Foundation — Python copyright/license page**
   - https://www.python.org/doc/copyright/
   - Supplemental reference for Python redistribution/license context.

## Packaging / release references

8. **PyInstaller — License**
   - https://pyinstaller.org/en/stable/license.html
   - Used to understand licensing of the build tool and generated bootloader/application bundles.

9. **PyInstaller — Bootloader documentation**
   - https://pyinstaller.org/en/stable/bootloader-building.html
   - Used as packaging/reference material for the Windows portable-build model.

## Visual / asset research references

The following packs were reviewed as possible CC0 sources and visual references. **None of their files are bundled in v0.96.3.**

10. **Kenney — Pixel UI Pack**
    - https://kenney.nl/assets/pixel-ui-pack
    - Source page identifies the pack as Creative Commons CC0.

11. **Kenney — Space Shooter Extension**
    - https://kenney.nl/assets/space-shooter-extension
    - Source page identifies the pack as Creative Commons CC0.

12. **Kenney — Space Shooter Remastered**
    - https://kenney.nl/assets/space-shooter-remastered
    - Source page identifies the pack as Creative Commons CC0.

The current bundled Slopfest pixel-art library was generated specifically for this project rather than copied from these packs.

## AI generation / development provenance

13. **OpenAI ChatGPT**
    - https://chatgpt.com/
    - Tool used to generate the project-authored code, original pixel art, lore, UI copy, procedural sound definitions, documentation, build/release files, and related project material in response to the project owner's prompts, direction, testing, bug reports, and iterative feedback.

This entry is a development-provenance record, not a claim that OpenAI owns, publishes, sponsors, or endorses Slopfest.

## Citation policy going forward

When a new external source materially informs the project:

1. add it here with a stable URL and a short description of how it was used;
2. if files/code are actually imported or redistributed, also update `THIRD_PARTY_NOTICES.md`;
3. if an asset is imported, also update `ASSET_SOURCES.md` with exact file-level provenance;
4. do not describe consulted material as bundled material;
5. do not remove citations merely because a later implementation becomes original.
