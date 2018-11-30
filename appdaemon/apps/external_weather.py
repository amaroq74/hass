#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')
import hass_secrets

import appdaemon.plugins.hass.hassapi as hass
import time
import urllib
import urllib.request
from datetime import datetime, timedelta

# Sensor List
SensorList = { 'sensor.wind_gust'           : 'windgustmph'  ,
               'sensor.wind_average'        : 'windspeedmph' ,
               'sensor.wind_direction'      : 'winddir'      ,
               'sensor.outdoor_humidity'    : 'humidity'     ,
               'sensor.outdoor_temperature' : 'tempf'        ,
               'sensor.indoor_pressure'     : 'baromin'      ,
               'sensor.rain_day'            : 'dailyrainin'  ,
               'sensor.rain_hour'           : 'rainin'       ,
               'sensor.outdoor_dewpoint'    : 'dewptf'       }

class WeatherPost(hass.Hass):

    def initialize(self):
        self.run_every(self.post_weather, datetime.now() + timedelta(seconds=10), 5)

    def post_weather(self, *args, **kwargs):

        # Generate WUG Url
        data  = "http://rtupdate.wunderground.com/weatherstation/"
        data += "updateweatherstation.php"
        data += "?action=updateraw"
        data += "&ID={}".format(hass_secrets.wunder_id)
        data += "&PASSWORD={}".format(hass_secrets.wunder_pass)
        data += "&realtime=1&rtfreq=5"
        data += "&dateutc=" + urllib.parse.quote(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        data += "&softwaretype=Home_Assistant"

        for k,v in SensorList.items():
            val = self.get_state(k)

            if val is not None:
                data += "&{}={}".format(v,val)

        try:
            #self.log("Posting {}".format(data))
            fh = urllib.request.urlopen(data)
            ures = fh.read().rstrip()
            fh.close()

            if ures != b'success':
                self.log("Bad url post result = {}".format(ures))

        except Exception as msg:
            self.log("Got exception: {}".format(msg))
        except:
            self.log("Got unknown exception")

