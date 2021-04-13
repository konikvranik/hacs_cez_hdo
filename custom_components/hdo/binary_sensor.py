"""
Support for RESTful API of ČEZ HDO.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
Modified to parse a JSON reply, set sensor state due to active T2 and HDO times
 as sensor attributes
"""

import datetime
import json

from homeassistant.components.binary_sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_VALUE_TEMPLATE, CONF_FORCE_UPDATE, STATE_UNKNOWN, STATE_ON, STATE_OFF)
from homeassistant.helpers.entity import Entity

from . import DOMAIN, SERVICE, CONF_CODE, CONF_MAX_COUNT, CONF_REFRESH_RATE, TIMES, SCHEMA, _LOGGER, strfdelta, VERSION

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(SCHEMA)


async def async_setup_entry(hass, config, async_add_entities):
    """Set up ESPHome binary sensors based on a config entry."""
    config = config.data
    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass
    sensor = HDORestSensor(hass, config.get(CONF_NAME), config.get(CONF_CODE), value_template,
                           datetime.timedelta(seconds=config.get(CONF_REFRESH_RATE)), config.get(CONF_FORCE_UPDATE),
                           config.get(CONF_MAX_COUNT))
    async_add_entities([sensor], True)


class HDORestSensor(Entity):
    """Implementation of a REST sensor."""

    def __init__(self, hass, name, code, value_template, refresh_rate, force_update, maxCount=10):
        """Initialize the REST sensor."""
        self._hass = hass
        self._name = name
        self._code = code
        self._data = None
        self._attributes = {}
        self._state = STATE_UNKNOWN
        self._value_template = value_template
        self._force_update = force_update
        self._maxCount = maxCount
        self._refresh_rate = refresh_rate
        self._last_refresh = datetime.datetime.now() - 2 * self._refresh_rate

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return self._code

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._code)},
            # If desired, the name for the device could be different to the entity
            "name": self.name,
            "sw_version": VERSION,
            "model": "REST call",
            "manufacturer": "ČEZ distribuce",
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def data(self):
        """Return the HDO data."""
        return self._data

    def update(self):
        """Get the latest data from REST API and update the state."""
        _LOGGER.info("Calling update %s", self._code)
        if self._last_refresh + self._refresh_rate < datetime.datetime.now():
            self._hass.services.call(DOMAIN, SERVICE, {CONF_CODE: self._code})
            self._last_refresh = datetime.datetime.now()
        if not self._hass.states.get(DOMAIN + '.' + self._code):
            _LOGGER.warn('Unable to update data')
            return
        else:
            self._data = self._hass.states.get(DOMAIN + '.' + self._code).attributes
            _LOGGER.debug('Updated sensor state: %s', self._data)

        """Parse the return text as JSON and save the json as an attribute."""
        try:
            _LOGGER.debug("Parsing attributes...")

            now = datetime.datetime.now()
            self._state = STATE_ON if self.is_in_limit(now) else STATE_OFF
            self._attributes['next'] = self.find_next(
                now).strftime('%H:%M')
            self._attributes['to_next'] = strfdelta(
                self.find_next(now) - now, '{H}:{M:02}')
            self._attributes['following'] = self.following(
                now, self._maxCount)
            self._attributes[CONF_CODE] = self._code

        except json.JSONDecodeError:
            _LOGGER.debug("Error decoding JSON. Resetting attributes")
            self._attributes = {}

    @property
    def state_attributes(self):
        """Return the attributes of the entity.
           Provide the parsed JSON data (if any).
        """

        return self._attributes

    @property
    def force_update(self):
        """Force update."""
        return self._force_update

    def is_in_limit(self, time):
        for t in self.data[TIMES]:
            if t[0] < time < t[1]:
                return True
        return False

    def find_next(self, time):
        n = None
        for t in self.data[TIMES]:
            for i in [0, 1]:
                if t[i] > time and (n is None or t[i] < n):
                    n = t[i]
        return n

    def following(self, time, maxCount):
        r = []
        count = 0
        for t in self.data[TIMES]:
            if t[0] > time or t[1] > time:
                r.append(dict(start=t[0], end=t[1], duration=':'.join(
                    str(t[1] - t[0])
                        .split(':')[:2])))
                count += 1
            if count >= maxCount:
                break

        return r
