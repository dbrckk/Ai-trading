from dataclasses import replace

import pytest

from ai_trading.model_codec import deserialize_model, serialize_model
from ai_trading.online import RiverDirectionModel


def test_model_codec_round_trip() -> None:
    blob = serialize_model(RiverDirectionModel())
    restored = deserialize_model(blob)
    assert blob.format == "joblib-river-v1"
    assert blob.version == 1
    assert len(blob.sha256) == 64
    assert isinstance(restored, RiverDirectionModel)


def test_model_codec_rejects_corrupt_payload() -> None:
    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="checksum"):
        deserialize_model(replace(blob, payload=blob.payload + b"x"))


def test_model_codec_rejects_unknown_version() -> None:
    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="format/version"):
        deserialize_model(replace(blob, version=99))
