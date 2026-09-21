# Third-Party Notices

For consulted/reference material that is **not redistributed**, see `SOURCES.md`.

This file records third-party software and external creative sources used by or materially relevant to Slopfest distribution.

## Runtime dependency: pygame-ce

- Project: pygame - Community Edition (`pygame-ce`)
- Package constraint: `pygame-ce>=2.5.8,<3`
- Python import namespace: `pygame`
- License identifier: **LGPL-2.1-or-later**
- Project: https://github.com/pygame-community/pygame-ce
- Documentation: https://pyga.me/

Slopfest does not vendor modified pygame-ce source. Source installs obtain pygame-ce separately. Portable binary distributions may bundle pygame-ce and its native dependencies; the Windows build collects license files shipped by the installed pygame-ce distribution into `THIRD_PARTY_LICENSES/pygame-ce/`.

pygame-ce builds also rely on SDL and related native libraries. Preserve the dependency license files provided by the pygame-ce distribution in binary releases.

## Python runtime

Portable PyInstaller builds may include CPython.

- Project: Python / CPython
- License: **Python Software Foundation License Version 2**, plus applicable incorporated-component notices
- Project: https://www.python.org/

The release helper attempts to copy the Python runtime license into `THIRD_PARTY_LICENSES/python/`.

## Build tooling / bundled bootloader: PyInstaller

- Purpose: Windows portable packaging
- License identifier used by upstream: **GPL-2.0-or-later WITH Bootloader-exception** for PyInstaller/bootloader code; some upstream files use other compatible licenses
- Project: https://pyinstaller.org/

PyInstaller is an optional build dependency, but its bootloader is part of a generated executable. Release builds therefore collect PyInstaller's installed license files into `THIRD_PARTY_LICENSES/pyinstaller/`.

The PyInstaller bootloader exception permits distributing generated applications under the application's own license, subject to licenses of bundled dependencies.

## CI tooling

The repository uses GitHub Actions such as `actions/checkout`, `actions/setup-python`, and `actions/upload-artifact`. These are CI tooling and are not redistributed as game runtime code.

## External asset candidates not currently bundled

These sources have been evaluated for possible future use but are **not bundled at v0.96.4**:

- Kenney Pixel UI Pack — CC0
- Kenney Space Shooter Extension — CC0
- Kenney Space Shooter Remastered — CC0

If any third-party asset is imported later, record exact files, creator, source URL, license, retrieval date, modifications, and attribution requirements in `ASSET_SOURCES.md` before merging.

## Historical inspiration

Slopfest is historically inspired by Synthetic Reality's _Warpath_ (1994). No original Warpath source code, graphics, audio, text, or other game assets are bundled.
