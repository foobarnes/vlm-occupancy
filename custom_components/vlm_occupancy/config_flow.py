"""Config flow for VLM Occupancy."""

from __future__ import annotations

import os
import re
from typing import Any

import voluptuous as vol
from yarl import URL

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_API_KEYS,
    CONF_CAMERA_ENTITY_ID,
    CONF_CREDENTIAL_NAME,
    CONF_COOLDOWN,
    CONF_DEBUG_CAPTURE,
    CONF_ENDPOINT,
    CONF_END_TIME,
    CONF_MODEL,
    CONF_MOTION_ENTITY_ID,
    CONF_POLL_INTERVAL,
    CONF_PROMPT,
    CONF_PROVIDER,
    CONF_START_TIME,
    DEFAULT_CREDENTIAL_NAMES,
    DEFAULT_COOLDOWN,
    DEFAULT_DEBUG_CAPTURE,
    DEFAULT_ENDPOINTS,
    DEFAULT_END_TIME,
    DEFAULT_MODELS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PROMPT,
    DEFAULT_START_TIME,
    DOMAIN,
    MAX_PROMPT_LENGTH,
    PROVIDER_OLLAMA,
    PROVIDERS,
)

ENV_VAR_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class VLMOccupancyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a VLM Occupancy config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._base: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VLMOccupancyOptionsFlow:
        """Create the editable prompt options flow."""
        return VLMOccupancyOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the camera and provider first."""
        if user_input is not None:
            self._base = user_input
            return await self.async_step_provider()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Bedroom Occupancy"): str,
                vol.Required(CONF_CAMERA_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="camera")
                ),
                vol.Required(
                    CONF_PROVIDER, default=PROVIDER_OLLAMA
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(PROVIDERS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="provider",
                    )
                ),
                vol.Optional(CONF_MOTION_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect provider and gating details without collecting a secret."""
        provider = self._base[CONF_PROVIDER]
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _valid_endpoint(
                user_input[CONF_ENDPOINT], require_https=provider != PROVIDER_OLLAMA
            ):
                errors[CONF_ENDPOINT] = "invalid_endpoint"
            credential_name = user_input.get(CONF_CREDENTIAL_NAME, "").strip()
            yaml_keys = self.hass.data.get(DOMAIN, {}).get(CONF_API_KEYS, {})
            if credential_name and not ENV_VAR_PATTERN.fullmatch(credential_name):
                errors[CONF_CREDENTIAL_NAME] = "invalid_credential_name"
            elif credential_name and not (
                yaml_keys.get(credential_name) or os.environ.get(credential_name)
            ):
                errors[CONF_CREDENTIAL_NAME] = "credential_missing"
            elif provider != PROVIDER_OLLAMA and not credential_name:
                errors[CONF_CREDENTIAL_NAME] = "api_key_required"

            prompt = user_input[CONF_PROMPT].strip()
            if not prompt or len(prompt) > MAX_PROMPT_LENGTH:
                errors[CONF_PROMPT] = "invalid_prompt"

            if not errors:
                user_input[CONF_PROMPT] = prompt
                data = {**self._base, **user_input}
                unique_id = f"{data[CONF_CAMERA_ENTITY_ID]}:{data[CONF_PROVIDER]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data.pop(CONF_NAME),
                    data=data,
                )

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENDPOINT,
                    default=defaults.get(CONF_ENDPOINT, DEFAULT_ENDPOINTS[provider]),
                ): str,
                vol.Required(
                    CONF_MODEL,
                    default=defaults.get(CONF_MODEL, DEFAULT_MODELS[provider]),
                ): str,
                vol.Optional(
                    CONF_CREDENTIAL_NAME,
                    default=defaults.get(
                        CONF_CREDENTIAL_NAME, DEFAULT_CREDENTIAL_NAMES[provider]
                    ),
                ): str,
                vol.Required(
                    CONF_START_TIME,
                    default=defaults.get(CONF_START_TIME, DEFAULT_START_TIME),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_END_TIME,
                    default=defaults.get(CONF_END_TIME, DEFAULT_END_TIME),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=1440,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    CONF_COOLDOWN,
                    default=defaults.get(CONF_COOLDOWN, DEFAULT_COOLDOWN),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_PROMPT,
                    default=defaults.get(CONF_PROMPT, DEFAULT_PROMPT),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(
            step_id="provider", data_schema=schema, errors=errors
        )


class VLMOccupancyOptionsFlow(config_entries.OptionsFlowWithReload):
    """Allow prompt iteration and opt-in diagnostics."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the prompt and privacy-sensitive diagnostic options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            prompt = user_input[CONF_PROMPT].strip()
            if not prompt or len(prompt) > MAX_PROMPT_LENGTH:
                errors[CONF_PROMPT] = "invalid_prompt"
            else:
                return self.async_create_entry(
                    data={
                        CONF_PROMPT: prompt,
                        CONF_DEBUG_CAPTURE: user_input[CONF_DEBUG_CAPTURE],
                    }
                )

        current_prompt = self.config_entry.options.get(
            CONF_PROMPT,
            self.config_entry.data.get(CONF_PROMPT, DEFAULT_PROMPT),
        )
        current_debug_capture = self.config_entry.options.get(
            CONF_DEBUG_CAPTURE, DEFAULT_DEBUG_CAPTURE
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROMPT,
                    default=current_prompt,
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Required(
                    CONF_DEBUG_CAPTURE,
                    default=current_debug_capture,
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


def _valid_endpoint(value: str, *, require_https: bool = False) -> bool:
    """Accept an endpoint without embedded credentials or query parameters."""
    try:
        url = URL(value)
    except (TypeError, ValueError):
        return False
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return (
        url.scheme in allowed_schemes
        and bool(url.host)
        and url.user is None
        and url.password is None
        and not url.query
        and not url.fragment
    )
