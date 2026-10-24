"""Small, dependency-free file helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def new_directory(path: str | Path) -> Path:
    target = Path(path)
    if target.exists():
        raise ValueError(f"Output directory already exists: {target}")
    target.mkdir(parents=True)
    return target


def schema_path() -> Path:
    return Path(__file__).with_name("schema.json")
