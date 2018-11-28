
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

from homeassistant.components.switch import SwitchDevice

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    lst = db.getDeviceList()
    nl = []
    for l in lst:
        if (l['category'] != 'Lights' and l['type'] != 'Fan'):
            nl.append(l)

    async_add_entities(SmarthomeSwitch(i) for i in nl)

class SmarthomeSwitch(SwitchDevice):

    def __init__(self, info):
        self._info  = info
        self._name  = info['name'].replace('_',' ')

        info = db.getDeviceInfo(self._info['name'])
        self._state = info['status'] != 0

        if info['category'] == 'Irrigation':
            self._on_icon  = 'mdi:water'
            self._off_icon = 'mdi:water-off'
        elif info['name'] == 'Garage_Door' or  info['name'] == 'Car_Gate':
            self._on_icon  = 'mdi:garage-open'
            self._off_icon = 'mdi:garage'
        elif info['name'] == 'Speakers':
            self._on_icon  = 'mdi:music-note'
            self._off_icon = 'mdi:music-note-off'
        elif info['category'] == 'Pool':
            self._on_icon  = 'mdi:pool'
            self._off_icon = 'mdi:pool'
        else:
            self._on_icon  = None
            self._off_icon = None

    @property
    def name(self):
        return self._name

    async def async_turn_on(self, speed: str = None, **kwargs):
        self._state = True
        db.setDevice(self._info['name'],100)

    async def async_turn_off(self, **kwargs):
        self._state = False
        db.setDevice(self._info['name'],0)

    @property
    def is_on(self):
        return self._state

    @property
    def icon(self):
        if self._state:
            return self._on_icon
        else:
            return self._off_icon

    async def async_update(self):
        info = db.getDeviceInfo(self._info['name'])
        self._state = info['status'] != 0


