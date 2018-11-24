#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import hass_mysql

import appdaemon.plugins.hass.hassapi as hass
from homeassistant.const import TEMP_FAHRENHEIT
import time
import weather_convert
from datetime import datetime, timedelta

weights = { "sensor.bedr_temp"   : 1.0,
            "sensor.master_temp" : 1.2, 
            "sensor.indoor_temp" : 0.8, 
            "sensor.bedta_temp"  : 1.0 }

DewPtTemp  = 'sensor.outdoor_temp'
DewPtHumid = 'sensor.outdoor_humidity'
RainCount  = 'sensor.rain_count'

class HouseWeather(hass.Hass):

    def initialize(self):
        self._db = hass_mysql.Mysql("hass-app")

        # House temp calculation
        for k,v in weights.items():
            self.listen_state(self.comp_temp, k)

        # Dew point calculation
        self.listen_state(self.comp_dewpt, DewPtTemp)
        self.listen_state(self.comp_dewpt, DewPtHumid)

        # Rain calculation
        self.run_every(self.rain_calc, datetime.now() + timedelta(seconds=10), 60)

    # Compute house temperature
    def comp_temp(self, entity, attribute, old, new, kwargs):
        self.log("Got {} {} {} {}".format(entity,attribute,old,new))
        tot = 0.0
        div = 0.0

        for k,v in weights.items():
            val = self.get_state(k)
            if val is not None:
                tot += (float(val) * v)
                div += weights[k]

        if div > 0.0:
            newF = tot / div
            newC = weather_convert.tempFarToCel(newF)
            self._db.setSensor('House', 'temp', newC, 'c')
            self.log("New house temp = {}".format(newF))

            self.set_state("sensor.house_temp", 
                           state=newF, 
                           attributes={'friendly_name' : 'House Temp', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})

    # New dew point source received
    def comp_dewpt(self, entity, attribute, old, new, kwargs):
        self.log("Got {} {} {} {}".format(entity,attribute,old,new))

        temp  = self.get_state(DewPtTemp)
        humid = self.get_state(DewPtHumid)

        if temp is not None and humid is not None:
            dewPt = weather_convert.compDewPtFar(float(temp), float(humid))
            self.log("Comp dewpt temp = {} humid = {} dewPt = {}".format(temp,humid,dewPt))

            self.set_state("sensor.outdoor_dewpt", 
                           state=dewPt,
                           attributes={'friendly_name' : 'Outdoor Dew Point', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})

    # rain calc
    def rain_calc(self, kwargs):
        count_now  = self.get_state(RainCount)
        count_hour = weather_convert.rainMmToIn(self._db.getSensorHour('rain','count'))
        count_day  = weather_convert.rainMmToIn(self._db.getSensorDay('rain','count'))

        if count_now is not None:
            val_hour = float(count_now) - count_hour
            val_day  = float(count_now) - count_day
        else:
            val_hour = 0.0
            val_day  = 0.0

        if val_hour >= 0.0 and val_day >= 0.0:
            self.log("Rain calc. count now = {}, count hour = {}, count day = {}, val hour = {}, val day = {}".format(count_now,count_hour,count_day,val_hour,val_day))

            self.set_state("sensor.rain_hour",
                           state=val_hour,
                           attributes={'friendly_name' : 'Rain Hour', 'unit_of_measurement' : 'in', 'device_class' : ''})

            self.set_state("sensor.rain_day", 
                           state=val_day,
                           attributes={'friendly_name' : 'Rain Day', 'unit_of_measurement' : 'in', 'device_class' : ''})


class HouseChrome(hass.Hass):

    def initialize(self):
        self.listen_state(self.chrome_changed,'media_player.chromecastultra3804')

    def chrome_changed(self, entity, attribute, old, new, kwargs):
        if new != 'off' and new != 'unavailable' and old == 'off':
            self.log("Setting Harmony state due to chrome state new {} old {} harmony = {}".format(new,old,self.get_state('remote.harmony_hub')))
            self.turn_on("remote.harmony_hub", activity = "Watch Chrome tv" )

