#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')
import hass_secrets as secrets

import appdaemon.plugins.hass.hassapi as hass
import time
from datetime import datetime, timedelta

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from urllib.parse import urlencode, quote_plus

##################################
# Button Setup
##################################
GateToggle = {'binary_sensor.car_gate_btn' : 'switch.car_gate'}

##################################
# Constants
##################################
Switches = [ 'dcare_bell', 'night_alarm', 'house_alarm', 'door_alarm']

SoundDevices = [ 'media_player.kitchen_speaker',
                 'media_player.shed_speaker',
                 'media_player.garage_speaker' ]

DcareDevice = 'media_player.kitchen_speaker'

Sounds = { 'gate_bell':  'doorbell.wav',
           'door_bell':  'front_door_and_gate_bell.wav',
           'dcare_bell': 'short_beep.wav' }

Lights = { 'auto_light' : ['light.gate_light',
                           'light.xmas_lights',
                           'light.entry_light',
                           'light.yard_lights1',
                           'light.yard_lights2'] }

# Alarm group levels
EmailLevels = {'night_alarm' : 'Alarm',
               'sump_alarm'  : 'Alarm',
               'door_bell'   : 'Alert',
               'door_alarm'  : 'Alarm',
               'house_alarm' : 'Alarm'}

EmailAddrs = 'ryan@amaroq.com'

##################################
# Sensor Setup
##################################
# Setup sensors
SecSensors = { 'binary_sensor.ped_gate'      : [ 'gate_bell',   'dcare_bell',  'night_alarm', 'auto_light' ],
               'switch.car_gate'             : [ 'gate_bell',   'dcare_bell',  'night_alarm', 'auto_light' ],
               'switch.garage_door'          : [ 'dcare_bell',  'night_alarm', 'door_alarm'  ],
               'switch.garage_door'          : [ 'night_alarm', 'door_alarm'  ],
               'binary_sensor.gate_bell'     : [ 'door_bell',   'auto_light'  ],
               'binary_sensor.door_bell'     : [ 'door_bell',   'auto_light'  ],
               'binary_sensor.family_door'   : [ 'night_alarm', 'door_alarm'  ],
               'binary_sensor.front_door'    : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.pbath_door'    : [ 'dcare_bell',  'night_alarm', 'door_alarm'   ],
               'binary_sensor.kitchen_door'  : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.dining_door'   : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.garage_rdoor'  : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.master_door'   : [ 'night_alarm', 'door_alarm'   ],
               'binary_sensor.garbage_gate'  : [ 'dcare_bell'   ],
               'binary_sensor.patio_gate'    : [ 'dcare_bell'   ],
               'binary_sensor.chickens_gate' : [ 'dcare_bell'   ],
               'binary_sensor.office_door'   : [ 'dcare_bell'   ],
               'binary_sensor.ivy_gate'      : [ 'dcare_bell'   ],
               'binary_sensor.bedta_motion'  : [ 'house_alarm'  ],
               'binary_sensor.bedr_motion'   : [ 'house_alarm'  ],
               'binary_sensor.living_motion' : [ 'house_alarm'  ],
               'binary_sensor.office_motion' : [ 'house_alarm'  ],
               'binary_sensor.master_motion' : [ 'house_alarm'  ],
               'binary_sensor.family_motion' : [ 'house_alarm'  ],
               'binary_sensor.garage_motion' : [ 'house_alarm'  ],
               'binary_sensor.sump_alarm'    : [ 'sump_alarm'   ] }


class HouseSecurity(hass.Hass):

    def warning(self,msg):
        self.log(msg,level='WARNING')

    def error(self,msg):
        self.log(msg,level='ERROR')

    def debug(self,msg):
        self.log(msg,level='DEBUG')

    def initialize(self):

        # Day care alarm
        self._dcSensors = []
        for k,v in SecSensors.items():
            if 'dcare_bell' in v:
                self._dcSensors.append(k)

        self.run_every(self.day_care, datetime.now() + timedelta(seconds=5), 5)

        # Security sounds
        self._lastSound = {}
        self._lastEmail = {}

        # Security items
        for k in SecSensors:
            self._lastSound[k] =0
            self._lastEmail[k] = 0
            self.listen_state(self.sec_update,k)

        # Button Toggles
        for k in GateToggle:
            self.listen_state(self.gate_toggle,k)


    # Gate toggle
    def gate_toggle(self, entity, attribute, old, new, *args, **kwargs):

        if entity in GateToggle:

            self.log("Got gate toggle {} {} {} {}".format(entity,attribute,old,new))
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
                                  entity_id=DcareDevice,
                                  media_content_id='http://172.16.20.1:8123/local/sounds/'+ Sounds['dcare_bell'],
                                  media_content_type='music')


    # Security update
    def sec_update(self, entity, attribute, old, new, *args, **kwargs):
        self.debug("Got event {} {} {} {}".format(entity,attribute,old,new))
        emailActions = []

        if new == old or new == 'off' or old != 'off':
            return

        # Procss each action
        for action in SecSensors[entity]:

            # Make sure action is enabled
            if action not in Switches or self.get_state('input_boolean.' + action) == 'on':

                # Check for sound without radio gate
                if (time.time() - self._lastSound[entity]) > 15 and action in Sounds:
                    self._lastSound[entity] = time.time()
                    self.log("Playing sound for: {}".format(entity))

                    for dev in SoundDevices:
                        self.call_service('media_player/play_media',
                                          entity_id=dev,
                                          media_content_id='http://172.16.20.1:8123/local/sounds/' + Sounds[action],
                                          media_content_type='music')

                # Check for lights
                if self.get_state('sun.sun') == 'below_horizon':
                    for light in Lights[action]:
                        self.turn_on(light)

                # Check for email actions
                if action in EmailLevels:
                    emailActions.append(action)

        # Form email
        if len(emailActions) != 0 and (time.time() - self._lastEmail[entity]) > 15:
            self._lastEmail[entity] = time.time()
            level = 'Alert'

            for action in emailActions:
                if EmailLevels[action] == 'Alarm':
                    level = 'Alarm'

            # Send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = level + ": " + entity
            msg['From']    = "home@amaroq.com"
            msg['To']      = EmailAddrs

            text  = '<center>\n'
            text += '<b>{} triggered by sensor {}</b><br><p>\n'.format(level,entity)

            msg.attach(MIMEText(text, 'html'))

            try:
               smtpObj = smtplib.SMTP('localhost')
               smtpObj.sendmail('home@amaroq.com', EmailAddrs, msg.as_string())
               self.log("Sent email to: " + EmailAddrs)
            except smtplib.SMTPException:
               self.error("Error sending alarm email to: " + EmailAddrs)

