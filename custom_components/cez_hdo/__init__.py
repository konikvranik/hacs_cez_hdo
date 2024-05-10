"""CEZ HDO info"""

import datetime
import json
import logging
import os
from string import Formatter

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_NAME, CONF_VALUE_TEMPLATE,
                                 CONF_FORCE_UPDATE, CONF_CODE)
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from voluptuous import ALLOW_EXTRA

CONF_MAX_COUNT = 'maxCount'
CONF_REFRESH_RATE = 'refreshRate'

_LOGGER = logging.getLogger(__name__)
_LOGGER.info('Starting hdo')

DEFAULT_METHOD = 'GET'
DEFAULT_VERIFY_SSL = True
MANIFEST = json.load(open("%s/manifest.json" % os.path.dirname(os.path.realpath(__file__))))
VERSION = MANIFEST["version"]
DOMAIN = MANIFEST["domain"]
DEFAULT_NAME = MANIFEST["name"]
PLATFORM = "binary_sensor"
ISSUE_URL = "https://github.com/konikvranik/hacs_cez/issues"
SERVICE = 'refresh'
TIMES = 'times'
STORAGE_VERSION = 1

SCHEMA = {
    vol.Required(CONF_CODE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_FORCE_UPDATE, default=True): cv.boolean,
    vol.Optional(CONF_REFRESH_RATE, default=86400): vol.All(vol.Coerce(int)),
    vol.Optional(CONF_MAX_COUNT, default=5): vol.All(vol.Coerce(int)),
}

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)

restdata = dict()


async def async_setup_entry(hass, entry):
    """Set up ESPHome binary sensors based on a config entry."""
    _LOGGER.debug(entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(entry.data)})
    _LOGGER.debug(config)

    def update(code):
        restdata[code].update()
        hass.states.set(DOMAIN + '.' + code, 'OK', attributes=restdata[code].data)

    @callback
    def hdo_updater(call):
        """My first service."""
        _LOGGER.debug("Called HDO: %s", call)
        if CONF_CODE in call.data:
            code = call.data[CONF_CODE]
        else:
            code = config.get(CONF_CODE)
        if code not in restdata:
            url = 'https://www.cezdistribuce.cz/api/graphql'
            _LOGGER.debug("Registering %s", code)
            restdata[code] = HDORestData(hass, 'POST', url, DEFAULT_VERIFY_SSL)
        hass.async_add_executor_job(update, code)

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, SERVICE, hdo_updater)
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, PLATFORM))
    # Return boolean to indicate that initialization was successfully.
    return True


async def platform_async_setup_entry(
        hass: HomeAssistant,
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


class HDORestData(object):
    """Class for handling the data retrieval."""

    def __init__(self, hass, method, resource, verify_ssl):
        """Initialize the data object.
         {
            "validFrom": "1. 4. 2019",
            "validTo": "1. 1. 2099",
            "dumpId": "34",
            "povel": "A3B4DP1",
            "kodPovelu": "405",
            "sazba": "D57d",
            "info": "sazba",
            "doba": "20",
            "date": "2019-03-22 07:21:11.245",
            "description": "2019_jaro_stred",
            "sazby" : [
                {
                    "id": "7780",
                    "platnost": "Po - Pá",
                    "casy" : [
                        {"start": "00:00", "stop": "05:35"},
                        {"start": "06:30", "stop": "08:55"},
                        {"start": "09:55", "stop": "14:15"},
                        {"start": "15:10", "stop": "20:15"},
                        {"start": "21:15", "stop": "23:59"},
                    ]
                },
                {
                    "id": "7781",
                    "platnost": "So - Ne",
                    "casy" : [
                        {"start": "00:00", "stop": "06:15"},
                        {"start": "07:15", "stop": "08:55"},
                        {"start": "09:55", "stop": "12:55"},
                        {"start": "13:55", "stop": "18:55"},
                        {"start": "19:55", "stop": "23:59"},
                    ]
                }
            ]
        }



        [
    {
        "data": {
            "hdoData": {
                "result": [
                    {
                        "description": "Sazba D57d ",
                        "kod": null,
                        "kod_povelu": "405",
                        "povel": "A3B4DP1",
                        "timelines": [
                            {
                                "description": "Pondělí - Pátek (20 hodin denně)",
                                "intervals": [
                                    {
                                        "left": 0,
                                        "width": 23.2128,
                                        "text": "0:00 - 5:35",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 27.04,
                                        "width": 10.0672,
                                        "text": "6:30 - 8:55",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 41.2672,
                                        "width": 23.545599999999993,
                                        "text": "9:55 - 15:35",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 68.97279999999999,
                                        "width": 15.267200000000017,
                                        "text": "16:35 - 20:15",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 88.4,
                                        "width": 11.439999999999998,
                                        "text": "21:15 - 24:00",
                                        "__typename": "HdoInterval"
                                    }
                                ],
                                "__typename": "HdoTimeline"
                            },
                            {
                                "description": "Sobota - Neděle (20 hodin denně)",
                                "intervals": [
                                    {
                                        "left": 0,
                                        "width": 38.1472,
                                        "text": "0:00 - 9:10",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 42.3072,
                                        "width": 9.692799999999998,
                                        "text": "10:10 - 12:30",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 56.160000000000004,
                                        "width": 22.54720000000001,
                                        "text": "13:30 - 18:55",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 82.86720000000001,
                                        "width": 8.319999999999993,
                                        "text": "19:55 - 21:55",
                                        "__typename": "HdoInterval"
                                    },
                                    {
                                        "left": 95.34720000000002,
                                        "width": 4.492799999999988,
                                        "text": "22:55 - 24:00",
                                        "__typename": "HdoInterval"
                                    }
                                ],
                                "__typename": "HdoTimeline"
                            }
                        ],
                        "__typename": "HdoResult"
                    }
                ],
                "resultPrint": [
                    {
                        "description": "Sazba D57d ",
                        "kod": null,
                        "kod_povelu": "405",
                        "povel": "A3B4DP1",
                        "rows": [
                            {
                                "day": "Pondělí",
                                "intervals": [
                                    "0:00 - 5:35",
                                    "6:30 - 8:55",
                                    "9:55 - 15:35",
                                    "16:35 - 20:15",
                                    "21:15 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Úterý",
                                "intervals": [
                                    "0:00 - 5:35",
                                    "6:30 - 8:55",
                                    "9:55 - 15:35",
                                    "16:35 - 20:15",
                                    "21:15 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Středa",
                                "intervals": [
                                    "0:00 - 5:35",
                                    "6:30 - 8:55",
                                    "9:55 - 15:35",
                                    "16:35 - 20:15",
                                    "21:15 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Čtvrtek",
                                "intervals": [
                                    "0:00 - 5:35",
                                    "6:30 - 8:55",
                                    "9:55 - 15:35",
                                    "16:35 - 20:15",
                                    "21:15 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Pátek",
                                "intervals": [
                                    "0:00 - 5:35",
                                    "6:30 - 8:55",
                                    "9:55 - 15:35",
                                    "16:35 - 20:15",
                                    "21:15 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Sobota",
                                "intervals": [
                                    "0:00 - 9:10",
                                    "10:10 - 12:30",
                                    "13:30 - 18:55",
                                    "19:55 - 21:55",
                                    "22:55 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            },
                            {
                                "day": "Neděle a svátky",
                                "intervals": [
                                    "0:00 - 9:10",
                                    "10:10 - 12:30",
                                    "13:30 - 18:55",
                                    "19:55 - 21:55",
                                    "22:55 - 24:00"
                                ],
                                "__typename": "HdoRow"
                            }
                        ],
                        "__typename": "HdoResultPrint"
                    }
                ],
                "queryDescription": "povel",
                "__typename": "HdoResponse"
            }
        }
    }
]
        """
        self._request = requests.Request(method, resource,
                                         {"content-type": "application/json", "accept": "application/json",
                                          "x-locale": "cs"}, None,
                                         '[{"operationName": "hdoData",'
                                         ' "variables": {"code": "A3B4DP1", "area": "stred"},'
                                         ' "query": "query hdoData($code: String, $area: String) { hdoData(code: $code, area: $area) { resultPrint { description kod kod_povelu povel rows { day intervals __typename } __typename } queryDescription __typename } } "}]').prepare()

        self._verify_ssl = verify_ssl
        self._hass = hass
        self.data = None

    def update(self):
        """Get the latest data from REST service with provided method."""
        _LOGGER.debug("Updating HDO data %s", self._request)
        try:
            with requests.Session() as sess:
                response = sess.send(self._request, timeout=10, verify=self._verify_ssl)

            response.encoding = 'UTF-8'
            _LOGGER.debug(response.text)
            _data = json.loads(response.text)
            if not _data:
                _LOGGER.warning("returned empty data: %s", self._request)
                return
            else:
                _LOGGER.debug("Got data:\n%s", _data)
            _time_sets = []
            for d in _data[0]['data']['hdoData']['resultPrint'][0]['rows']:
                _time_sets.append(_parse_times(d))
            self.data = {
                "valid_from": _data['data'][0]["VALID_FROM"],
                "valid_to": _data['data'][0]["VALID_TO"],
                "dump_id": _data['data'][0]["DUMP_ID"],
                "povel": _data['data'][0]["POVEL"],
                "kod_povelu": _data['data'][0]["KOD_POVELU"],
                "sazba": _data['data'][0]["SAZBA"],
                "info": _data['data'][0]["INFO"],
                "doba": _data['data'][0]["DOBA"],
                "date": _data['data'][0]["DATE_OF_ENTRY"],
                "description": _data['data'][0]["DESCRIPTION"],
                "sazby": _time_sets
            }

        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)

        today = datetime.date.today()
        _times = []
        one_day = datetime.timedelta(days=1)
        for d in [today - one_day, today, today + one_day]:
            for i in self._prepare_intervals(d):
                _times.append(i)
        self.data[TIMES] = _times
        _LOGGER.debug(self.data)

    def _prepare_intervals(self, date):
        r = []
        _LOGGER.debug('DATA: %s' % self.data)
        for t in self.data['sazby'][_tarif_index(date)]['casy']:
            r.append((datetime.datetime.combine(date, datetime.datetime.strptime(t['start'], '%H:%M').time()),
                      datetime.datetime.combine(date, datetime.datetime.strptime(t['end'], '%H:%M').time())))
        return r


def _tarif_index(t):
    return 0 if (t.weekday() < 5) else 1


def _parse_times(data):
    """
							{
								"day": "Pondělí",
								"intervals": [
									"0:00 - 5:35",
									"6:30 - 8:55",
									"9:55 - 15:35",
									"16:35 - 20:15",
									"21:15 - 24:00"
								],
								"__typename": "HdoRow"
							}

    :param data:
    :return:
    """
    r = []
    for i in data['intervals']:
        s = i.split(" - ")
        if len(s) > 1:
            r.append({'start': s[0], 'end': s[1]})

    return {
        "id": data["day"],
        "platnost": data["day"],
        "casy": r
    }


def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s',
              inputtype='timedelta'):
    """Convert a datetime.timedelta object or a regular number to a custom-
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == 'timedelta':
        remainder = int(tdelta.total_seconds())
    elif inputtype in ['s', 'seconds']:
        remainder = int(tdelta)
    elif inputtype in ['m', 'minutes']:
        remainder = int(tdelta) * 60
    elif inputtype in ['h', 'hours']:
        remainder = int(tdelta) * 3600
    elif inputtype in ['d', 'days']:
        remainder = int(tdelta) * 86400
    elif inputtype in ['w', 'weeks']:
        remainder = int(tdelta) * 604800

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('W', 'D', 'H', 'M', 'S')
    constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)
