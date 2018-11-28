#!/usr/bin/env python3

import appdaemon.plugins.hass.hassapi as hass
import time
from datetime import datetime, timedelta

BellSensors = [ 'binary_sensor.car_gate', 'binary_sensor.ped_gate' ]
GateSensors = [ 'binary_sensor.gate_bell', 'binary_sensor.door_bell' ]

DcSensors   = [ 'binary_sensor.car_gate', 'binary_sensor.ped_gate', 'binary_sensor.garage_door', 
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
    def day_care(self, kwargs):
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
    def sec_sound(self, entity, attribute, old, new, kwargs):
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

