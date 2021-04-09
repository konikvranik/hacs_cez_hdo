"""Adds config flow for HDO."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CODE
from homeassistant.core import callback

from . import DOMAIN
from .binary_sensor import PLATFORM_SCHEMA

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class HDOFlowHandler(config_entries.ConfigFlow):
    """Config flow for HDO."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._data = {}

    async def async_step_user(self, user_input={}):  # pylint: disable=dangerous-default-value
        """Display the form, then store values and create entry."""
        self._errors = {}
        if user_input is not None:
            if user_input[CONF_CODE] != "":
                # Remember Frequency
                self._data.update(user_input)
                # Call next step
                return self.async_create_entry(title=self._data["code"], data=self._data)
            else:
                self._errors["base"] = "code"
        return await self._show_user_form(user_input)

    async def _show_user_form(self, user_input):
        """Configure the form."""
        # Defaults
        code = ""
        if user_input is not None:
            if CONF_CODE in user_input:
                code = user_input[CONF_CODE]
        data_schema = PLATFORM_SCHEMA
        data_schema[vol.Required(CONF_CODE, default=code)] = str
        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors)

    async def async_step_import(self, user_input):  # pylint: disable=unused-argument
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        if config_entry.options.get("code", None) is not None:
            return OptionsFlowHandler(config_entry)
        else:
            return EmptyOptions(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the configuration."""

    def __init__(self, config_entry):
        """Read the configuration and initialize data."""
        self.config_entry = config_entry
        self._data = config_entry.options
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display the form, then store values and create entry."""

        if user_input is not None:
            # Update entry
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        return await self._show_init_form(user_input)

    async def _show_init_form(self, user_input):
        """Configure the form."""
        data_schema = PLATFORM_SCHEMA
        data_schema[vol.Required(CONF_CODE, default=self.config_entry.options.get(CONF_CODE))] = str
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(data_schema), errors=self._errors
        )


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
