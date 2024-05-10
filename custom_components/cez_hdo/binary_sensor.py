"""
Support for RESTful API of ČEZ HDO.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
Modified to parse a JSON reply, set sensor state due to active T2 and HDO times
 as sensor attributes
"""

import datetime
import json

from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import (CONF_NAME, CONF_VALUE_TEMPLATE, CONF_FORCE_UPDATE)
from homeassistant.helpers.entity import DeviceInfo

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


class HDORestSensor(BinarySensorEntity):
    """Implementation of a REST sensor."""

    def __init__(self, hass, name, code, value_template, refresh_rate, force_update, maxCount=10):
        """Initialize the REST sensor."""
        self._hass = hass
        self._attr_name = name
        self._attr_unique_id = code
        self._data = None
        self._value_template = value_template
        self._attr_force_update = force_update
        self._maxCount = maxCount
        self._refresh_rate = refresh_rate
        self._last_refresh = datetime.datetime.now() - 2 * self._refresh_rate
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_extra_state_attributes = dict()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            # If desired, the name for the device could be different to the entity
            name=self.name,
            sw_version=VERSION,
            model="REST call",
            manufacturer="ČEZ distribuce",
        )

    @property
    def data(self):
        """Return the HDO data."""
        return self._data

    def update(self):
        """Get the latest data from REST API and update the state."""
        _LOGGER.info("Calling update %s", self._attr_unique_id)
        if self._last_refresh + self._refresh_rate < datetime.datetime.now():
            self._hass.services.call(DOMAIN, SERVICE, {CONF_CODE: self._attr_unique_id})
            self._last_refresh = datetime.datetime.now()
        if not self._hass.states.get(DOMAIN + '.' + self._attr_unique_id):
            _LOGGER.warn('Unable to update data')
            return
        else:
            self._data = self._hass.states.get(DOMAIN + '.' + self._attr_unique_id).attributes
            _LOGGER.debug('Updated sensor state: %s', self._data)

        """Parse the return text as JSON and save the json as an attribute."""
        try:
            _LOGGER.debug("Parsing attributes...")

            now = datetime.datetime.now()
            self._attr_is_on = self.is_in_limit(now)
            self.extra_state_attributes['next'] = self.find_next(
                now).strftime('%H:%M')
            self.extra_state_attributes['to_next'] = strfdelta(
                self.find_next(now) - now, '{H}:{M:02}')
            self.extra_state_attributes['following'] = self.following(
                now, self._maxCount)
            self.extra_state_attributes[CONF_CODE] = self._attr_unique_id

        except json.JSONDecodeError:
            _LOGGER.debug("Error decoding JSON. Resetting attributes")
            self._attr_extra_state_attributes = {}

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
