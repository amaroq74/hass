#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')

import paho.mqtt.client as mqtt
import logging
import hass_rfxcom
import threading
import weather_convert
import time

PRES_ADJUST = 6.0
DEF_DEVICE  = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A6003Q5Y-if00-port0'
KNOWN_LOG   = '/amaroq/hass/config/rfxcom_known.txt'
UNKNOWN_LOG = '/amaroq/hass/config/rfxcom_unknown.txt'

SourceMap = { 'thgr228n.75' : 'master',
              'thn132n.63'  : 'chickens',
              'f007pf.02'   : 'pool',
              'wgr800.71'   : 'wind',
              'bthr918n.68' : 'indoor',
              'thgr228n.dd' : 'garage',
              'thgr810.15'  : 'bedr',
              'thgr228n.55' : 'bedta',
              'thgr810.89'  : 'outdoor',
              'pcr800.c3'   : 'rain' }


class RfxCom(object):

    def __init__(self, path, server):
        self._rx = hass_rfxcom.RFXCom(self.on_message,device=path,log=None)

        self._client = mqtt.Client("rfxcom")
        self._client.connect(server)
        self._unknown = { }
        self._known   = { }
        self._last = time.time()

    def run(self):
        self._rx.setup()
        self._rx.run()

    def on_message(self,message):
        source = message['source']
        topic  = message.topic

        for key, newValue in message.values.items():
            if key != 'topic' and key != 'source' and key != 'sensor':

                # Source = address i.e. thgr228n.75
                # topic = main type, i.e. temp, wind, rain, etc.
                # key = sub type, i.e. battery, temp, humidity,
                if key == 'temp':
                    value = weather_convert.tempCelToFar(newValue)

                elif key == 'humidity':
                    value = newValue

                elif key == 'battery':
                    value = newValue

                elif key == 'barometer':
                    value = weather_convert.pressureHpaToInhg(newValue + PRES_ADJUST)

                elif key == 'trend':
                    value = newValue

                elif topic == 'rain' and key == 'speed':
                    value = weather_convert.rainMmToIn(newValue)

                elif topic == 'rain' and key == 'total':
                    value = weather_convert.rainMmToIn(newValue)

                elif topic == 'wind' and key == 'speed':
                    value = weather_convert.speedMpsToMph(newValue)

                elif topic == 'wind' and key == 'dir':
                    value = newValue

                elif topic == 'wind' and key == 'avgspeed':
                    value = weather_convert.speedMpsToMph(newValue)

                else:
                    value = newValue

                # Check if the device is known
                if source in SourceMap:
                    path = f'stat/rfxcom/{SourceMap[source]}/{key}'

                    #print(f"Publishing {path} = {value}")
                    self._known[path] = { 'time' : time.ctime(), 'value' : value }
                    self._client.publish(path,value)

                # Unknown value
                else:
                    path = f'stat/rfxcom/{source}/{key}'

                    #print(f"Unknown {path} = {value}")
                    self._unknown[path] = { 'time' : time.ctime(), 'value' : value }

                self._client.publish('stat/rfxcom/lastrx',time.ctime())


        if (time.time() - self._last) > 60.0:

            with open(KNOWN_LOG,'w') as f:
                for k,v in self._known.items():
                    f.write(f"{k} - {v['time']} - {v['value']}\n")

            with open(UNKNOWN_LOG,'w') as f:
                for k,v in self._unknown.items():
                    f.write(f"{k} - {v['time']} - {v['value']}\n")

rx = RfxCom('/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A6003Q5Y-if00-port0', '127.0.0.1')
rx.run()

