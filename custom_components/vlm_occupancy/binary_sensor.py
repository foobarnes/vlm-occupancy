"""Binary sensor platform for VLM Occupancy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CAMERA_ENTITY_ID,
    CONF_DEBUG_CAPTURE,
    CONF_PROVIDER,
    DEFAULT_DEBUG_CAPTURE,
    DOMAIN,
)
from .coordinator import VLMOccupancyRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the configured occupancy binary sensor."""
    async_add_entities([VLMOccupancyBinarySensor(entry, entry.runtime_data)])


class VLMOccupancyBinarySensor(BinarySensorEntity):
    """Expose the most recent structured evaluation."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_has_entity_name = True
    _attr_name = "Bed occupancy"
    _attr_translation_key = "bed_occupancy"

    def __init__(self, entry: ConfigEntry, runtime: VLMOccupancyRuntime) -> None:
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="VLM Occupancy",
            model=entry.data[CONF_PROVIDER],
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the last evaluation found a person in bed."""
        if self._runtime.result is None:
            return None
        return self._runtime.result.in_bed

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return non-primary structured output and safe operational metadata."""
        result = self._runtime.result
        return {
            "wheelchair_parked": (
                result.wheelchair_parked if result is not None else None
            ),
            "confidence": result.confidence if result is not None else None,
            "reasoning": result.reasoning if result is not None else None,
            "last_evaluated": (
                self._runtime.last_evaluated.isoformat()
                if self._runtime.last_evaluated is not None
                else None
            ),
            "last_attempted": (
                self._runtime.last_attempted.isoformat()
                if self._runtime.last_attempted is not None
                else None
            ),
            "last_error": self._runtime.last_error,
            "debug_capture_enabled": self._entry.options.get(
                CONF_DEBUG_CAPTURE, DEFAULT_DEBUG_CAPTURE
            ),
            "debug_image_path": self._runtime.last_debug_image,
            "camera_entity_id": self._entry.data[CONF_CAMERA_ENTITY_ID],
            "provider": self._entry.data[CONF_PROVIDER],
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to runtime updates."""
        self.async_on_remove(self._runtime.add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
