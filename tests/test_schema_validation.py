"""Test structured metadata schema validation."""

import json
from pathlib import Path

import pytest
from jsonschema import validate, ValidationError

# Import the schema from step1_ocr
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from modal_etl.step1_ocr import PAGASA_JSON_SCHEMA


@pytest.fixture
def sample_valid_metadata():
    """Minimal valid metadata that satisfies the schema."""
    return {
        "bulletin_type": "TCA",
        "bulletin_number": 1,
        "storm": {
            "name": "TEST",
            "category": "Tropical Depression",
            "international_name": None,
            "wind_signal": None,
        },
        "issuance": {
            "datetime": "2025-01-01T00:00:00",
            "valid_until": None,
        },
        "current_position": {
            "latitude": 14.5,
            "longitude": 121.0,
            "reference": "East of Manila",
            "as_of": None,
        },
        "intensity": {
            "max_sustained_winds_kph": 45,
            "gusts_kph": 55,
        },
        "movement": {
            "direction": "Westward",
            "speed_kph": 20,
        },
        "forecast_positions": [
            {
                "hour": 24,
                "label": "24-hour forecast",
                "latitude": 14.6,
                "longitude": 120.5,
                "reference": "East of Manila Bay",
            }
        ],
        "affected_areas": {
            "signal_1": [],
            "signal_2": [],
            "signal_3": [],
            "signal_4": [],
            "signal_5": [],
            "rainfall_warning": [],
            "coastal_waters": None,
        },
        "storm_track_map": {
            "current_position_shown": True,
            "forecast_track_shown": True,
            "description": "Storm track map",
        },
        "confidence": 0.95,
    }


def test_schema_has_required_fields():
    """Verify schema defines all expected top-level fields."""
    required = PAGASA_JSON_SCHEMA.get("required", [])
    assert "bulletin_type" in required
    assert "storm" in required
    assert "issuance" in required
    assert "current_position" in required
    assert "intensity" in required
    assert "movement" in required
    assert "forecast_positions" in required
    assert "affected_areas" in required
    assert "storm_track_map" in required
    assert "confidence" in required


def test_valid_metadata_passes(sample_valid_metadata):
    """A properly structured metadata dict should validate."""
    validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_missing_required_field_fails(sample_valid_metadata):
    """Missing a required field should raise ValidationError."""
    del sample_valid_metadata["storm"]
    with pytest.raises(ValidationError):
        validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_invalid_bulletin_type_fails(sample_valid_metadata):
    """bulletin_type must be one of the enum values."""
    sample_valid_metadata["bulletin_type"] = "INVALID"
    with pytest.raises(ValidationError):
        validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_invalid_storm_category_fails(sample_valid_metadata):
    """storm.category must be one of the allowed categories."""
    sample_valid_metadata["storm"]["category"] = "Hurricane"
    with pytest.raises(ValidationError):
        validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_confidence_out_of_range_fails(sample_valid_metadata):
    """confidence must be between 0.0 and 1.0."""
    sample_valid_metadata["confidence"] = 1.5
    with pytest.raises(ValidationError):
        validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_forecast_positions_requires_hour_and_label(sample_valid_metadata):
    """Each forecast_position must have at least hour and label."""
    sample_valid_metadata["forecast_positions"] = [{"hour": 24}]  # missing label
    with pytest.raises(ValidationError):
        validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_null_values_allowed_for_optional_fields(sample_valid_metadata):
    """Many fields allow null as a valid value."""
    sample_valid_metadata["storm"]["international_name"] = None
    sample_valid_metadata["current_position"]["latitude"] = None
    sample_valid_metadata["intensity"]["max_sustained_winds_kph"] = None
    sample_valid_metadata["issuance"]["valid_until"] = None
    
    # Should still validate
    validate(instance=sample_valid_metadata, schema=PAGASA_JSON_SCHEMA)


def test_archived_files_do_not_match_schema():
    """Archived files from notebook experiments should fail validation.
    
    This test documents that old files have inconsistent schemas.
    """
    archive_dir = Path(__file__).parent.parent / "data" / "gemma4_results" / "structured_archive_20260412"
    
    if not archive_dir.exists():
        pytest.skip("Archive directory not found")
    
    json_files = list(archive_dir.glob("*.json"))
    if not json_files:
        pytest.skip("No archived JSON files found")
    
    # Pick the first archived file
    sample_file = json_files[0]
    with open(sample_file) as f:
        old_data = json.load(f)
    
    # This should fail validation because old files have different structure
    with pytest.raises(ValidationError):
        validate(instance=old_data, schema=PAGASA_JSON_SCHEMA)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
