
import sys
sys.path.append('/amaroq/hass/pylib')
import weather_convert
import logging
import hass_arduino

from homeassistant.helpers.entity import Entity
from custom_components.arduino_relay import DOMAIN
from homeassistant.const import TEMP_FAHRENHEIT

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    lst = []

    sources = config['sources']

    for k,v in sources.items():
        board = v['board']
        inp   = v['input']
        name  = v['name']
        per   = v['avgPeriod']

        if board in data['boards']:
            brd = data['boards'][board]
            sen = ArduinoSensor(brd, k, name, per)
            brd.addInput(inp, sen)

            lst.append(sen)

    async_add_entities(lst)

class ArduinoSensor(Entity,hass_arduino.ArduinoRelayPoolSolar):

    def __init__(self, parent, entity, name, avgPeriod):
        super(ArduinoSensor,self).__init__(parent,entity,name,avgPeriod)

        self._units = TEMP_FAHRENHEIT
        self._conv  = weather_convert.tempCelToFar
        self._icon  = 'mdi:thermometer'

    @property
    def unique_id(self):
        return self._entity

    @property
    def icon(self):
        self._icon

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._state is not None:
            return self._conv(self._state)
        else:
            return None

    @property
    def unit_of_measurement(self):
        return self._units

    def locInputState(self,state):
        super(ArduinoSensor,self).locInputState(state)
        self.async_update_ha_state()

