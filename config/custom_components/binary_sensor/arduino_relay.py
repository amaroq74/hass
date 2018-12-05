
import sys
sys.path.append('/amaroq/hass/pylib')
import weather_convert
import logging
import hass_arduino

from custom_components.arduino_relay import DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_STATE, TEMP_FAHRENHEIT
from homeassistant.components.binary_sensor import (BinarySensorDevice)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    lst = []

    sources = config['sources']

    for k,v in sources.items():
        board      = v['board']
        inp        = v['input']
        name       = v['name']
        inverted   = v['inverted']
        fire_event = v['fire_event']

        if board in data['boards']:
            brd = data['boards'][board]
            sen = ArduinoBinarySensor(brd, k, name, inverted, hass, fire_event)
            brd.addInput(inp, sen)

            lst.append(sen)

    async_add_entities(lst)

class ArduinoBinarySensor(BinarySensorDevice,hass_arduino.ArduinoRelayInput):

    def __init__(self, parent, entity, name, inv, hass, event):
        super(ArduinoBinarySensor,self).__init__(parent,entity,name,inv)

        self._icon     = ''
        self._class    = None
        self._hass     = hass
        self._event    = event

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
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        return self._class

    def locInputState(self,state):
        ret = super(ArduinoBinarySensor,self).locInputState(state)
        if ret: self.async_schedule_update_ha_state(force_refresh=True)

        if ret and self._state and self._event:
            _LOGGER.info('firing pushbutton event for {}'.format(self.entity_id))
            self._hass.bus.fire('button_pressed', { ATTR_ENTITY_ID: self.entity_id })

        return ret

