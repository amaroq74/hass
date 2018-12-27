#!/usr/bin/env python3

import appdaemon.plugins.hass.hassapi as hass

class HouseEntertainment(hass.Hass):

    def warning(self,msg):
        self.log(msg,level='WARNING')

    def error(self,msg):
        self.log(msg,level='ERROR')

    def debug(self,msg):
        self.log(msg,level='DEBUG')

    def initialize(self):

        # Chrome state
        self.listen_state(self.chrome_changed,'media_player.chrome_family')

    # Turn on TV when chrome starts
    def chrome_changed(self, entity, attribute, old, new, *args, **kwargs):
        pass
        if new != 'off' and new != 'unavailable' and old == 'off':
            self.log("Setting Harmony state due to chrome state new {} old {} harmony = {}".format(new,old,self.get_state('remote.family_room')))
            self.turn_on("remote.family_room", activity = "Watch Chrome tv" )

