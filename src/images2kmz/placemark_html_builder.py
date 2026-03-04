from __future__ import annotations

"""HTML builder for placemark info cards."""

import logging

from .image_processor import GPSData
from .placemark_config import PlacemarkConfig
from .utils import create_file_uri

logger = logging.getLogger(__name__)


class PlacemarkHtmlBuilder:
    """Builds HTML for placemark info card.

    Generates HTML descriptions for KML placemarks based on
    a PlacemarkConfig to control which fields are displayed.
    """

    def __init__(self, config: PlacemarkConfig | None = None):
        """Initialize builder with optional config.

        Args:
            config: Field visibility config. Defaults to full config (all fields shown).
        """
        self.config = config or PlacemarkConfig()

    def build(
        self,
        embedded_path: str,
        abs_photo_path: str,
        gps_data: GPSData,
        description_text: str | None = None,
        bearing: dict | None = None,
    ) -> str:
        """Generate HTML description for placemark.

        Uses config to determine which fields to include in the info card.

        Args:
            embedded_path: Path to thumbnail within KMZ archive.
            abs_photo_path: Absolute path to original photo file.
            gps_data: GPS coordinates for the photo.
            description_text: Optional EXIF description text.
            bearing: Optional compass bearing data with 'raw_text' and 'azimuth' keys.

        Returns:
            HTML string wrapped in CDATA for KML compatibility.
        """
        # Build info rows based on config
        info_rows = []

        # Direction (compass bearing)
        if self.config.show_direction and bearing and bearing.get('raw_text'):
            info_rows.append(
                f'<div class="info-row">'
                f'<span class="info-label">Direction:</span>'
                f'<span class="info-value">{bearing["raw_text"]}</span>'
                f'</div>'
            )

        # Location (coordinates)
        if self.config.show_location:
            info_rows.append(
                f'<div class="info-row">'
                f'<span class="info-label">Location:</span>'
                f'<span class="info-value coords">{gps_data.latitude:.6f}, {gps_data.longitude:.6f}</span>'
                f'</div>'
            )

        # Photo path link
        if self.config.show_photo_path:
            info_rows.append(
                f'<div class="info-row photo-link">'
                f'<a href="{create_file_uri(abs_photo_path)}" target="_blank">Open Original Photo</a>'
                f'</div>'
            )

        info_section = ''
        if info_rows:
            info_section = f'''
            <div class="info-card">
                {''.join(info_rows)}
            </div>
            '''

        # Description block
        description_section = ''
        if self.config.show_description and description_text:
            formatted_desc = description_text.replace(' - ', '<br/>')
            description_section = f'''
            <div class="description-block">
                {formatted_desc}
            </div>
            '''

        # Build complete HTML
        html = f'''
<![CDATA[
<div class="placemark-container">
    <div class="thumbnail-wrapper">
        <img src="{embedded_path}" class="thumbnail" />
    </div>
    
    {description_section}
    {info_section}
</div>
]]>
'''
        return html

    def build_inline_styles(self) -> str:
        """Return inline CSS styles for the placemark HTML.

        These styles are embedded directly in the HTML for maximum
        compatibility with KML viewers.

        Returns:
            CSS string to be embedded in style tag.
        """
        return '''
<style>
.placemark-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    max-width: 800px;
    color: #212529;
}

.thumbnail-wrapper {
    text-align: center;
    background: #1a1a1a;
    padding: 8px;
    border-radius: 8px;
    margin-bottom: 12px;
}

.thumbnail {
    max-width: 100%;
    max-height: 500px;
    border-radius: 4px;
    display: block;
    margin: 0 auto;
}

.description-block {
    font-weight: 600;
    font-size: 1.1em;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 2px solid #007bff;
    color: #212529;
    line-height: 1.4;
}

.info-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 14px;
    border: 1px solid #e9ecef;
}

.info-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
    font-size: 0.95em;
    line-height: 1.4;
}

.info-row + .info-row {
    border-top: 1px solid #e9ecef;
}

.info-label {
    color: #6c757d;
    min-width: 80px;
    flex-shrink: 0;
}

.info-value {
    color: #212529;
    word-break: break-word;
}

.info-value.coords {
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', 'Droid Sans Mono', monospace;
    font-size: 0.9em;
}

.photo-link {
    margin-top: 8px;
    padding-top: 8px !important;
    border-top: 1px solid #e9ecef !important;
}

.photo-link a {
    color: #007bff;
    text-decoration: none;
    font-weight: 500;
}

.photo-link a:hover {
    text-decoration: underline;
}
</style>
'''
