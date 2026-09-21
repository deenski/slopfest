$ErrorActionPreference = "Stop"

Write-Host "Installing Slopfest and optional build tooling..."
python -m pip install -e ".[build]"

Write-Host "Building portable Windows application..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name Slopfest `
  --collect-all pygame `
  launcher.py

$Out = "dist\Slopfest"
Write-Host "Copying project notices..."
Copy-Item LICENSE "$Out\LICENSE" -Force
Copy-Item CREDITS.md "$Out\CREDITS.md" -Force
Copy-Item ATTRIBUTION.md "$Out\ATTRIBUTION.md" -Force
Copy-Item SOURCES.md "$Out\SOURCES.md" -Force
Copy-Item THIRD_PARTY_NOTICES.md "$Out\THIRD_PARTY_NOTICES.md" -Force
Copy-Item ASSET_SOURCES.md "$Out\ASSET_SOURCES.md" -Force
Copy-Item LEGAL.md "$Out\LEGAL.md" -Force

Write-Host "Collecting dependency license files..."
python tools\collect_third_party_licenses.py "$Out\THIRD_PARTY_LICENSES"

Write-Host "Generating per-file checksums..."
Get-ChildItem -Path $Out -Recurse -File |
  Get-FileHash -Algorithm SHA256 |
  ForEach-Object { "{0}  {1}" -f $_.Hash.ToLower(), $_.Path.Substring((Resolve-Path $Out).Path.Length + 1) } |
  Set-Content -Encoding ascii "dist\Slopfest-SHA256SUMS.txt"

Write-Host ""
Write-Host "Build complete: dist\Slopfest\Slopfest.exe"
Write-Host "Checksums: dist\Slopfest-SHA256SUMS.txt"
