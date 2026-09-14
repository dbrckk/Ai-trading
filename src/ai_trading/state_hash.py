from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def canonical_state_hash(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_state_hash(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        return "MISSING"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "INVALID"
    return canonical_state_hash(payload)
