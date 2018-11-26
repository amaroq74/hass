#!/usr/bin/env python3

# Add relative path
import sys,os
sys.path.append('/amaroq/hass/pylib')

# Libraries
import appdaemon.plugins.hass.hassapi as hass
import rainforest

class PowerPost(hass.Hass):

    def initialize(self):
        self._devPath = "/dev/serial/by-id/usb-Rainforest_RFA-Z106-RA-PC_RAVEn_v2.3.21-if00-port0"
        self._error   = False
        self._pwr     = None

        self.run_in(self.post_power,0)

    def post_power(self, kwargs):

        if self._pwr is None:
            self.log("Reopening usb port")
            self._pwr = rainforest.Rainforest(self._devPath)
            self._pwr.open()

        try:
            mode, value, units = self._pwr.getData()
            self.log("Got {} = {} {}".format(mode,value,units))

            if mode == 'current':
                self.set_state('sensor.smartmeter_rate', state=value,
                           attributes={'friendly_name' : 'Smartmeter Rate', 'unit_of_measurement' : units, 'device_class' : None})

            elif mode == 'total':
                self.set_state('sensor.smartmeter_total', state=value,
                           attributes={'friendly_name' : 'Smartmeter Total', 'unit_of_measurement' : units, 'device_class' : None})

        except rainforest.RainforestException as msg:
            self.log("Got error: {}".format(msg))
            self._pwr.close()
            self._pwr = None

        self.run_in(self.post_power,0)

