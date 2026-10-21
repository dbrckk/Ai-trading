from dataclasses import replace

import pytest

from ai_trading.online import RiverDirectionModel, RiverMulticlassDirectionModel


def test_model_codec_round_trip() -> None:
    from ai_trading.model_codec import deserialize_model, serialize_model

    blob = serialize_model(RiverDirectionModel())
    restored = deserialize_model(blob)
    assert blob.format == "joblib-river-v1"
    assert blob.version == 1
    assert len(blob.sha256) == 64
    assert type(restored) is RiverDirectionModel

    from ai_trading.research_model_codec import (
        deserialize_research_model,
        serialize_research_model,
    )

    research = RiverMulticlassDirectionModel()
    research_blob = serialize_research_model(research)
    research_restored = deserialize_research_model(research_blob)
    assert research_blob.format == "joblib-river-ovr-v2"
    assert research_blob.version == 2
    assert type(research_restored) is RiverMulticlassDirectionModel
    with pytest.raises(TypeError, match="production model"):
        serialize_model(research)
    with pytest.raises(ValueError, match="format/version"):
        deserialize_model(research_blob)
    with pytest.raises(ValueError, match="format/version"):
        deserialize_research_model(blob)


def test_model_codec_rejects_corrupt_payload() -> None:
    from ai_trading.model_codec import deserialize_model, serialize_model

    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="checksum"):
        deserialize_model(replace(blob, payload=blob.payload + b"x"))

    from ai_trading.research_model_codec import (
        deserialize_research_model,
        serialize_research_model,
    )

    research_blob = serialize_research_model(RiverMulticlassDirectionModel())
    with pytest.raises(ValueError, match="checksum"):
        deserialize_research_model(replace(research_blob, payload=research_blob.payload + b"x"))


def test_model_codec_rejects_unknown_version() -> None:
    from ai_trading.model_codec import deserialize_model, serialize_model

    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="format/version"):
        deserialize_model(replace(blob, version=99))

    from ai_trading.research_model_codec import (
        deserialize_research_model,
        serialize_research_model,
    )

    research_blob = serialize_research_model(RiverMulticlassDirectionModel())
    with pytest.raises(ValueError, match="format/version"):
        deserialize_research_model(replace(research_blob, version=1))
