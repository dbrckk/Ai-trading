from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .global_allocator import GlobalAllocatorConfig


class AllocatorConfigStore:
    def __init__(self, path: str | Path = "artifacts/global_allocator_config.json") -> None:
        self.path = Path(path)

    def load(self) -> GlobalAllocatorConfig | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return GlobalAllocatorConfig(**payload)

    def save(self, config: GlobalAllocatorConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(config), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
