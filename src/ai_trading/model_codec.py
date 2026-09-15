from __future__ import annotations

import hashlib
from io import BytesIO

import joblib

from .online import RiverDirectionModel
from .persistence import ModelBlob

MODEL_FORMAT = "joblib-river-v1"
MODEL_VERSION = 1


def serialize_model(model: RiverDirectionModel) -> ModelBlob:
    buffer = BytesIO()
    joblib.dump(model, buffer)
    payload = buffer.getvalue()
    return ModelBlob(
        format=MODEL_FORMAT,
        version=MODEL_VERSION,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def deserialize_model(blob: ModelBlob) -> RiverDirectionModel:
    if blob.format != MODEL_FORMAT or blob.version != MODEL_VERSION:
        raise ValueError("unsupported model format/version")
    if hashlib.sha256(blob.payload).hexdigest() != blob.sha256:
        raise ValueError("model checksum mismatch")
    model = joblib.load(BytesIO(blob.payload))
    if not isinstance(model, RiverDirectionModel):
        raise ValueError("persisted model has unexpected type")
    return model
