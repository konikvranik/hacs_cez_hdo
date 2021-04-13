"""Adds config flow for HDO."""
import json
import logging
from collections import OrderedDict

import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_FORCE_UPDATE, CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import config_validation

from . import DOMAIN, DEFAULT_NAME, CONF_REFRESH_RATE, CONF_MAX_COUNT, CONF_STREET, _call_request

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
        if user_input is None:
            return await self._show_address_form(user_input)

        return await self.async_step_config(await self._load_addresses(user_input.get(CONF_ADDRESS)))

    async def async_step_config(self, user_input={}):  # pylint: disable=dangerous-default-value
        if user_input.get(CONF_NAME) is None:
            return await self._show_config_form(user_input)

        self._data.update(user_input)

        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def _load_addresses(self, addr):
        request = requests.Request(
            "GET", "https://api.bezstavy.cz/address/addressesAndTowns?q=%s" % addr).prepare()
        try:
            response = await self.hass.async_add_executor_job(_call_request, request)
            return json.loads(response.text)
        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)
            self.data = None



    async def _show_address_form(self, user_input):
        """Configure the form."""
        # Defaults
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_ADDRESS)] = str
        form = self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors)
        return form

    async def _show_config_form(self, user_input):
        """Configure the form."""
        all_repos = dict()
        for a in user_input.get("addresses"):
            all_repos[str(a["id"])] = "%s %s, %s" % (a["street"], a["houseNum"], a["town"])
        # Defaults
        data_schema = OrderedDict()
        data_schema[vol.Optional(CONF_NAME, default=DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_STREET, default=list(all_repos.keys()))] = config_validation.multi_select(
            all_repos)
        data_schema[vol.Optional(CONF_FORCE_UPDATE, default=True)] = bool
        data_schema[
            vol.Optional(CONF_REFRESH_RATE, default=86400)] = int
        data_schema[vol.Optional(CONF_MAX_COUNT, default=5)] = int
        form = self.async_show_form(step_id="config", data_schema=vol.Schema(data_schema), errors=self._errors)
        return form

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
        if config_entry.unique_id is not None:
            return OptionsFlowHandler(config_entry)
        else:
            return EmptyOptions(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the configuration."""

    def __init__(self, config_entry):
        """Read the configuration and initialize data."""
        self.config_entry = config_entry
        self._data = dict(config_entry.options)
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display the form, then store values and create entry."""

        if user_input is not None:
            # Update entry
            self._data.update(user_input)
            if CONF_REFRESH_RATE in user_input:
                self._data[CONF_REFRESH_RATE] = user_input[CONF_REFRESH_RATE]
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        else:
            return await self._show_init_form(user_input)

    async def _show_init_form(self, user_input):
        """Configure the form."""
        if user_input is None:
            user_input = self.config_entry.data
        data_schema = OrderedDict()
        data_schema[
            vol.Optional(CONF_NAME, default=user_input[CONF_NAME] if CONF_NAME in user_input else DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_FORCE_UPDATE, default=user_input[
            CONF_FORCE_UPDATE] if CONF_FORCE_UPDATE in user_input else True)] = bool
        data_schema[vol.Optional(CONF_REFRESH_RATE, default=user_input[
            CONF_REFRESH_RATE] if CONF_REFRESH_RATE in user_input else 86400)] = int
        data_schema[vol.Optional(CONF_MAX_COUNT,
                                 default=user_input[CONF_MAX_COUNT] if CONF_MAX_COUNT in user_input else 5)] = int
        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema), errors=self._errors)


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
