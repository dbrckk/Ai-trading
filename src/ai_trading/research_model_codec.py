"""Versioned River-v2 research codec, isolated from paper production storage.

This module is opt-in for offline and read-only shadow studies only.
The production model_codec continues to accept *only* joblib-river-v1.
Joblib deserialization is unsafe for untrusted payloads; only load artifacts
from a trusted research run, never remote or user-supplied model blobs.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

import joblib

from .online import RiverMulticlassDirectionModel
from .persistence import ModelBlob

RESEARCH_MODEL_FORMAT = "joblib-river-ovr-v2"
RESEARCH_MODEL_VERSION = 2


def serialize_research_model(model: RiverMulticlassDirectionModel) -> ModelBlob:
    """Serialize a ternary River challenger without using the production codec."""
    if type(model) is not RiverMulticlassDirectionModel:
        raise TypeError("research model must be exactly RiverMulticlassDirectionModel")
    buffer = BytesIO()
    joblib.dump(model, buffer)
    payload = buffer.getvalue()
    return ModelBlob(
        format=RESEARCH_MODEL_FORMAT,
        version=RESEARCH_MODEL_VERSION,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def deserialize_research_model(blob: ModelBlob) -> RiverMulticlassDirectionModel:
    """Load only a trusted, versioned v2 challenger blob; never accept v1."""
    if blob.format != RESEARCH_MODEL_FORMAT or blob.version != RESEARCH_MODEL_VERSION:
        raise ValueError("unsupported research model format/version")
    if hashlib.sha256(blob.payload).hexdigest() != blob.sha256:
        raise ValueError("research model checksum mismatch")
    model = joblib.load(BytesIO(blob.payload))
    if type(model) is not RiverMulticlassDirectionModel:
        raise TypeError("persisted research model has unexpected type")
    return model
