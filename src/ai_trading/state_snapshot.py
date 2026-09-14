from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SnapshotManifest:
    created_at_utc: str
    files: dict[str, str]


class AtomicSnapshotStore:
    def __init__(
        self,
        root: str | Path = "artifacts/snapshots",
    ) -> None:
        self.root = Path(root)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def create(self, files: list[str | Path]) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        final_dir = self.root / stamp
        temp_dir = self.root / f".{stamp}.tmp"
        temp_dir.mkdir(parents=True, exist_ok=False)

        manifest: dict[str, str] = {}
        for item in files:
            source = Path(item)
            if not source.exists() or not source.is_file():
                continue
            destination = temp_dir / source.name
            shutil.copy2(source, destination)
            manifest[source.name] = self._sha256(destination)

        payload = SnapshotManifest(
            created_at_utc=datetime.now(UTC).isoformat(),
            files=manifest,
        )
        (temp_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "created_at_utc": payload.created_at_utc,
                    "files": payload.files,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.replace(final_dir)
        return final_dir

    def latest_valid(self) -> Path | None:
        if not self.root.exists():
            return None
        for directory in sorted(
            (p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")),
            reverse=True,
        ):
            manifest_path = directory / "manifest.json"
            if not manifest_path.exists():
                continue
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = payload.get("files", {})
            valid = True
            for name, expected in files.items():
                path = directory / name
                if not path.exists() or self._sha256(path) != expected:
                    valid = False
                    break
            if valid:
                return directory
        return None

    def prune(self, keep_last: int = 20) -> int:
        if keep_last < 1:
            raise ValueError("keep_last must be at least 1")
        if not self.root.exists():
            return 0

        snapshots = sorted(
            (
                p
                for p in self.root.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ),
            reverse=True,
        )
        removed = 0
        for directory in snapshots[keep_last:]:
            shutil.rmtree(directory)
            removed += 1
        return removed

    def restore_latest(self, destination_root: str | Path = "artifacts") -> Path:
        snapshot = self.latest_valid()
        if snapshot is None:
            raise RuntimeError("no valid snapshot available")
        destination_root = Path(destination_root)
        destination_root.mkdir(parents=True, exist_ok=True)

        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        for name in manifest.get("files", {}):
            source = snapshot / name
            destination = destination_root / name
            temp = destination.with_suffix(destination.suffix + ".restore.tmp")
            shutil.copy2(source, temp)
            temp.replace(destination)
        return snapshot
