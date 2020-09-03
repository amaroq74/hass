#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')
import hass_mysql

import appdaemon.plugins.hass.hassapi as hass
import weather_convert
from datetime import datetime, timedelta

TempWeights = { "sensor.bedr_temperature"   : 1.5,
                "sensor.master_temperature" : 1.5,
                "sensor.indoor_temperature" : 0.5,
                "sensor.bedta_temperature"  : 1.5 }

TEMP_FAHRENHEIT = '°F'

class HouseClimate(hass.Hass):

    def warning(self,msg):
        self.log(msg,level='WARNING')

    def error(self,msg):
        self.log(msg,level='ERROR')

    def debug(self,msg):
        self.log(msg,level='DEBUG')

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
            if val is not None and val != 'unknown' and val != 'NoneType' and val != 'unavailable':
                tot += (float(val) * v)
                div += TempWeights[k]
            else:
                self.warning("Missing data from {}".format(k))

        if div > 0.0:
            newF = round(tot / div,2)
            newC = weather_convert.tempFarToCel(newF)
            self._db.setSensor('House', 'temp', newC, 'c')
            self.debug("New house temp = {}".format(newF))

            self.set_state("sensor.house_temperature",
                           state=newF,
                           attributes={'friendly_name' : 'House Temp',
                                       'unit_of_measurement' : TEMP_FAHRENHEIT,
                                       'device_class' : 'temperature',
                                       'icon' : 'mdi:thermometer'})

    # New dew point source received
    def comp_dewpt(self, *args, **kwargs):
        temp  = self.get_state('sensor.outdoor_temperature')
        humid = self.get_state('sensor.outdoor_humidity')

        if temp is not None and temp != 'unknown' and temp != 'unavailable' and humid is not None and humid != 'unknown' and humid != 'unavailable':
            dewPt = weather_convert.compDewPtFar(float(temp), float(humid))
            self.debug("Comp dewpt temp = {} humid = {} dewPt = {}".format(temp,humid,dewPt))

            self.set_state("sensor.outdoor_dewpoint",
                           state=dewPt,
                           attributes={'friendly_name' : 'Outdoor Dew Point',
                                       'unit_of_measurement' : TEMP_FAHRENHEIT,
                                       'device_class' : 'temperature',
                                       'icon' : 'mdi:thermometer'})

        else:
            self.warning("Unable to calculate dewPt Temp = {}, Humid = {}".format(temp,humid))

    # rain calc
    def rain_calc(self, *args, **kwargs):
        count_now  = self.get_state('sensor.rain_total')
        counts = {'rain_hour' : {'name' : 'Rain Hour', 'count' : None},
                  'rain_day'  : {'name' : 'Rain Day',  'count' : None},
                  'rain_24h'  : {'name' : 'Rain 24H',  'count' : None},
                  'rain_72h'  : {'name' : 'Rain 72H',  'count' : None} }

        if count_now == 'uknown' or count_now == None:
            self.warning("Unable to get current rain count")
            return

        try:
            counts['rain_hour']['count'] = self._db.getSensorHour('rain','count')
            counts['rain_day']['count']  = self._db.getSensorDay('rain','count')
            counts['rain_24h']['count']  = self._db.getSensorHours('rain','count',24)
            counts['rain_72h']['count']  = self._db.getSensorHours('rain','count',72)
        except:
            self.warning("Unable to get previous rain counts")

        for k,v in counts.items():
            if v['count'] is not None:
                calc = round(float(count_now) - weather_convert.rainMmToIn(v['count']),2)
                if calc < 0.001: calc = 0.0
                self.debug("Rain calc. count_now = {}, {} = {}".format(count_now,k,calc))
            else:
                calc = 0.0

            self.set_state("sensor.{}".format(k), state=calc,
                           attributes={'friendly_name' : v['name'],
                                       'unit_of_measurement' :
                                       'IN', 'device_class' : '',
                                       'icon' : 'mdi:weather-rainy'})

    # Set compass direction
    def wind_comp(self, *args, **kwargs):
        cur = self.get_state('sensor.wind_direction')

        if cur is not None and cur != 'unknown':
            new = weather_convert.windDegToCompass(cur)

            self.set_state("sensor.wind_compass",
                           state=new,
                           attributes={'friendly_name' : 'Wind Compass',
                                       'unit_of_measurement' : '',
                                       'device_class' : '',
                                       'device_class' : '',
                                       'icon' : 'mdi:weather-windy'})

