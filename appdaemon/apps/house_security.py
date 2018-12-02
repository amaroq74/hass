#!/usr/bin/env python3

import appdaemon.plugins.hass.hassapi as hass
import time
from datetime import datetime, timedelta

GateSensors = [ 'switch.car_gate', 'binary_sensor.ped_gate' ]
BellSensors = [ 'binary_sensor.gate_bell', 'binary_sensor.door_bell' ]

DcSensors   = [ 'switch.car_gate', 'binary_sensor.ped_gate', 'switch.garage_door', 
                'binary_sensor.pbath_door', 'binary_sensor.kitchen_door', 'binary_sensor.office_door',
                'binary_sensor.chicken_gate', 'binary_sensor.ivy_gate', 'binary_sensor.garbage_gate' ]

GateSound = 'doorbell.wav'
BellSound = 'front_door_and_gate_bell.wav'
DcSound   = 'short_beep.wav'

class HouseSecurity(hass.Hass):

    def initialize(self):

        # Day care alarm
        self.run_every(self.day_care, datetime.now() + timedelta(seconds=5), 5)

        # Security sounds
        self._lastSound = {}

        for k in GateSensors:
            self._lastSound[k] = time.time()
            self.listen_state(self.sec_sound,k)

        for k in BellSensors:
            self._lastSound[k] = time.time()
            self.listen_state(self.sec_sound,k)

    # Day care alarm, 5 second intervals
    def day_care(self, *args, **kwargs):
        if self.get_state('input_boolean.dcare_bell') == 'on':
            count = 0
            lst = []
            for sen in DcSensors:
                if self.get_state(sen) == 'on':
                    count += 1
                    lst.append(sen)

            if count != 0:
                self.log("Playing daycare alarm for: {}".format(lst))
                self.call_service('media_player/play_media',
                                  entity_id='media_player.kitchen_speaker',
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ DcSound,
                                  media_content_type='music')

    # Security Sounds
    def sec_sound(self, entity, attribute, old, new, *args, **kwargs):
        ldiff = time.time() - self._lastSound[entity]

        if ldiff > 30 and new != old and new == 'on':
            self._lastSound[entity] = time.time()

            if entity in BellSensors:
                self.log("Playing sound for: {}".format(entity))
                self.call_service('media_player/play_media',
                                  entity_id='media_player.kitchen_speaker',
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ BellSound,
                                  media_content_type='music')

            elif self.get_state('input_boolean.gate_bell') == 'on' and entity in GateSensors:
                self.log("Playing sound for: {}".format(entity))
                self.call_service('media_player/play_media',
                                  entity_id='media_player.kitchen_speaker',
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ GateSound,
                                  media_content_type='music')

            elif self.get_state('input_boolean.dcare_bell') == 'on' and entity in DcSensors:
                self.log("Playing daycare alarm for: {}".format(entity))
                self.call_service('media_player/play_media',
                                  entity_id='media_player.kitchen_speaker',
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ DcSound,
                                  media_content_type='music')





# Add relative path
#import sys,os
#sys.path.append(os.path.dirname(__file__) + "/../pylib")

# Libraries
#import time
#from amaroq_home import zoneminder
#from amaroq_home import mysql
#import smtplib
#from email.mime.multipart import MIMEMultipart
##from email.mime.text      import MIMEText

# Notifications
#EmailAddrs = 'ryan@amaroq.com,steph@amaroq.com'

# Constants
#service = "home_security"

# Mysql
#db = mysql.Mysql(service)

# Cameras
#CamTime = 120
#Cameras = { 'GateCam'   : zoneminder.ZmCamera("1"),
#            'FrontCam'  : zoneminder.ZmCamera("2"),
#            'GarageCam' : zoneminder.ZmCamera("4"),
#            'SideCam'   : zoneminder.ZmCamera("5") }
#
## Alarm group levels
#GroupLevels = {'night' : 'Alarm',
#               'dcare' : 'Alert',
#               'door'  : 'Alarm',
#               'house' : 'Alarm'}

# Variables
#lastAlarm = 0

# Setup sensors
#SecSensors = { 'Car_Gate'      : {'type':'gate',   'lights':['Gate_Light'], 'cameras':['GateCam','FrontCam']   ,'groups':['night']                 },
#               'Ped_Gate'      : {'type':'gate',   'lights':['Gate_Light'], 'cameras':['GateCam','FrontCam']   ,'groups':['night']                 },
#               'Gate_Bell'     : {'type':'bell',   'lights':['Gate_Light'], 'cameras':['GateCam','FrontCam']   ,'groups':[]                        },
#               'Door_Bell'     : {'type':'bell',   'lights':['Gate_Light'], 'cameras':['GateCam','FrontCam']   ,'groups':[]                        },
#               'Garage_Door'   : {'type':'door',   'lights':[],             'cameras':['GarageCam']            ,'groups':['night','dcare','door']  },
#               'PBath_Door'    : {'type':'door',   'lights':[],             'cameras':[]                       ,'groups':['night','dcare','door']  },
#               'Kitchen_Door'  : {'type':'door',   'lights':[],             'cameras':[]                       ,'groups':['night','dcare','door']  },
#               'Dining_Door'   : {'type':'door',   'lights':[],             'cameras':[]                       ,'groups':['night','door']          },
#               'Family_Door'   : {'type':'door',   'lights':[],             'cameras':['FrontCam','GarageCam'] ,'groups':['night','door']          },
#               'Front_Door'    : {'type':'door',   'lights':[],             'cameras':['FrontCam']             ,'groups':['night','door']          },
#               'Garage_Door2'  : {'type':'door',   'lights':[],             'cameras':[]                       ,'groups':['night','door']          },
#               'Office_Door'   : {'type':'door',   'lights':[],             'cameras':[]                       ,'groups':['dcare']                 },
#               'East_Gate'     : {'type':'gate',   'lights':[],             'cameras':['GarageCam']            ,'groups':['dcare']                 },
#               'West_Gate'     : {'type':'gate',   'lights':[],             'cameras':[]                       ,'groups':['dcare']                 },
#               'Gar_Gate'      : {'type':'gate',   'lights':[],             'cameras':['SideCam']              ,'groups':['dcare']                 },
#               'BedTA_Motion'  : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'BedR_Motion'   : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'Living_Motion' : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'Office_Motion' : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'Master_Motion' : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'Family_Motion' : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 },
#               'Garage_Motion' : {'type':'motion', 'lights':[],             'cameras':[]                       ,'groups':['house']                 } }

# Add tracking fields
#for k,v in SecSensors.items():
#    v['state'] = 'normal'
#    v['lastAlarm'] = 0


# Process results
#def secCb(res):
#    global db
#    global Cameras
#    global SecSensors
#    global lastAlarm
#
#    sensor = res["zone"]
#    state  = res["event"]
#
#    typ  = SecSensors[sensor]['type']
#    old  = SecSensors[sensor]['state']
#    SecSensors[sensor]['state'] = state
#
#    # No state change
#    if old == state: return
#
#    # Sensor going to alert
#    if state == 'alert':
#
#        # Auto light
#        if len(SecSensors[sensor]['lights']) > 0 and db.getVariable('Security','auto_light') > 0:
#            for light in SecSensors[sensor]['lights']:
#                db.setDevice(light,"100")
#            db.setLog("inf", sensor, "Turned on lights: " + str(SecSensors[sensor]['lights']))
#
#        # Camera Trigger
#        for cam in SecSensors[sensor]['cameras']:
#            try:
#                Cameras[cam].triggerCamera(sensor,CamTime)
#                db.setLog("inf", sensor, "Triggered camera: " + cam)
#            except:
#                db.setLog("wrn", sensor, "Error triggering camera: " + cam)
#
#        # Determine if any of the groups are armed
#        if (time.time() - SecSensors[sensor]['lastAlarm']) > 3600:
#            level = None
#
#            for grp in SecSensors[sensor]['groups']:
#                if db.getVariable('Security',grp + '_arm') > 0:
#                    level = GroupLevels[grp]
#                    if level == 'Alarm':
#                        break;
#
#            if level is not None:
#                SecSensors[sensor]['lastAlarm'] = time.time()
#
#                # Send email
#                msg = MIMEMultipart('alternative')
#                msg['Subject'] = level + ": " + sensor
#                msg['From']    = "home@amaroq.com"
#                msg['To']      = EmailAddrs
#
#                text = level + " triggered by sensor " + sensor + "\n"
#                text += "\nhttps://www.amaroq.net/home/?key=lolhak\n"
#                text += "\nhttps://www.amaroq.net/home/cameras/\n"
#                msg.attach(MIMEText(text, 'plain'))
#
#                try:
#                   smtpObj = smtplib.SMTP('localhost')
#                   smtpObj.sendmail('home@amaroq.com', EmailAddrs, msg.as_string())
#                   db.setLog("inf", sensor, "Sent email to " + EmailAddrs)
#                except smtplib.SMTPException:
#                   db.setLog("wrn", sensor, "Error sending alarm email to " + EmailAddrs)
#
#    db.setLog("inf", sensor, "Processed event for state " + state)
#
## Callback config for sensors
#for sensor in SecSensors:
#    db.addPollCallback(secCb,"security_current", {"zone"  :sensor})
#
#print "Security Daemon Starting"
#
## Setup network
#db.pollEnable(0.5)
#db.setLog("inf", "main", "Starting!")
#
#while True:
#    try:
#        time.sleep(.1)
#    except KeyboardInterrupt:
#        break
#
#db.setLog("inf", "main", "Stopping!")
#
## Stop
#for cam in Cameras:
#    Cameras[cam].halt()
#
#db.pollDisable()
#db.disconnect()
#print "Security Daemon Stopped"
#

