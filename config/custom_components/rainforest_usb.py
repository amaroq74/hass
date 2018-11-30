
from homeassistant.const import (ATTR_STATE, CONF_DEVICE, CONF_NAME, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol

import time 
import serial
import xml.etree.ElementTree as ET
import threading
import logging

DEF_BAUD=115200
DEF_TOUT=120

DOMAIN="rainforest_usb"
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICE): cv.string,
        vol.Required(CONF_NAME):   cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    data = {}

    def rx_data(channel, value):
        if channel in data['channels']:
            data['channels'][channel]._update(value)

    data['name']     = config[DOMAIN].get(CONF_NAME)
    data['channels'] = {}
    data['dev']      = Rainforest(config[DOMAIN].get(CONF_DEVICE),rx_data)

    hass.data[DOMAIN] = data
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, data['dev'].stop)

    return True


#########################################
#          PULL FROM CURRENT COST       #
#########################################
#<InstantaneousDemand>
#   <DeviceMacId>0x00158d00001ab90a</DeviceMacId>
#   <MeterMacId>0x00135001000e547e</MeterMacId>
#   <TimeStamp>0x1a907e66</TimeStamp>
#   <Demand>0x000990</Demand>
#   <Multiplier>0x00000001</Multiplier>
#   <Divisor>0x000003e8</Divisor>
#   <DigitsRight>0x03</DigitsRight>
#   <DigitsLeft>0x0f</DigitsLeft>
#   <SuppressLeadingZero>Y</SuppressLeadingZero>
#</InstantaneousDemand>
#<CurrentSummationDelivered>
#   <DeviceMacId>0x00158d00001ab90a</DeviceMacId>
#   <MeterMacId>0x00135001000e547e</MeterMacId>
#   <TimeStamp>0x1a908965</TimeStamp>
#   <SummationDelivered>0x000000000318163f</SummationDelivered>
#   <SummationReceived>0x0000000000000000</SummationReceived>
#   <Multiplier>0x00000001</Multiplier>
#   <Divisor>0x000003e8</Divisor>
#   <DigitsRight>0x03</DigitsRight>
#   <DigitsLeft>0x0f</DigitsLeft>
#   <SuppressLeadingZero>Y</SuppressLeadingZero>
#</CurrentSummationDelivered>

#<Command>\n<Name>factory_reset</Name>\n</Command>")
#<Command>\n<Name>restart</Name>\n</Command>")

class Rainforest(threading.Thread):
    """Class to handle rainforest data reception."""

    def __init__(self, path, callback):
        threading.Thread.__init__(self)
        self._cb    = callback
        self._path  = path
        self._runEn = True

        self.start() 

    def stop(self):
        self._runEn = False
        self.join()

    def run(self):
        ser   = None
        last  = time.time()
        block = ''

        while self._runEn:

            # Serial port needs to e open
            if ser is None:
                try:
                    ser = serial.Serial(self._path, DEF_BAUD, timeout=DEF_TOUT)
                    ser.flushInput()
                    _LOGGER.info("Opened serial port")
                    last = time.time()
                except Exception as msg:
                    _LOGGER.error("Got exception: {}".format(msg))
                    time.sleep(1)
                    continue

            # No Data
            if (time.time() - last) > 600 :
                _LOGGER.warning("Timeout closing")
                time.sleep(1)
                ser = None
                continue

            # Attempt to read
            try:
                line = ser.readline().decode('utf-8')
                last = time.time()
            except Exception as msg:
                _LOGGER.error("Got exception: {}".format(msg))
                ser = None
                time.sleep(1)
                continue

            # Skip short lines
            if len(line) > 10:
                block = block + line

            # Process block
            try:

                if line.find("</InstantaneousDemand>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("Demand"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    self._cb('rate', value)
                    block = ''

                elif line.find("</CurrentSummationDelivered>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("SummationDelivered"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    self._cb('total', value)
                    block = ''

                elif line.find("</ConnectionStatus>") == 0 or line.find("</TimeCluster>") == 0 :
                    block = ''

            except Exception as msg:
                _LOGGER.warning("Got exception: {}".format(msg))
                block = ''
                ser.flushInput()

