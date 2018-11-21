
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

from homeassistant.components.light import Light

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    # Add devices
    lst = db.getDeviceList()
    nl = []
    for l in lst:
        if l['category'] == 'Lights':
            nl.append(l)

    async_add_entities(SmarthomeLight(i) for i in nl)

class SmarthomeLight(Light):

    def __init__(self, info):
        self._info = info
        self._name = info['name'].replace('_',' ')
        self._state = None
        self._brightness_pct = None

    @property
    def name(self):
        return self._name

    @property
    def brightness_pct(self):
        return self._brightness_pct

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        self._state = True
        db.setDevice(self._info['name'],100)

    async def async_turn_off(self, **kwargs):
        self._state = False
        db.setDevice(self._info['name'],0)

    async def async_update(self):
        info = db.getDeviceInfo(self._info['name'])
        self._state = info['status'] != 0

