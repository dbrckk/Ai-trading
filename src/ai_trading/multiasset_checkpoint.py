from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zlib
from dataclasses import asdict
from pathlib import Path

import joblib

from .multiasset_state import AssetPosition, MultiAssetState


class MultiAssetCheckpointStore:
    """Checkpoint portfolio state and online models as one durable generation."""

    def __init__(self, root: str | Path, *, retain_generations: int = 3) -> None:
        if retain_generations < 1:
            raise ValueError("retain_generations must be at least 1")
        self.root = Path(root)
        self.current_path = self.root / "CURRENT"
        self.retain_generations = retain_generations

    def _generation_dir(self, generation: str) -> Path:
        return self.root / self._validate_generation(generation)

    @staticmethod
    def _validate_generation(generation: str) -> str:
        if re.fullmatch(r"step-\d{12}", generation) is None:
            raise ValueError("invalid multiasset checkpoint generation")
        return generation

    @staticmethod
    def _model_filename(symbol: str) -> str:
        digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:16]
        return f"model-{digest}.joblib"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


    @staticmethod
    def _fsync_file(path: Path) -> None:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            # Directory fsync is not supported on every platform/filesystem.
            return
        finally:
            os.close(descriptor)

    @staticmethod
    def _artifact_path(directory: Path, filename: object) -> Path:
        if not isinstance(filename, str) or not filename:
            raise ValueError("invalid multiasset checkpoint artifact path")
        candidate = Path(filename)
        if candidate.name != filename or filename in {".", ".."}:
            raise ValueError("invalid multiasset checkpoint artifact path")
        return directory / filename


    @staticmethod
    def _metadata_dict(value: object, *, label: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValueError(f"invalid multiasset checkpoint {label} metadata")
        return value

    @staticmethod
    def _checksum(value: object, *, label: str) -> str:
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9a-f]{64}", value) is None
        ):
            raise ValueError(f"invalid multiasset checkpoint {label} checksum")
        return value

    def commit(self, state: MultiAssetState, models: dict[str, object]) -> str:
        generation = self._validate_generation(f"step-{state.processed_bars:012d}")
        final_dir = self._generation_dir(generation)
        temp_dir = self.root / f".{generation}.tmp"
        self.root.mkdir(parents=True, exist_ok=True)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        state_path = temp_dir / "state.json"
        state_path.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        self._fsync_file(state_path)
        model_files: dict[str, str] = {}
        for symbol, model in sorted(models.items()):
            filename = self._model_filename(symbol)
            model_path = temp_dir / filename
            joblib.dump(model, model_path)
            self._fsync_file(model_path)
            model_files[symbol] = filename

        manifest = {
            "generation": generation,
            "processed_bars": state.processed_bars,
            "last_processed": state.last_processed,
            "state": {"file": "state.json", "sha256": self._sha256(state_path)},
            "models": {
                symbol: {"file": filename, "sha256": self._sha256(temp_dir / filename)}
                for symbol, filename in model_files.items()
            },
        }
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )
        self._fsync_file(manifest_path)
        self._fsync_directory(temp_dir)
        if final_dir.exists():
            shutil.rmtree(temp_dir)
            raise ValueError(f"multiasset checkpoint already exists: {generation}")
        temp_dir.replace(final_dir)
        self._fsync_directory(self.root)
        self._publish_current(generation)
        self._prune_old_generations_best_effort(current=generation)
        return generation

    def _publish_current(self, generation: str) -> None:
        pointer_tmp = self.current_path.with_suffix(".tmp")
        pointer_tmp.write_text(generation, encoding="utf-8")
        self._fsync_file(pointer_tmp)
        pointer_tmp.replace(self.current_path)
        self._fsync_directory(self.root)

    def _prune_old_generations(self, *, current: str) -> None:
        generations = sorted(
            path for path in self.root.glob("step-*")
            if path.is_dir() and path.name != current
        )
        removable = max(0, len(generations) - (self.retain_generations - 1))
        for path in generations[:removable]:
            shutil.rmtree(path)

    def _prune_old_generations_best_effort(self, *, current: str) -> None:
        try:
            self._prune_old_generations(current=current)
        except OSError:
            # CURRENT is already authoritative at this point. Retention cleanup
            # must not make a successfully published checkpoint look failed.
            return

    def _load_generation(self, generation: str) -> tuple[MultiAssetState, dict[str, object]]:
        directory = self._generation_dir(generation)
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("invalid multiasset checkpoint manifest")
        if manifest.get("generation") != generation:
            raise ValueError("multiasset checkpoint generation mismatch")

        state_meta = self._metadata_dict(
            manifest.get("state"),
            label="state",
        )
        state_path = self._artifact_path(directory, state_meta.get("file"))
        state_checksum = self._checksum(
            state_meta.get("sha256"),
            label="state",
        )
        if self._sha256(state_path) != state_checksum:
            raise ValueError("multiasset checkpoint state checksum mismatch")
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid multiasset checkpoint state payload")
        positions = payload.get("positions", {})
        if not isinstance(positions, dict):
            raise ValueError("invalid multiasset checkpoint positions")
        normalized_positions: dict[str, AssetPosition] = {}
        for symbol, position in positions.items():
            if not isinstance(symbol, str) or not isinstance(position, dict):
                raise ValueError("invalid multiasset checkpoint position")
            normalized_positions[symbol] = AssetPosition(**position)
        payload["positions"] = normalized_positions
        state = MultiAssetState(**payload)
        expected_generation = self._validate_generation(f"step-{state.processed_bars:012d}")
        if expected_generation != generation:
            raise ValueError("multiasset checkpoint state generation mismatch")
        if manifest.get("processed_bars") != state.processed_bars:
            raise ValueError("multiasset checkpoint processed bars mismatch")
        if manifest.get("last_processed") != state.last_processed:
            raise ValueError("multiasset checkpoint last processed mismatch")

        raw_models = manifest.get("models", {})
        if not isinstance(raw_models, dict):
            raise ValueError("invalid multiasset checkpoint models metadata")
        models: dict[str, object] = {}
        for symbol, raw_metadata in raw_models.items():
            if not isinstance(symbol, str) or not symbol:
                raise ValueError("invalid multiasset checkpoint model symbol")
            metadata = self._metadata_dict(
                raw_metadata,
                label=f"model {symbol}",
            )
            path = self._artifact_path(directory, metadata.get("file"))
            expected_filename = self._model_filename(symbol)
            if path.name != expected_filename:
                raise ValueError(
                    f"multiasset checkpoint model filename mismatch: {symbol}"
                )
            expected_checksum = self._checksum(
                metadata.get("sha256"),
                label=f"model {symbol}",
            )
            if self._sha256(path) != expected_checksum:
                raise ValueError(
                    f"multiasset checkpoint model checksum mismatch: {symbol}"
                )
            models[symbol] = joblib.load(path)
        return state, models

    def _newer_valid_generation(self, current: str | None) -> str | None:
        candidates = sorted(
            path.name for path in self.root.glob("step-*")
            if path.is_dir() and (current is None or path.name > current)
        )
        for generation in reversed(candidates):
            try:
                self._load_generation(generation)
            except (
                EOFError,
                FileNotFoundError,
                IndexError,
                KeyError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
                zlib.error,
            ):
                continue
            return generation
        return None

    def load(self) -> tuple[MultiAssetState, dict[str, object]] | None:
        current: str | None = None
        if self.current_path.exists():
            current = self.current_path.read_text(encoding="utf-8").strip()
            if not current:
                raise ValueError("multiasset checkpoint pointer is empty")
            current = self._validate_generation(current)
            loaded = self._load_generation(current)
        else:
            loaded = None

        recovered = self._newer_valid_generation(current)
        if recovered is not None:
            self._publish_current(recovered)
            self._prune_old_generations_best_effort(current=recovered)
            return self._load_generation(recovered)

        return loaded
