#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import appdaemon.plugins.hass.hassapi as hass
import time
import urllib
import urllib.request
from datetime import datetime, timedelta

# Sensor List
SensorList = { 'sensor.wind'             : 'windgustmph'  ,
               'sensor.wind_avg'         : 'windspeedmph' ,
               'sensor.wind'             : 'winddir'      ,
               'sensor.outdoor_humidity' : 'humidity'     ,
               'sensor.outdoor_temp'     : 'tempf'        ,
               'sensor.indoor_pressure'  : 'baromin'      ,
               'sensor.rain_day'         : 'dailyrainin'  ,
               'sensor.rain_hour'        : 'rainin'       ,
               'sensor.outdoor_dewpt'    : 'dewptf'       }

class WeatherPost(hass.Hass):

    def initialize(self):
        self.run_every(self.post_weather, datetime.now() + timedelta(seconds=10), 5)

    def post_weather(self, kwargs):

        # Generate WUG Url
        data  = "http://rtupdate.wunderground.com/weatherstation/"
        data += "updateweatherstation.php"
        data += "?action=updateraw"
        data += "&ID=KCAREDWO4"
        data += "&PASSWORD=741753"
        data += "&realtime=1&rtfreq=5"
        data += "&dateutc=" + urllib.parse.quote(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        data += "&softwaretype=Custom_Linux_Python"

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


