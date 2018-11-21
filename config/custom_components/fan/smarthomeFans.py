
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

from homeassistant.components.fan import FanEntity, SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH, SUPPORT_SET_SPEED

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    lst = db.getDeviceList()
    nl = []
    for l in lst:
        if l['category'] == 'Other' and l['type'] == 'Fan':
            nl.append(l)

    async_add_entities(SmarthomeFan(i) for i in nl)

class SmarthomeFan(FanEntity):

    def __init__(self, info):
        self._info  = info
        self._name  = info['name'].replace('_',' ')

        info = db.getDeviceInfo(self._info['name'])
        self._level = info['status']

    @property
    def name(self):
        return self._name

    async def async_set_speed(self, speed: str):
        if speed == SPEED_OFF:
            self._level = 0
        elif speed == SPEED_LOW:
            self._level = 20
        elif speed == SPEED_MEDIUM:
            self._level = 50
        elif speed == SPEED_HIGH:
            self._level = 100
        else:
            self._level = 0

        db.setDevice(self._info['name'],self._level)

    async def async_turn_on(self, speed: str = None, **kwargs):
        self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs):
        self.async_set_speed(SPEED_OFF)

    @property
    def is_on(self):
        return self._level != 0

    @property
    def speed(self):
        if self._level == 0:
            return SPEED_OFF
        elif self._level == 20:
            return SPEED_LOW
        elif self._level == 50:
            return SPEED_MEDIUM
        elif self._level == 100:
            return SPEED_HIGH
        else:
            return SPEED_OFF

    @property
    def speed_list(self):
        return[SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    @property
    def supported_fatures(self):
        return SUPPORT_SET_SPEED

    async def async_update(self):
        info = db.getDeviceInfo(self._info['name'])
        self._level = info['status']

