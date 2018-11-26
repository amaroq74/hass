#!/usr/bin/env python3

import sys,os
sys.path.append('/amaroq/hass/pylib')

# Libraries
import rfxcom
import logging
import time

class RfxcomPost(hass.Hass):

    def initialize(self):
        self._devPath = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A6003Q5Y-if00-port0"
        self._error   = False
        self._lastRx  = time.time()

        # Device List
        self._devices = {}
        self._devices['thgr228n.c3']  = {id:'sensor.bedta',    name:'BedTA Temp'}
        self._devices['thwr288a.84']  = {id:'sensor.camper',   name:'Camper'}
        self._devices['thgr228n.1f']  = {id:'sensor.garage',   name:'Garage'}
        self._devices['thgr810.cc']   = {id:'sensor.bedr',     name:'BedR'}
        self._devices['bthr918n.1d']  = {id:'sensor.indoor',   name:'Indoor'}
        self._devices['thgr228n.75']  = {id:'sensor.master',   name:'Master'}
        self._devices['thgr228n.94']  = {id:'sensor.shed',     name:'Shed'}
        self._devices['thgr810.02']   = {id:'sensor.outdoor',  name:'Outdoor'}
        self._devices['f007pf.23.08'] = {id:'sensor.pool',     name:'Pool'}
        self._devices['pcr800.1d']    = {id:'sensor.rain',     name:'Rain'}
        self._devices['wgr800.30']    = {id:'sensor.wind',     name:'Wind'}
        self._devices['thn132n.63']   = {id:'sensor.chickens', name:'Chickens'}



rfx = rfxcom.RFXCom(on_message,device=devPath)
rfx.setup()
rfx.run()

while not error:
    try:
        time.sleep(1)

        if (time.time() - lastRx) > 300:
           db.setLog('err','main',"Its been 5 minutes since last rx!")
           error = True

    except KeyboardInterrupt:
        break

db.setLog("inf", "main", "Stopping!")







    def on_message(self):
        global devices
        global lastRx

        source = message['source']
        topic  = message.topic
        lastRx = time.time()

        if devices.has_key(source):
            device = devices[source]
            log    = True;
        else:
            device = 'unknown' + '.' + message['source']
            log    = False;

        for key in message.values:

            if key == 'battery': 
                db.setSensor(device,key,message[key],'%',log)

            elif key == 'temp':
                db.setSensor(device,key,message[key],'c',log)

            elif key == 'humidity':
                db.setSensor(device,key,message[key],'%',log)

    #        elif key == 'speed' and topic == 'rain':
    #            db.setSensor(device,'count_rate',message[key],'mmph',log)

            elif key == 'total' and topic == 'rain':
                rainCurr = message[key]
                db.setSensor(device,'count',rainCurr,'mm',log)

    #            rainHour = db.getSensorHour(device,'count')
    #            if rainHour and rainCurr > rainHour: 
    #                db.setSensor(device,'count_hour',rainCurr - rainHour,'mm',log)
    #            else:
    #                db.setSensor(device,'count_hour',0,'mm',log)

    #            rainDay = db.getSensorDay(device,'count')
    #            if rainDay and rainCurr > rainDay: 
    #                db.setSensor(device,'count_day',rainCurr - rainDay,'mm',log)
    #            else:
    #                db.setSensor(device,'count_day',0,'mm',log)

            elif key == 'barometer':
                value = message[key] + 6.0   # Alititude adjustment
                db.setSensor(device,'pressure',value,'hpa',log)

            elif key == 'dir':
                db.setSensor(device,'direction',message[key],'deg',log)

            elif key == 'speed' and topic == 'wind':
                db.setSensor(device,key,message[key],'mps',log)

            elif key == 'avgspeed' and topic == 'wind':
                db.setSensor(device,'speed_average',message[key],'mps',log)



