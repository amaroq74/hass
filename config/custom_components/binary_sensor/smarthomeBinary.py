
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

import logging
_LOGGER = logging.getLogger(__name__)

import logging
import datetime
import homeassistant.util.dt as dt_util
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import track_point_in_time
from homeassistant.components.binary_sensor import (DOMAIN, BinarySensorDevice)

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    lst = db.getSecurityList()
    async_add_entities(SmarthomeBinary(i) for i in lst)

class SmarthomeBinary(BinarySensorDevice):

    def __init__(self, info):
        self._info = info
        #_LOGGER.info("Creating {}".format(self._info))
        self._state = None
        self._name = self._info['zone'].replace('_',' ').title()

        if self._info['zone'] == 'Car_Gate':
            self._class = 'garage_door'
        elif self._info['zone'] == 'Garage_Door':
            self._class = 'garage_door'
        elif 'Bell' in self._info['zone']:
            self._class = None
        elif 'Motion' in self._info['zone']:
            self._class = 'motion'
        elif 'Door' in self._info['zone']:
            self._class = 'door'
        elif 'Gate' in self._info['zone']:
            self._class = 'door'
        else:
            self._class = None

    async def async_update(self):
        tval = db.getSecurity(self._info['zone'])
        self._state = (tval['event'] != 'normal')

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        return self._class

