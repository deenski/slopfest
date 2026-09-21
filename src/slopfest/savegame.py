from __future__ import annotations
import json
from pathlib import Path

SAVE_VERSION = 1

def save_dir() -> Path:
    return Path.home() / ".slopfest"

def save_path() -> Path:
    return save_dir() / "save_v1.json"

def has_save() -> bool:
    return save_path().is_file()

def write_save(payload: dict) -> None:
    save_dir().mkdir(parents=True, exist_ok=True)
    envelope = {"save_version": SAVE_VERSION, "payload": payload}
    temp = save_path().with_suffix(".tmp")
    temp.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(save_path())

def read_save() -> dict:
    raw = json.loads(save_path().read_text(encoding="utf-8"))
    if raw.get("save_version") != SAVE_VERSION:
        raise ValueError("Unsupported save version")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Malformed save payload")
    return payload
