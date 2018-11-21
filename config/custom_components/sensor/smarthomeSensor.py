
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.const import TEMP_CELSIUS
from homeassistant.const import TEMP_FAHRENHEIT
from homeassistant.helpers.entity import Entity

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    lst = db.getSensorList()
    nl = []

    for l in lst:
        if 'unknown' not in l['device'] and l['age'] < 24*3600:
            nl.append(l)

    async_add_entities(SmarthomeSensor(i) for i in nl)

def convertPass(value):
    return (float(value))

def convertCtoF(value):
    return ( (float(value) * 9.0/5.0) + 32.0 )

def convertMMtoIn(value):
    return ( float(value) / 25.0 )

def convertMpstoMph(value):
    return ( float(value) * 2.237)

def convertHpatoInhg(value):
    return ( float(value) * 0.02953 )

class SmarthomeSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self,info):
        self._info = info
        #_LOGGER.info("Creating {}".format(self._info))
        self._val = None
        self._name = self._info['device'].replace('_',' ').title()
        self._units = ''
        self._convert = convertPass
        self._icon = None

        if self._info['type'] == 'temp':
            self._name += " Temp"
            self._units = TEMP_FAHRENHEIT
            self._convert = convertCtoF
            self._icon = 'mdi:thermometer'
        elif self._info['type'] == 'humidity':
            self._name += " Humidity"
            self._units = '%'
            self._icon = 'mdi:water-percent'
        elif self._info['type'] == 'battery':
            self._name += " Battery"
            self._units = '%'
            self._icon = 'mdi:battery'
        elif self._info['type'] == 'cpu_load_15m':
            self._name += " Load15m"
            self._units = ''
        elif self._info['type'] == 'cpu_load_5m':
            self._name += " Load5m"
            self._units = ''
        elif self._info['type'] == 'cpu_load_1m':
            self._name += " Load1m"
            self._units = ''
        elif self._info['type'] == 'count':
            self._name += " Count"
            self._units = 'in'
            self._convert = convertMMtoIn
        elif self._info['type'] == 'count_day':
            self._name += " Day"
            self._units = 'in'
            self._convert = convertMMtoIn
        elif self._info['type'] == 'count_hour':
            self._name += " Hour"
            self._units = 'in'
            self._convert = convertMMtoIn
        elif self._info['type'] == 'count_rate':
            self._name += " Rate"
            self._units = 'mm/hr'
            self._convert = convertMMtoIn
        elif self._info['type'] == 'current' and self._info['device'] == 'SmartMeter':
            self._name += " Rate"
            self._units = 'kw'
            self._icon = 'mdi:flash'
        elif self._info['type'] == 'total' and self._info['device'] == 'SmartMeter':
            self._name += " Total"
            self._units = 'kwh'
            self._icon = 'mdi:flash'
        elif self._info['type'] == 'direction':
            self._units = 'deg'
        elif self._info['type'] == 'line_voltage':
            self._name += " Volts"
            self._units = 'v'
            self._icon = 'mdi:flash'
        elif self._info['type'] == 'load':
            self._name += " Load"
            self._units = '%'
        elif self._info['type'] == 'power':
            self._name += " Power"
            self._units = 'w'
        elif self._info['type'] == 'missed' and self._info['device'] == 'wunder':
            self._name += " missed"
            self._units = ''
        elif self._info['type'] == 'period' and self._info['device'] == 'wunder':
            self._name += " Period"
            self._units = 's'
        elif self._info['type'] == 'pressure':
            self._name += " Pressure"
            self._units = 'inhg'
            self._convert = convertHpatoInhg
        elif self._info['type'] == 'speed':
            self._name += " Gust"
            self._units = 'mph'
            self._convert = convertMpstoMph
        elif self._info['type'] == 'speed_average':
            self._name += " Avg"
            self._units = 'mph'
            self._convert = convertMpstoMph
        elif self._info['type'] == 'timeout':
            self._name += " Timeout"
            self._units = ''
        elif self._info['type'] == 'time_left':
            self._name += " Time"
            self._units = ' minutes'

    @property
    def icon(self):
        self._icon

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._val

    @property
    def unit_of_measurement(self):
        return self._units

    async def async_update(self):
        tval = db.getSensorCurrent(self._info['device'],self._info['type'])
        if tval == None:
            self._val = None
        else:
            self._val = self._convert(tval)

