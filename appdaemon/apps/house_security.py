#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')
import hass_secrets as secrets
import zm_camera

import appdaemon.plugins.hass.hassapi as hass
import time
from datetime import datetime, timedelta

##################################
# Button Setup
##################################
GateToggle = {'binary_sensor.car_gate_btn' : 'switch.car_gate'}

##################################
# Constants
##################################
Switches = [ 'dcare_bell', 'gate_bell', 'night_alarm', 'house_alarm', 'door_alarm', 'auto_light' ]

Sounds = { 'gate_bell':  'doorbell.wav',
           'door_bell':  'front_door_and_gate_bell.wav',
           'dcare_bell': 'short_beep.wav' }

CamTime = 120
Cameras = { 'gate_cam'   : zm_camera.ZmCamera('1'),
            'front_cam'  : zm_camera.ZmCamera('2'),
            'garage_cam' : zm_camera.ZmCamera('4'),
            'side_cam'   : zm_camera.ZmCamera('5') }

Lights = { 'auto_light' :'switch.gate_light' }

##################################
# Sensor Setup
##################################
# Setup sensors
SecSensors = { 'binary_sensor.ped_gate'      : [ 'gate_bell',   'dcare_bell',  'gate_cam',    'front_cam',  'night_alarm', 'auto_light' ],
               'switch.car_gate'             : [ 'gate_bell',   'dcare_bell',  'gate_cam',    'front_cam',  'night_alarm', 'auto_light' ],
               'switch.garage_door'          : [ 'dcare_bell',  'garage_cam',  'night_alarm', 'door_alarm'  ],
               'binary_sensor.gate_dbell'    : [ 'door_bell',   'gate_cam',    'front_cam',   'auto_light'  ],
               'binary_sensor.door_dbell'    : [ 'door_bell',   'gate_cam',    'front_cam',   'auto_light'  ],
               'binary_sensor.family_door'   : [ 'front_cam',   'garage_cam',  'night_alarm', 'door_alarm'  ],
               'binary_sensor.front_door'    : [ 'front_cam',   'night_alarm', 'door_alarm'   ],
               'binary_sensor.pbath_door'    : [ 'dcare_bell',  'night_alarm', 'door_alarm'   ],
               'binary_sensor.kitchen_door'  : [ 'dcare_bell',  'night_alarm', 'door_alarm'   ],
               'binary_sensor.dining_door'   : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.garage_rdoor'  : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.garbage_gate'  : [ 'dcare_bell',  'garage_cam'   ],
               'binary_sensor.chickens_gate' : [ 'dcare_bell',  'side_cam'     ],
               'binary_sensor.office_door'   : [ 'dcare_bell'   ],
               'binary_sensor.ivy_gate'      : [ 'dcare_bell'   ],
               'binary_sensor.bedta_motion'  : [ 'house_alarm'  ],
               'binary_sensor.bedr_motion'   : [ 'house_alarm'  ],
               'binary_sensor.living_motion' : [ 'house_alarm'  ],
               'binary_sensor.office_motion' : [ 'house_alarm'  ],
               'binary_sensor.master_motion' : [ 'house_alarm'  ],
               'binary_sensor.family_motion' : [ 'house_alarm'  ],
               'binary_sensor.garage_motion' : [ 'house_alarm'  ] }


class HouseSecurity(hass.Hass):

    def initialize(self):

        # Day care alarm
        self._dcSensors = []
        for k,v in SecSensors.items():
            if 'dcare_bell' in v:
                self._dcSensors.append(k)

        self.run_every(self.day_care, datetime.now() + timedelta(seconds=5), 5)

        # Security sounds
        self._lastSound = {}

        # Security items
        for k in SecSensors:
            self._lastSound[k] =0
            self.listen_state(self.sec_update,k)

        # Stop cameras
        for k,v in Cameras.items():
            try:
                v.cancelCamera()
            except:
                self.log("Error cancelling camera: {}".format(k))


    # Gate toggle
    def gate_toggle(self, entity, attribute, old, new, *args, **kwargs):
        if new == 'on':
            sw = GateToggle[entity]
            cur = self.get_state(sw)

            if cur == 'on':
                self.turn_off(sw)
            else:
                self.turn_on(sw)


    # Day care alarm, 5 second intervals
    def day_care(self, *args, **kwargs):
        if self.get_state('input_boolean.dcare_bell') == 'on':
            count = 0
            lst = []
            for sen in self._dcSensors:
                if self.get_state(sen) == 'on':
                    count += 1
                    lst.append(sen)

            if count != 0:
                self.log("Playing daycare alarm for: {}".format(lst))
                self.call_service('media_player/play_media',
                                  entity_id='media_player.kitchen_speaker',
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ Sounds['dcare_bell'],
                                  media_content_type='music')


    # Security update
    def sec_update(self, entity, attribute, old, new, *args, **kwargs):
        if new == old or new == 'off':
            return

        # Procss each action
        for action in SecSensors[entity]:

            # Make sure action is enabled
            if action not in Switches or self.get_state('input_boolean.' + action) == 'on':

                # Check for sound
                if (time.time() - self._lastSound[entity]) > 15 and action in Sounds:
                    self._lastSound[entity] = time.time()
                    self.log("Playing sound for: {}".format(entity))
                    self.call_service('media_player/play_media',
                                      entity_id='media_player.kitchen_speaker',
                                      media_content_id='http://172.16.20.1:8123/local/sounds/' + Sounds[action],
                                      media_content_type='music')

                # Check for camera
                if action in Cameras:
                    try:
                        Cameras[action].triggerCamera(entity,CamTime)
                        self.log("Triggering camera: {}".format(action))
                    except:
                        self.log("Error triggering camera: {}".format(action))

                # Check for lights
                if action in Lights:
                    self.turn_on(Lights[action])


#import smtplib
#from email.mime.multipart import MIMEMultipart
##from email.mime.text      import MIMEText

# Notifications
#EmailAddrs = 'ryan@amaroq.com,steph@amaroq.com'

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


