
import sys
sys.path.append('/amaroq/hass/pylib')
import weather_convert
import logging
import hass_arduino

from custom_components.arduino_relay import DOMAIN
from homeassistant.components.switch import SwitchDevice

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    lst = []

    sources = config['outputs']

    for k,v in sources.items():
        board    = v['board']
        output   = v['output']
        name     = v['name']
        door     = v['door']

        if board in data['boards']:
            brd = data['boards'][board]

            if door:
                inp = v['input']
                sw = ArduinoRelayDoorGate(brd, k, name, v['inverted'])
                brd.addInput(inp, sw)
            else:
                sw = ArduinoRelaySwitch(brd, k, name, v['timeout'])

            brd.addOutput(output, sw)

            lst.append(sw)

    async_add_entities(lst)

class ArduinoRelaySwitch(SwitchDevice,hass_arduino.ArduinoRelayOutput):

    def __init__(self, parent, entity, name, timeout):
        super(ArduinoRelaySwitch,self).__init__(parent,entity,name,timeout)

        self._on_icon  = None
        self._off_icon = None

    @property
    def unique_id(self):
        return self._entity

    @property
    def name(self):
        return self._name

    async def async_turn_on(self, speed: str = None, **kwargs):
        self.setState(True)

    async def async_turn_off(self, **kwargs):
        self.setState(False)

    @property
    def is_on(self):
        return self._state

    @property
    def icon(self):
        if self._state:
            return self._on_icon
        else:
            return self._off_icon


class ArduinoRelayDoorGate(SwitchDevice,hass_arduino.ArduinoRelayDoorGate):

    def __init__(self, parent, entity, name, inverted):
        super(ArduinoRelayDoorGate,self).__init__(parent,entity,name,inverted)

        self._on_icon  = None
        self._off_icon = None

    @property
    def unique_id(self):
        return self._entity

    @property
    def name(self):
        return self._name

    async def async_turn_on(self, speed: str = None, **kwargs):
        self.setState(True)

    async def async_turn_off(self, **kwargs):
        self.setState(False)

    @property
    def is_on(self):
        return self._state

    @property
    def icon(self):
        if self._state:
            return self._on_icon
        else:
            return self._off_icon

    def locInputState(self,state):
        ret = super(ArduinoRelayDoorGate,self).locInputState(state)
        if ret: self.async_schedule_update_ha_state(force_refresh=True)
        return ret

