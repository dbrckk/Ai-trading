from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

import pandas as pd


@dataclass(frozen=True)
class DatasetEvidence:
    rows: int
    first_timestamp: str
    last_timestamp: str
    columns: tuple[str, ...]
    data_hash: str


def build_dataset_evidence(df: pd.DataFrame) -> DatasetEvidence:
    if df.empty:
        raise ValueError("cannot fingerprint an empty dataset")
    normalized = df.copy()
    normalized.index = pd.to_datetime(normalized.index, utc=True)
    normalized = normalized.sort_index()
    columns = tuple(str(column) for column in normalized.columns)
    records = [
        [
            timestamp.isoformat(),
            *[
                None if pd.isna(value) else float(value)
                for value in row
            ],
        ]
        for timestamp, row in zip(
            normalized.index,
            normalized.loc[:, list(columns)].to_numpy(),
            strict=True,
        )
    ]
    payload = {
        "columns": columns,
        "records": records,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return DatasetEvidence(
        rows=len(normalized),
        first_timestamp=normalized.index[0].isoformat(),
        last_timestamp=normalized.index[-1].isoformat(),
        columns=columns,
        data_hash=sha256(canonical).hexdigest(),
    )


def dataset_evidence_hash(evidence: DatasetEvidence) -> str:
    canonical = json.dumps(
        asdict(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()
