"""VLM Bed & Wheelchair Occupancy Sensor integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_FORCE,
    CONF_API_KEYS,
    DOMAIN,
    PLATFORMS,
    SERVICE_EVALUATE,
)
from .coordinator import VLMOccupancyRuntime
from .vlm_client import VLMClientError

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_FORCE, default=False): cv.boolean,
    }
)
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {vol.Optional(CONF_API_KEYS, default={}): {cv.string: cv.string}}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration action."""
    hass.data[DOMAIN] = {
        CONF_API_KEYS: dict(config.get(DOMAIN, {}).get(CONF_API_KEYS, {}))
    }

    async def async_handle_evaluate(
        call: ServiceCall,
    ) -> dict[str, object] | None:
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        requested_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        if requested_id:
            entries = [entry for entry in entries if entry.entry_id == requested_id]
        if not entries:
            raise ServiceValidationError("No matching VLM Occupancy entry is loaded")

        results: dict[str, object] = {}
        for entry in entries:
            try:
                result = await entry.runtime_data.async_evaluate(
                    force=call.data[ATTR_FORCE]
                )
            except VLMClientError as err:
                raise ServiceValidationError(str(err)) from None
            results[entry.entry_id] = result.as_dict()
        return {"results": results} if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_EVALUATE,
        async_handle_evaluate,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one VLM Occupancy config entry."""
    runtime = VLMOccupancyRuntime.create(hass, entry)
    entry.runtime_data = runtime
    runtime.start()
    entry.async_on_unload(runtime.stop)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one VLM Occupancy config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    (CONF_API_KEYS,)
