
import sys
sys.path.append('/amaroq/hass/pylib')
import weather_convert
import logging

from homeassistant.helpers.entity import Entity
from custom_components.rfxcom_rx import DOMAIN
from homeassistant.const import TEMP_FAHRENHEIT

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    lst = []

    pres_adjust = config['pressure_adjust']

    for source in config['sources']:
        topic = config['sources'][source]['topic']
        name  = config['sources'][source]['name']

        if source not in data['sources']:
            data['sources'][source] = {}

        for value in config['sources'][source]['values']:
            sen = RfxcomSensor(source,topic,name,value,pres_adjust)
            lst.append(sen)
            data['sources'][source][value] = sen

    async_add_entities(lst)


class RfxcomSensor(Entity):

    def __init__(self, source, topic, name, value, pressure_adjust):
        self._source  = source
        self._topic   = topic
        self._name    = name
        self._val     = value
        self._value   = None
        self._conv    = None
        self._adjust  = None
        self._units   = ''
        self._icon    = ''

        if value == 'temp':
            self._name += ' Temperature'
            self._conv  = weather_convert.tempCelToFar
            self._units = TEMP_FAHRENHEIT
            self._icon  = 'mdi:thermometer'
        elif value == 'humidity':
            self._name += ' Humidity'
            self._units = "%"
            self._icon  = 'mdi:water-percent'
        elif value == 'battery':
            self._name += ' Battery'
            self._units = "%"
            self._icon  = 'mdi:battery'
        elif value == 'barometer':
            self._name += ' Pressure'
            self._conv   = weather_convert.pressureHpaToInhg
            self._units  = "INHG"
            self._adjust = pressure_adjust
        elif value == 'trend':
            self._name += ' Trend'
        elif topic == 'rain' and value == 'speed':
            self._name += ' Rate'
            self._conv  = weather_convert.rainMmToIn
            self._units = "INPH"
        elif topic == 'rain' and value == 'total':
            self._name += ' Total'
            self._conv  = weather_convert.rainMmToIn
            self._units = "IN"
        elif topic == 'wind' and value == 'speed':
            self._name += ' Gust'
            self._conv  = weather_convert.speedMpsToMph
            self._units = "MPH"
        elif topic == 'wind' and value == 'dir':
            self._name += ' Direction'
            self._units = "Deg"
        elif topic == 'wind' and value == 'avgspeed':
            self._name += ' Average'
            self._conv  = weather_convert.speedMpsToMph
            self._units = "MPH"

        # Generate Entity ID
        self._id = self._name.lower().replace(' ','_')

    @property
    def unique_id(self):
        return self._id

    @property
    def icon(self):
        self._icon

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._value

    @property
    def unit_of_measurement(self):
        return self._units

    def _update(self,value):
        if self._adjust is not None:
            lval = value + self._adjust
        else:
            lval = value

        if self._conv is not None:
            self._value = self._conv(lval)
        else:
            self._value = lval

        _LOGGER.warning("Set {} = {}".format(self._name,self._value))
        self.async_update_ha_state()

