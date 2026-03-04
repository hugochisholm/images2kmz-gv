"""Tests for PlacemarkHtmlBuilder."""

import pytest

from images2kmz.image_processor import GPSData
from images2kmz.placemark_config import PlacemarkConfig
from images2kmz.placemark_html_builder import PlacemarkHtmlBuilder


class TestPlacemarkHtmlBuilder:
    """Tests for PlacemarkHtmlBuilder class."""

    @pytest.fixture
    def sample_gps_data(self):
        """Create sample GPS data for testing."""
        return GPSData(latitude=47.606209, longitude=-122.332069, altitude=10.0)

    @pytest.fixture
    def sample_bearing(self):
        """Create sample bearing data for testing."""
        return {'azimuth': 315.0, 'raw_text': 'NW (315°)'}

    def test_builder_default_creates_full_config(self):
        """Builder with no config should use default (all fields)."""
        builder = PlacemarkHtmlBuilder()
        assert builder.config.show_direction is True
        assert builder.config.show_location is True
        assert builder.config.show_photo_path is True
        assert builder.config.show_description is True

    def test_builder_accepts_custom_config(self):
        """Builder should accept custom PlacemarkConfig."""
        config = PlacemarkConfig(show_location=False)
        builder = PlacemarkHtmlBuilder(config)
        assert builder.config.show_location is False

    def test_build_includes_thumbnail(self, sample_gps_data):
        """HTML should include thumbnail image."""
        builder = PlacemarkHtmlBuilder()
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data
        )
        assert 'thumb.jpg' in html
        assert '<img' in html

    def test_build_with_all_fields_enabled(self, sample_gps_data, sample_bearing):
        """HTML should include all fields when enabled."""
        config = PlacemarkConfig()  # all True
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            description_text='Test description',
            bearing=sample_bearing
        )
        
        assert 'Direction:' in html
        assert 'Location:' in html
        assert 'Open Original Photo' in html
        assert 'Test description' in html

    def test_build_omits_direction_when_disabled(self, sample_gps_data, sample_bearing):
        """HTML should omit direction when disabled."""
        config = PlacemarkConfig(show_direction=False)
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            bearing=sample_bearing
        )
        
        assert 'Direction:' not in html
        assert 'Location:' in html

    def test_build_omits_location_when_disabled(self, sample_gps_data):
        """HTML should omit location when disabled."""
        config = PlacemarkConfig(show_location=False)
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data
        )
        
        assert 'Location:' not in html
        # Thumbnail should still be present
        assert 'thumb.jpg' in html

    def test_build_omits_photo_path_when_disabled(self, sample_gps_data):
        """HTML should omit photo path link when disabled."""
        config = PlacemarkConfig(show_photo_path=False)
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data
        )
        
        assert 'Open Original Photo' not in html

    def test_build_omits_description_when_disabled(self, sample_gps_data):
        """HTML should omit description when disabled."""
        config = PlacemarkConfig(show_description=False)
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            description_text='Test description'
        )
        
        assert 'Test description' not in html
        assert 'description' not in html.lower()

    def test_build_minimal_preset_no_info_card(self, sample_gps_data):
        """Minimal preset should not include info card."""
        config = PlacemarkConfig.from_preset('minimal')
        builder = PlacemarkHtmlBuilder(config)
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            description_text='Test description',
            bearing={'azimuth': 90.0, 'raw_text': 'E (90°)'}
        )
        
        # Thumbnail should be present
        assert 'thumb.jpg' in html
        # Info fields should not be present
        assert 'Direction:' not in html
        assert 'Location:' not in html
        assert 'Open Original Photo' not in html

    def test_build_uses_coordinates(self, sample_gps_data):
        """HTML should include correct GPS coordinates."""
        builder = PlacemarkHtmlBuilder()
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data
        )
        
        assert '47.606209' in html
        assert '-122.332069' in html

    def test_build_cdata_wrapped(self, sample_gps_data):
        """HTML should be wrapped in CDATA."""
        builder = PlacemarkHtmlBuilder()
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data
        )
        
        # CDATA should be present (may have leading whitespace)
        assert '<![CDATA[' in html
        assert ']]>' in html

    def test_build_handles_none_description(self, sample_gps_data):
        """Builder should handle None description gracefully."""
        builder = PlacemarkHtmlBuilder()
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            description_text=None
        )
        
        # Should not error, should just not include description
        assert 'thumb.jpg' in html

    def test_build_handles_none_bearing(self, sample_gps_data):
        """Builder should handle None bearing gracefully."""
        builder = PlacemarkHtmlBuilder()
        
        html = builder.build(
            embedded_path='files/thumb.jpg',
            abs_photo_path='/path/photo.jpg',
            gps_data=sample_gps_data,
            bearing=None
        )
        
        # Should include location but not direction
        assert 'Location:' in html
        assert 'Direction:' not in html


class TestPlacemarkHtmlBuilderStyles:
    """Tests for HTML styling in PlacemarkHtmlBuilder."""

    def test_build_inline_styles_returns_css(self):
        """build_inline_styles should return CSS string."""
        builder = PlacemarkHtmlBuilder()
        styles = builder.build_inline_styles()
        
        assert '<style>' in styles
        assert '.placemark-container' in styles
        assert '.info-card' in styles
        assert '.thumbnail' in styles
