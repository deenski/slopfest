# Distribution Model

## Canonical source

`deenski/slopfest` on GitHub is the canonical source repository, issue tracker, release history, and provenance record.

Pre-1.0 tags use versions such as `v0.96.4`. Once the QA gate is satisfied, use semantic versioning beginning with `v1.0.0`.

## Release channels

### 1. GitHub source repository

Contains source, original assets, documentation, provenance, build scripts, and CI configuration.

### 2. GitHub Releases

Primary binary distribution for 1.0:

- `slopfest-<version>-windows-x64.zip` — portable Windows build
- `slopfest-<version>-windows-x64.zip.sha256` — archive checksum
- release notes / changelog
- GitHub-provided source archives

The portable ZIP contains:

- `Slopfest.exe` and its application directory
- `LICENSE`
- `CREDITS.md`
- `ATTRIBUTION.md`
- `SOURCES.md`
- `THIRD_PARTY_NOTICES.md`
- `ASSET_SOURCES.md`
- `THIRD_PARTY_LICENSES/`

Start with a portable ZIP rather than an installer. It is easier to audit, remove, mirror, troubleshoot, and compare byte-for-byte.

### 3. Optional itch.io mirror

After 1.0 is stable, mirror the **same GitHub Release ZIP** to itch.io for discoverability. GitHub remains the source of truth. Do not rebuild independently per storefront.

## Source installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
slopfest
```

Compatibility launch path during development:

```powershell
python -m warpath_ce
```

## Windows portable build

```powershell
.\build_windows.ps1
```

The build script copies project notices, collects third-party license files, and emits checksums.

## Release checklist

1. Run `QA_CHECKLIST.md` on the exact release candidate.
2. Confirm `ATTRIBUTION.md`, `SOURCES.md`, `ASSET_SOURCES.md`, and `THIRD_PARTY_NOTICES.md` are current.
3. Build on a clean Windows runner.
4. Smoke-test the portable ZIP on a Windows machine without the development environment.
5. Verify checksums and license folders.
6. Tag the exact source commit.
7. Let GitHub Actions build and publish the release artifact from that tag.
8. Mirror the exact artifact elsewhere rather than rebuilding it.

## Update model

No auto-updater for 1.0. Releases are explicit, versioned, inspectable downloads. Save-file migrations should be versioned separately from application updates.
