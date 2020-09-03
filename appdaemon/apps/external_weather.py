#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')
import hass_secrets
import weather_convert

import appdaemon.plugins.hass.hassapi as hass
import time
import urllib
import urllib.request
from socket import *
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

    def warning(self,msg):
        self.log(msg,level='WARNING')

    def error(self,msg):
        self.log(msg,level='ERROR')

    def debug(self,msg):
        self.log(msg,level='DEBUG')

    def initialize(self):
        self.run_every(self.post_wunderground, datetime.now() + timedelta(seconds=10), 60)
        self.run_every(self.post_aprs, datetime.now() + timedelta(seconds=10), 60)
        self.listen_state(self.post_event,'sensor.wind_gust')

        self._last = time.time()
        self._count = 0

    def post_event(self, *args, **kwargs):
        self.post_wunderground()

    def convValue(self,key):
        try:
            return float(self.get_state(key))
        except Exception as msg:
            self.error("Got exception: {}".format(msg))

        return 0.0

    def post_wunderground(self, *args, **kwargs):

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
            fh = urllib.request.urlopen(data)
            ures = fh.read().rstrip()
            fh.close()

            if ures != b'success':
                self.warning("Bad url post result = {}".format(ures))
            else:
                self._count += 1
                if (time.time() - self._last) > 300.0:
                    self.log("Posted {} times in {} seconds".format(self._count,(time.time() - self._last)))
                    self._last  = time.time()
                    self._count = 0

        except Exception as msg:
            self.error("Got exception: {}".format(msg))
        except:
            self.error("Got unknown exception")

    def post_aprs(self, *args, **kwargs):
        try:
            serverHost = 'rotate.aprs.net'
            serverPort = 14580

            # Generate password
            code = 0x73e2
            for i, char in enumerate(hass_secrets.callSign.split('-')[0]):
                code ^= ord(char) << (8 if not i % 2 else 0)

            code = code & 0x7fff
            password = str(code)

            # https://weather.gladstonefamily.net/aprswxnet.html
            weather = '_{:03d}/{:03d}g{:03d}t{:03d}r{:03d}p{:03d}P{:03d}h{:02d}b{:05d}'.format(
                round(self.convValue('sensor.wind_direction')),
                round(self.convValue('sensor.wind_average')),
                round(self.convValue('sensor.wind_gust')),
                round(self.convValue('sensor.outdoor_temperature')),
                round(self.convValue('sensor.rain_hour')*100.0),
                round(self.convValue('sensor.rain_24h')*100.0),
                round(self.convValue('sensor.rain_day')*100.0),
                round(self.convValue('sensor.outdoor_humidity')),
                round(weather_convert.pressureInhgToHpa(self.convValue('sensor.indoor_pressure'))*10.0))

            login = 'user {} pass {} vers "Python" \n'.format(hass_secrets.callSign,password)
            message = '{}>APRS,TCPIP*:!{}{}Amaroq APRS TCPIP Weather Station\n'.format(hass_secrets.callSign,hass_secrets.position,weather)

            self.warning(login)
            self.warning(message)

            sSock = socket(AF_INET, SOCK_STREAM)
            sSock.connect((serverHost, serverPort))
            sSock.send(login.encode('UTF-8'))
            sSock.send(message.encode('UTF-8'))
            sSock.shutdown(0)
            sSock.close()

        except Exception as msg:
            self.error("Got exception: {}".format(msg))
        except:
            self.error("Got unknown exception")

