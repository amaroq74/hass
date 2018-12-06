
import sys
sys.path.append('/amaroq/hass/pylib')

from homeassistant.const import (ATTR_STATE, CONF_DEVICE, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol
import logging
import hass_arduino
import threading

DOMAIN="arduino_relay"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hosts = config[DOMAIN].get('hosts')

    data = {}
    data['hosts']  = {}
    data['boards'] = {}

    for host in hosts:
        device = hosts[host]['device']
        xbee   = hosts[host]['xbee']
        boards = hosts[host]['boards']

        data['hosts'][host] = hass_arduino.ArduinoRelayHost(host,device,xbee)

        for k,v in boards.items():
            brd = hass_arduino.ArduinoRelayBoard(k, data['hosts'][host], v)
            data['hosts'][host].addNode(brd)
            data['boards'][k] = brd

    def stop_arduino(*args, **kwargs):
        for host in data['hosts']:
            host.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_arduino)

    hass.data[DOMAIN] = data

    return True

