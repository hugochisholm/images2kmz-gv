"""Tests for PlacemarkConfig."""

import pytest

from images2kmz.placemark_config import PlacemarkConfig


class TestPlacemarkConfigDefault:
    """Tests for default PlacemarkConfig behavior."""

    def test_default_has_all_fields_enabled(self):
        """Default config should have all fields enabled."""
        config = PlacemarkConfig()
        assert config.show_direction is True
        assert config.show_location is True
        assert config.show_photo_path is True
        assert config.show_description is True

    def test_has_any_fields_true_when_all_enabled(self):
        """has_any_fields should return True when all fields enabled."""
        config = PlacemarkConfig()
        assert config.has_any_fields() is True

    def test_has_any_fields_false_when_all_disabled(self):
        """has_any_fields should return False when all fields disabled."""
        config = PlacemarkConfig(
            show_direction=False,
            show_location=False,
            show_photo_path=False,
            show_description=False
        )
        assert config.has_any_fields() is False

    def test_to_fields_list_returns_all_fields(self):
        """to_fields_list should return all field names when all enabled."""
        config = PlacemarkConfig()
        fields = config.to_fields_list()
        assert 'direction' in fields
        assert 'location' in fields
        assert 'photo_path' in fields
        assert 'description' in fields
        assert len(fields) == 4


class TestPlacemarkConfigFromFieldsList:
    """Tests for PlacemarkConfig.from_fields_list()."""

    def test_from_fields_list_all(self):
        """from_fields_list(['all']) should enable all fields."""
        config = PlacemarkConfig.from_fields_list(['all'])
        assert config.show_direction is True
        assert config.show_location is True
        assert config.show_photo_path is True
        assert config.show_description is True

    def test_from_fields_list_none(self):
        """from_fields_list(['none']) should disable all fields."""
        config = PlacemarkConfig.from_fields_list(['none'])
        assert config.show_direction is False
        assert config.show_location is False
        assert config.show_photo_path is False
        assert config.show_description is False

    def test_from_fields_list_single_field(self):
        """from_fields_list with single field should enable only that field."""
        config = PlacemarkConfig.from_fields_list(['location'])
        assert config.show_location is True
        assert config.show_direction is False
        assert config.show_photo_path is False
        assert config.show_description is False

    def test_from_fields_list_multiple_fields(self):
        """from_fields_list with multiple fields should enable only those fields."""
        config = PlacemarkConfig.from_fields_list(['location', 'description'])
        assert config.show_location is True
        assert config.show_description is True
        assert config.show_direction is False
        assert config.show_photo_path is False

    def test_from_fields_list_case_insensitive(self):
        """from_fields_list should be case insensitive."""
        config = PlacemarkConfig.from_fields_list(['LOCATION', 'DESCRIPTION'])
        assert config.show_location is True
        assert config.show_description is True

    def test_from_fields_list_with_whitespace(self):
        """from_fields_list should handle whitespace in field names."""
        config = PlacemarkConfig.from_fields_list([' location , description '])
        assert config.show_location is True
        assert config.show_description is True

    def test_from_fields_list_invalid_field_raises(self):
        """from_fields_list should raise ValueError for invalid field."""
        with pytest.raises(ValueError) as exc_info:
            PlacemarkConfig.from_fields_list(['invalid_field'])
        assert "Unknown field 'invalid_field'" in str(exc_info.value)

    def test_from_fields_list_valid_fields_in_error_message(self):
        """Error message should list valid fields."""
        with pytest.raises(ValueError) as exc_info:
            PlacemarkConfig.from_fields_list(['bad'])
        assert 'direction' in str(exc_info.value)
        assert 'location' in str(exc_info.value)
        assert 'photo_path' in str(exc_info.value)
        assert 'description' in str(exc_info.value)


class TestPlacemarkConfigFromPreset:
    """Tests for PlacemarkConfig.from_preset()."""

    def test_from_preset_full(self):
        """from_preset('full') should enable all fields."""
        config = PlacemarkConfig.from_preset('full')
        assert config.show_direction is True
        assert config.show_location is True
        assert config.show_photo_path is True
        assert config.show_description is True

    def test_from_preset_minimal(self):
        """from_preset('minimal') should disable all info fields."""
        config = PlacemarkConfig.from_preset('minimal')
        assert config.show_direction is False
        assert config.show_location is False
        assert config.show_photo_path is False
        assert config.show_description is False

    def test_from_preset_client(self):
        """from_preset('client') should disable photo path only."""
        config = PlacemarkConfig.from_preset('client')
        assert config.show_direction is True
        assert config.show_location is True
        assert config.show_photo_path is False
        assert config.show_description is True

    def test_from_preset_none(self):
        """from_preset('none') should disable all fields."""
        config = PlacemarkConfig.from_preset('none')
        assert config.show_direction is False
        assert config.show_location is False
        assert config.show_photo_path is False
        assert config.show_description is False

    def test_from_preset_case_insensitive(self):
        """from_preset should be case insensitive."""
        config = PlacemarkConfig.from_preset('MINIMAL')
        assert config.show_direction is False

    def test_from_preset_invalid_raises(self):
        """from_preset should raise ValueError for invalid preset."""
        with pytest.raises(ValueError) as exc_info:
            PlacemarkConfig.from_preset('invalid_preset')
        assert "Unknown preset 'invalid_preset'" in str(exc_info.value)


class TestPlacemarkConfigToFieldsList:
    """Tests for PlacemarkConfig.to_fields_list()."""

    def test_to_fields_list_empty_when_all_disabled(self):
        """to_fields_list should return empty list when all disabled."""
        config = PlacemarkConfig.from_preset('none')
        assert config.to_fields_list() == []

    def test_to_fields_list_partial_fields(self):
        """to_fields_list should return only enabled fields."""
        config = PlacemarkConfig(
            show_direction=True,
            show_location=False,
            show_photo_path=True,
            show_description=False
        )
        fields = config.to_fields_list()
        assert 'direction' in fields
        assert 'location' not in fields
        assert 'photo_path' in fields
        assert 'description' not in fields

    def test_to_fields_list_order(self):
        """to_fields_list should return fields in consistent order."""
        config = PlacemarkConfig(
            show_direction=True,
            show_location=True,
            show_photo_path=False,
            show_description=False
        )
        fields = config.to_fields_list()
        assert fields == ['direction', 'location']
