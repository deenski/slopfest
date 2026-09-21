from __future__ import annotations

import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def copy_distribution_licenses(dist_name: str, out_root: Path) -> int:
    try:
        dist = metadata.distribution(dist_name)
    except metadata.PackageNotFoundError:
        print(f"license collector: distribution not installed: {dist_name}")
        return 0

    dest = out_root / safe_name(dist_name)
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for entry in dist.files or []:
        low = str(entry).lower()
        name = Path(str(entry)).name.lower()
        if not (
            "license" in low
            or "copying" in low
            or name in {"notice", "notice.txt", "copyright"}
        ):
            continue
        src = Path(dist.locate_file(entry))
        if not src.is_file():
            continue
        target = dest / safe_name(str(entry).replace("/", "__").replace("\\", "__"))
        shutil.copy2(src, target)
        count += 1

    (dest / "PACKAGE-METADATA.txt").write_text(
        "\n".join(
            [
                f"Name: {dist.metadata.get('Name', dist_name)}",
                f"Version: {dist.version}",
                f"License: {dist.metadata.get('License', '')}",
                f"License-Expression: {dist.metadata.get('License-Expression', '')}",
                f"Home-page: {dist.metadata.get('Home-page', '')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return count


def copy_python_license(out_root: Path) -> bool:
    candidates = [
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE",
        Path(sys.prefix) / "LICENSE.txt",
        Path(sys.prefix) / "LICENSE",
    ]
    for src in candidates:
        if src.is_file():
            dest = out_root / "python"
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / src.name)
            return True
    print("license collector: Python runtime license file not found automatically")
    return False


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "THIRD_PARTY_LICENSES")
    output.mkdir(parents=True, exist_ok=True)
    pygame_count = copy_distribution_licenses("pygame-ce", output)
    pyinstaller_count = copy_distribution_licenses("pyinstaller", output)
    python_found = copy_python_license(output)
    print(f"license collector: pygame-ce files copied: {pygame_count}")
    print(f"license collector: PyInstaller files copied: {pyinstaller_count}")
    print(f"license collector: Python license copied: {python_found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
