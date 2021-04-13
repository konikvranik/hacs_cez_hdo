import logging

import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_VERIFY_SSL, CONF_FORCE_UPDATE
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType
from integrationhelper.const import CC_STARTUP_VERSION
from voluptuous import ALLOW_EXTRA

CONF_PARCEL_NO = "parcelNo"
CONF_STREET_NO = "streetNo"
CONF_STREET = "street"
CONF_REFRESH_RATE = 'refreshRate'
CONF_MAX_COUNT = 'maxCount'

DOMAIN = "cez_outages"
VERSION = "0.1.0"
PLATFORM = "binary_sensor"
DEFAULT_METHOD = 'GET'
DEFAULT_NAME = 'JSON REST Sensor'
DEFAULT_VERIFY_SSL = True
ISSUE_URL = "https://github.com/konikvranik/hacs_cez/issues"
SCHEMA = {
    vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_STREET): cv.ensure_list(vol.Any(list, cv.string)),
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    vol.Optional(CONF_FORCE_UPDATE, default=True): cv.boolean,
    vol.Optional(CONF_REFRESH_RATE, default=86400): vol.All(vol.Coerce(int)),
    vol.Optional(CONF_MAX_COUNT, default=5): vol.All(vol.Coerce(int)),
}
SERVICE = 'refresh'

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    """Set up ESPHome binary sensors based on a config entry."""
    _LOGGER.debug(entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(entry.data)})
    _LOGGER.debug(config)

    # Register our service with Home Assistant.
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, PLATFORM))
    # Return boolean to indicate that initialization was successfully.
    return True


async def platform_async_setup_entry(
        hass: HomeAssistantType,
        config_entry: ConfigEntry,
        async_add_entities,
        *,
        component_key: str,
        info_type,
        entity_type,
        state_type,
) -> bool:
    """Set up this integration using UI."""
    if config_entry.source == config_entries.SOURCE_IMPORT:
        # We get here if the integration is set up using YAML
        hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
        return False
    # Print startup message
    _LOGGER.info(CC_STARTUP_VERSION.format(name=DOMAIN, version=VERSION, issue_link=ISSUE_URL))
    config_entry.options = config_entry.data
    config_entry.add_update_listener(update_listener)
    # Add sensor
    return await hass.config_entries.async_forward_entry_setup(config_entry, PLATFORM)


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, PLATFORM)
        _LOGGER.info("Successfully removed sensor from the HDO integration")
    except ValueError:
        pass


async def update_listener(hass, entry):
    """Update listener."""
    entry.data = entry.options
    await hass.config_entries.async_forward_entry_unload(entry, PLATFORM)
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, PLATFORM))


def _call_request(request):
    with requests.Session() as sess:
        return sess.send(request, timeout=10)
