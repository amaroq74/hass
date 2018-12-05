#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')
import hass_mysql

import appdaemon.plugins.hass.hassapi as hass
from homeassistant.const import TEMP_FAHRENHEIT
import weather_convert
from datetime import datetime, timedelta

TempWeights = { "sensor.bedr_temperature"   : 1.0,
                "sensor.master_temperature" : 1.2,
                "sensor.indoor_temperature" : 0.8,
                "sensor.bedta_temperature"  : 1.0 }

class HouseClimate(hass.Hass):

    def initialize(self):
        self._db = hass_mysql.Mysql("hass-app")

        # House temp calculation
        for k,v in TempWeights.items():
            self.listen_state(self.comp_temp, k)
        self.comp_temp()

        # Dew point calculation
        self.listen_state(self.comp_dewpt,'sensor.outdoor_temperature')
        self.listen_state(self.comp_dewpt,'sensor.outdoor_humidity')
        self.comp_dewpt()

        # Rain calculation
        self.run_every(self.rain_calc, datetime.now() + timedelta(seconds=10), 60)
        self.rain_calc()

        # Wind compass
        self.listen_state(self.wind_comp,'sensor.wind_direction')
        self.wind_comp()

    # Compute house temperature
    def comp_temp(self, *args, **kwargs):
        tot = 0.0
        div = 0.0

        for k,v in TempWeights.items():
            val = self.get_state(k)
            if val is not None and val != 'unknown':
                tot += (float(val) * v)
                div += TempWeights[k]
            else:
                self.log('WARNING',"Missing data from = {}".format(k))

        if div > 0.0:
            newF = tot / div
            newC = weather_convert.tempFarToCel(newF)
            self._db.setSensor('House', 'temp', newC, 'c')
            self.log("New house temp = {}".format(newF))

            self.set_state("sensor.house_temperature", 
                           state=newF, 
                           attributes={'friendly_name' : 'House Temperature', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})

    # New dew point source received
    def comp_dewpt(self, *args, **kwargs):
        temp  = self.get_state('sensor.outdoor_temperature')
        humid = self.get_state('sensor.outdoor_humidity')

        if temp is not None and temp != 'unknown' and humid is not None and humid != 'unknown':
            dewPt = weather_convert.compDewPtFar(float(temp), float(humid))
            self.log("Comp dewpt temp = {} humid = {} dewPt = {}".format(temp,humid,dewPt))

            self.set_state("sensor.outdoor_dewpoint", 
                           state=dewPt,
                           attributes={'friendly_name' : 'Outdoor Dew Point', 'unit_of_measurement' : TEMP_FAHRENHEIT, 'device_class' : 'temperature'})


        else:
            self.log('ERROR',"Unable to calculate dewPt Temp = {}, Humid = {}".format(temp,humid))

    # rain calc
    def rain_calc(self, *args, **kwargs):
        count_now  = self.get_state('sensor.rain_total')
        count_hour = self._db.getSensorHour('rain','count')
        count_day  = self._db.getSensorDay('rain','count')

        if count_now == 'unknown' or count_now is None or count_hour is None or count_day is None:
            val_hour = 0.0
            val_day  = 0.0
            self.log('ERROR',"Unable to calculate rain now = {}, hour = {}, day = {}".format(count_now,count_hour,count_day))
        else:
            val_hour = float(count_now) - weather_convert.rainMmToIn(count_hour)
            val_day  = float(count_now) - weather_convert.rainMmToIn(count_day)

        if val_hour < 0.001:
            val_hour = 0.0

        if val_day < 0.001:
            val_day = 0.0

        if val_hour >= 0.0 and val_day >= 0.0:
            self.log("Rain calc. count now = {}, count hour = {}, count day = {}, val hour = {}, val day = {}".format(count_now,count_hour,count_day,val_hour,val_day))

            self.set_state("sensor.rain_hour",
                           state=val_hour,
                           attributes={'friendly_name' : 'Rain Hour', 'unit_of_measurement' : 'IN', 'device_class' : ''})

            self.set_state("sensor.rain_day", 
                           state=val_day,
                           attributes={'friendly_name' : 'Rain Day', 'unit_of_measurement' : 'IN', 'device_class' : ''})

    # Set compass direction
    def wind_comp(self, *args, **kwargs):
        cur = self.get_state('sensor.wind_direction')

        if cur is not None and cur != 'unknown':
            new = weather_convert.windDegToCompass(cur)

            self.set_state("sensor.wind_compass",
                           state=new,
                           attributes={'friendly_name' : 'Wind Compass', 'unit_of_measurement' : '', 'device_class' : ''})

