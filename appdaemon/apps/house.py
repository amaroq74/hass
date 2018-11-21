#!/usr/bin/env python3

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
            new = tot / div
            self.log("New house temp = {}".format(new))

            self.set_state("sensor.house_temp", state=new, attributes={'friendly_name' : 'House Temp', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})

    def new_temp(self, entity, attribute, old, new, kwargs):
        self.log("Got {} {} {} {}".format(entity,attribute,old,new))

        self._cur[entity]  = float(new)
        self._last[entity] = time.time()

        self.comp_temp()

