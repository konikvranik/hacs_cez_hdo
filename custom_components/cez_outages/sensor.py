"""
Support for RESTful API sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
Modified to parse a JSON reply and store data as attributes
"""
import datetime
import json
import logging
import re

import requests
from homeassistant.const import (
    CONF_NAME, STATE_UNKNOWN, CONF_RESOURCE, CONF_METHOD,
    CONF_VERIFY_SSL, CONF_PAYLOAD, CONF_HEADERS, STATE_OFF)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

from . import CONF_STREET, CONF_STREET_NO, CONF_PARCEL_NO, CONF_REFRESH_RATE, SCHEMA

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(SCHEMA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config, async_add_entities):
    """Set up ESPHome binary sensors based on a config entry."""
    config = config.data
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE,
                          "https://dip.cezdistribuce.cz/irj/portal/anonymous/rest-api?path=/vyhledaniOdstavek/nactiOdstavky")
    method = config.get(CONF_METHOD, "POST")
    payload = config.get(CONF_PAYLOAD, '{"ulice":"","mesto":"Statenice","psc":""}')
    verify_ssl = config.get(CONF_VERIFY_SSL, True)
    headers = config.get(CONF_HEADERS, {"X-App-ID": "1582533535480",
                                        "Origin": "https://dip.cezdistribuce.cz",
                                        "X-Request-Token": "3491d2690c38fc98ce999a6c39d31017a6ffb1ab",
                                        "Content-Type": "application/json;charset=UTF-8",
                                        "Referer": "https://dip.cezdistribuce.cz/irj/portal/anonymous/vyhledani-odstavek",
                                        "Accept-Encoding": "gzip, deflate, br",
                                        "Accept-Language": "cs,en-US;q=0.9,en-GB;q=0.8,en;q=0.7,cs-CZ;q=0.6"})
    auth = None
    rest = JSONRestClient(method, resource, auth, headers, payload, verify_ssl)
    rest.update()

    if rest.data is None:
        _LOGGER.error("Unable to fetch REST data")
        return False

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


def filterout(x, streets, street_numbers, parcel_numbers):
    for part in x['parts']:
        for street in part['streets']:
            s = anymatch(street['streetName'], streets)
            if s:
                for number in street['streetNumbers']:
                    r = anymatch(number['buildingId'], street_numbers)
                    if r:
                        _LOGGER.debug("matched on c:%s, s:%s, b:%s", part['cityPart'], s, r)
                        return dict(times(x), part=part['cityPart'], street=s, building=r)
                    r = anymatch(number['parcelaId'], parcel_numbers)
                    if r:
                        _LOGGER.debug("matched on c:%s, s:%s, p:%s", part['cityPart'], s, r)
                        return dict(times(x), part=part['cityPart'], street=s, parcel=r)
    return False


def times(x):
    date = datetime.datetime.fromisoformat(x['date']).date()
    from_time = datetime.datetime.fromisoformat(x['fromTime']).time()
    to_time = datetime.datetime.fromisoformat(x['toTime']).time()
    return {"from": datetime.datetime.combine(date, from_time), "to": datetime.datetime.combine(date, to_time)}


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
        self.update()

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
        self.rest.update()
        value = self.rest.data
        _LOGGER.debug("Raw REST data: %s" % value)

        if value is None:
            _LOGGER.debug("value is None -> state UNKNOWN")
            value = STATE_UNKNOWN
        else:
            data = json.loads(value)['data']
            t = [y for y in [filterout(x, self._streets, self._street_numbers, self._parcel_numbers) for x in data] if
                 y]
            value = t[0]['from'] if len(t) > 0 else STATE_OFF
            self._attributes['times'] = t
            self._attributes['data'] = data

        self._state = value

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

            self.data = response.text
        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)
            self.data = None
