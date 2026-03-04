from __future__ import annotations

"""Placemark configuration for controlling info card fields."""

from dataclasses import dataclass


# Valid field names for configuration
VALID_FIELDS = frozenset({'direction', 'location', 'photo_path', 'description', 'all', 'none'})

# Valid preset names
VALID_PRESETS = frozenset({'full', 'minimal', 'client', 'none'})


@dataclass
class PlacemarkConfig:
    """Configuration for placemark info card fields.

    Controls which fields are displayed in the placemark popup
    when viewing photos in Google Earth or similar KML viewers.

    Attributes:
        show_direction: Whether to show compass bearing/direction
        show_location: Whether to show latitude/longitude coordinates
        show_photo_path: Whether to show link to original photo
        show_description: Whether to show EXIF description text
    """

    show_direction: bool = True
    show_location: bool = True
    show_photo_path: bool = True
    show_description: bool = True

    @classmethod
    def from_fields_list(cls, fields: list[str]) -> PlacemarkConfig:
        """Create config from list of field names.

        Args:
            fields: List of field names like ['location', 'description']
                    Use 'all' to enable all fields or 'none' to disable all.

        Returns:
            PlacemarkConfig instance with specified fields enabled.

        Raises:
            ValueError: If unknown field name is provided.
        """
        normalized = []
        for f in fields:
            # Handle both comma-separated strings and list items
            for item in f.split(','):
                normalized.append(item.strip().lower())

        # Validate all fields
        for field in normalized:
            if field not in VALID_FIELDS:
                raise ValueError(
                    f"Unknown field '{field}'. Valid fields: {', '.join(sorted(VALID_FIELDS))}"
                )

        # Handle 'all' or 'none'
        if 'all' in normalized:
            return cls(
                show_direction=True,
                show_location=True,
                show_photo_path=True,
                show_description=True,
            )

        if 'none' in normalized:
            return cls(
                show_direction=False,
                show_location=False,
                show_photo_path=False,
                show_description=False,
            )

        # Build config from explicit list
        return cls(
            show_direction='direction' in normalized,
            show_location='location' in normalized,
            show_photo_path='photo_path' in normalized,
            show_description='description' in normalized,
        )

    @classmethod
    def from_preset(cls, preset: str) -> PlacemarkConfig:
        """Create config from preset name.

        Args:
            preset: Preset name - 'full', 'minimal', 'client', or 'none'

        Returns:
            PlacemarkConfig instance configured for the preset.

        Raises:
            ValueError: If unknown preset name is provided.
        """
        normalized = preset.lower().strip()

        if normalized not in VALID_PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. Valid presets: {', '.join(sorted(VALID_PRESETS))}"
            )

        # Full: all fields enabled (default)
        if normalized == 'full':
            return cls(
                show_direction=True,
                show_location=True,
                show_photo_path=True,
                show_description=True,
            )

        # Minimal: thumbnail only, no info fields
        if normalized == 'minimal':
            return cls(
                show_direction=False,
                show_location=False,
                show_photo_path=False,
                show_description=False,
            )

        # Client: location + description, no photo path (safe for external sharing)
        if normalized == 'client':
            return cls(
                show_direction=True,
                show_location=True,
                show_photo_path=False,
                show_description=True,
            )

        # None: all fields disabled
        if normalized == 'none':
            return cls(
                show_direction=False,
                show_location=False,
                show_photo_path=False,
                show_description=False,
            )

        # Should not reach here, but default to full
        return cls()

    def to_fields_list(self) -> list[str]:
        """Return list of enabled field names.

        Returns:
            List of field names that are enabled (e.g., ['location', 'direction'])
        """
        fields = []
        if self.show_direction:
            fields.append('direction')
        if self.show_location:
            fields.append('location')
        if self.show_photo_path:
            fields.append('photo_path')
        if self.show_description:
            fields.append('description')
        return fields

    def has_any_fields(self) -> bool:
        """Check if any info fields are enabled.

        Returns:
            True if at least one field is shown, False otherwise.
        """
        return any([
            self.show_direction,
            self.show_location,
            self.show_photo_path,
            self.show_description,
        ])
