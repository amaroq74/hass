#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import hass_mysql

import appdaemon.plugins.hass.hassapi as hass
from homeassistant.const import TEMP_FAHRENHEIT
from datetime import datetime, timedelta
import weather_convert
import time

LogSensors = {  'sensor.rain_count'          : {'type':'count',         'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_day'            : {'type':'count_day',     'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_hour'           : {'type':'count_hour',    'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_hour'           : {'type':'count_rate',    'device':'Rain',           'units':'mmph',     'conv':weather_convert.rainInToMm},
                'sensor.wind'                : {'type':'direction',     'device':'Wind',           'units':'deg',      'conv':None},
                'sensor.wind_gust'           : {'type':'speed',         'device':'Wind',           'units':'mps',      'conv':weather_convert.speedMphToMps},
                'sensor.wind_avg'            : {'type':'speed_average', 'device':'Wind',           'units':'mps',      'conv':weather_convert.speedMphToMps},
                'sensor.outdoor_temp'        : {'type':'temp',          'device':'Outdoor',        'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.outdoor_dewpt'       : {'type':'temp',          'device':'Outdoor_DewPt',  'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.outdoor_humidity'    : {'type':'humidity',      'device':'Outdoor',        'units':'%',        'conv':None},
                'sensor.indoor_temp'         : {'type':'temp',          'device':'Indoor',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.indoor_humidity'     : {'type':'humidity',      'device':'Indoor',         'units':'%',        'conv':None},
                'sensor.indoor_pressure'     : {'type':'pressure',      'device':'Indoor',         'units':'hpa',      'conv':weather_convert.pressureInhgToHpa},
                'sensor.garage_temp'         : {'type':'temp',          'device':'Garage',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.garage_humidity'     : {'type':'humidity',      'device':'Garage',         'units':'%',        'conv':None},
                'sensor.shed_temp'           : {'type':'temp',          'device':'Shed',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.shed_humidity'       : {'type':'humidity',      'device':'Shed',           'units':'%',        'conv':None},
                'sensor.master_temp'         : {'type':'temp',          'device':'Master',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.master_humidity'     : {'type':'humidity',      'device':'Master',         'units':'%',        'conv':None},
                'sensor.bedr_temp'           : {'type':'temp',          'device':'BedR',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.bedr_humidity'       : {'type':'humidity',      'device':'BedR',           'units':'%',        'conv':None},
                'sensor.bedta_temp'          : {'type':'temp',          'device':'BedTA',          'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.bedta_humidity'      : {'type':'humidity',      'device':'BedTA',          'units':'%',        'conv':None},
                'sensor.camper_temp'         : {'type':'temp',          'device':'Camper',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.chickens_temp'       : {'type':'temp',          'device':'Chickens',       'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_temp'           : {'type':'temp',          'device':'Pool',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_solar_in_temp'  : {'type':'temp',          'device':'Pool_Solar_In',  'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_solar_out_temp' : {'type':'temp',          'device':'Pool_Solar_Out', 'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.smartmeter_rate'     : {'type':'current',       'device':'SmartMeter',     'units':'KW',       'conv':None},
                'sensor.smartmeter_total'    : {'type':'total',         'device':'SmartMeter',     'units':'KW_Hours', 'conv':None},
                'sensor.ups_volts'           : {'type':'line_voltage',  'device':'UPS',            'units':'V',        'conv':None},
                'sensor.ups_load'            : {'type':'load',          'device':'UPS',            'units':'%',        'conv':None},
                'sensor.ups_power'           : {'type':'power',         'device':'UPS',            'units':'W',        'conv':None} }
 

class SensorLog(hass.Hass):

    def initialize(self):
        self._db = hass_mysql.Mysql("hass-app")

        for k,v in LogSensors.items():
            self.listen_state(self.sensor_rx, k)

        self.run_every(self.sensor_all, datetime.now() + timedelta(seconds=60), 60*5)

    def sensor_rx(self, entity, attribute, old, new, kwargs):
        self.log("Got new value for {} = {}".format(entity,new))
        ent = LogSensors[entity]

        if ent['conv'] is not None:
            val = ent['conv'](float(new))
        else:
            val = float(new)

        self._db.setSensor(ent['device'] + '_new', ent['type'], new, ent['units'])

    def sensor_all(self, kwargs):
        self.log("Logging all sensors")
        for k,ent in LogSensors.items():
            new = self.get_state(k)

            if new is not None:
                if ent['conv'] is not None:
                    val = ent['conv'](float(new))
                else:
                    val = float(new)

                self._db.setSensor(ent['device'] + '_new', ent['type'], val, ent['units'])

