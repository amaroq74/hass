#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import hass_mysql

import appdaemon.plugins.hass.hassapi as hass
from homeassistant.const import TEMP_FAHRENHEIT
import time

weights = { "sensor.bedr_temp"   : 1.0,
            "sensor.master_temp" : 1.2, 
            "sensor.indoor_temp" : 0.8, 
            "sensor.bedta_temp"  : 1.0 }

class HouseTemp(hass.Hass):

    def initialize(self):
        self._cur  = {}
        self._last = {}

        self._db = hass_mysql.Mysql("hass-app")

        for k,v in weights.items():
            self.listen_state(self.new_temp, k)
            self._cur[k]  = float(self.get_state(k))
            self._last[k] = time.time()

        self.comp_temp()

    def comp_temp(self):
        tot = 0.0
        div = 0.0

        for k,v in weights.items():
            if (time.time() - self._last[k]) < 60*15:
                tot += (self._cur[k] * weights[k])
                div += weights[k]

        if div > 0.0:
            newF = tot / div
            newC = (newF -32.0) * (5.0/9.0)
            self._db.setSensor('House', 'temp', newC, 'c')
            self.log("New house temp = {}".format(newF))

            self.set_state("sensor.house_temp", state=newF, attributes={'friendly_name' : 'House Temp', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})

    def new_temp(self, entity, attribute, old, new, kwargs):
        self.log("Got {} {} {} {}".format(entity,attribute,old,new))

        self._cur[entity]  = float(new)
        self._last[entity] = time.time()

        self.comp_temp()

