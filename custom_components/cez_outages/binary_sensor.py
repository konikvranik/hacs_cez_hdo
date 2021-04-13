"""
Support for RESTful API sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
Modified to parse a JSON reply and store data as attributes
"""
import json
import logging
import re

import requests
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, STATE_UNKNOWN, CONF_RESOURCE, CONF_METHOD,
    CONF_VERIFY_SSL, CONF_PAYLOAD, CONF_HEADERS, STATE_OFF, STATE_ON)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from . import CONF_STREET, CONF_STREET_NO, CONF_PARCEL_NO, CONF_REFRESH_RATE, SCHEMA

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(SCHEMA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config, async_add_entities):
    """Set up ESPHome binary sensors based on a config entry."""
    config = config.data
    name = config.get(CONF_NAME)
    url = config.get(CONF_RESOURCE, "https://api.bezstavy.cz/cezd/api/inspectaddress/%s")
    method = config.get(CONF_METHOD, "GET")
    payload = config.get(CONF_PAYLOAD, '{"ulice":"","mesto":"Statenice","psc":""}')
    verify_ssl = config.get(CONF_VERIFY_SSL, True)
    auth = None
    rest = []
    for r in config[CONF_STREET]:
        client = JSONRestClient(method, url % r, auth, None, payload, verify_ssl)
        rest.append(client)
        await hass.async_add_executor_job(client.update)

    async_add_entities([JSONRestSensor(hass, rest, name, config.get(CONF_STREET), config.get(CONF_STREET_NO),
                                       config.get(CONF_PARCEL_NO), config.get(CONF_REFRESH_RATE))])


def anymatch(value, patterns):
    for x in cv.ensure_list(patterns):
        _LOGGER.debug("matching %s against %s", value, x)
        r = re.search(x, value)
        if r:
            _LOGGER.debug("Matched %s", r)
            return r.group(0)
    return False


class JSONRestSensor(Entity):
    """Implementation of a REST sensor."""

    def __init__(self, hass, rest, name, streets, street_numbers, parcel_numbers, refresh_rate):
        """Initialize the REST sensor."""
        self._street_numbers = street_numbers
        self._streets = streets if streets else '.*'
        self._hass = hass
        self.rest = rest
        self._name = name
        self._attributes = {}
        self._state = STATE_UNKNOWN
        self._parcel_numbers = parcel_numbers

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def update(self):
        """Get the latest data from REST API and update the state."""
        outages = []
        outages_in_town = []
        for r in self.rest:
            self._hass.async_add_executor_job(r.update)
            value = r.data
            outages += value["outages"]
            outages_in_town += value["outages_in_town"]
            _LOGGER.debug("Raw REST data: %s" % value)

        self._attributes['outages'] = outages
        self._attributes['outages_in_town'] = outages_in_town
        self._attributes['times'] = list(map(lambda x: x["opened_at"], outages))

        self._state = STATE_ON if outages else STATE_OFF

    @property
    def state_attributes(self):
        """Return the attributes of the entity.
           Provide the parsed JSON data (if any).
        """

        return self._attributes


class JSONRestClient(object):
    """Class for handling the data retrieval."""

    def __init__(self, method, resource, auth, headers, data, verify_ssl):
        """Initialize the data object."""
        self._request = requests.Request(
            method, resource, headers=headers, auth=auth, data=data).prepare()
        self._verify_ssl = verify_ssl
        self.data = None

    def update(self):
        """Get the latest data from REST service with provided method."""
        try:
            with requests.Session() as sess:
                response = sess.send(
                    self._request, timeout=10, verify=self._verify_ssl)

            self.data = json.loads(response.text)
        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)
            self.data = None
