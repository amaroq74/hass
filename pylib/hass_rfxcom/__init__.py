#!/usr/bin/env python2

import glob
import re
import time
import struct
import logging

import sys,os
sys.path.append(os.path.dirname(__file__) + "/..")

import hass_rfxcom.parsers

class RFXError(Exception):
    """Exception indicating communication with the device has gone screwy."""
    pass

class Pyserial(object):
    def __init__(self, device, baudrate):
        import serial
        device = self._find_device(device)
        self.ser = serial.Serial(device, baudrate=baudrate)
        self.ser.timeout = 0.500 # 500ms
        self.ser.interCharTimeout = 0.030 # 30ms

    def _find_device(self, device):
        serial_ports = glob.glob(device)
        if not serial_ports:
            raise RFXError('Error: No USB serial ports found')
            
        return serial_ports[0]

    def flush(self):
        self.ser.flushInput()

    def write(self, data):
        self.ser.write(data.encode('utf-8'))

    def read(self, bytes):
        ret = self.ser.read(bytes)
        return ret

class RFXCom(object):
    """Main class

    >>> i = 0
    >>> rfx = None
    >>> def on_message(m):
    ...     global i, rfx
    ...     i += 1
    ...     print m
    ...     if i == 3:
    ...         rfx.stop()
    >>> rfx = RFXCom(on_message, serial_type=FakeRFXSerial)
    >>> rfx.setup()
    >>> rfx.run()
    topic: x10, device: 11, source: a11, command: on, group: a
    topic: x10, device: 01, source: a01, command: off, group: a
    topic: homeeasy, device: group, source: 31F8177G, command: off, address: 31f8177
    """

    parsers = [ getattr(hass_rfxcom.parsers, x)() for x in hass_rfxcom.parsers.__all__ ]

    def __init__(self, on_message, dedup=2.5, device='/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_*-if00-port0', serial_type=Pyserial):
        self.on_message = on_message
        self.dedup = dedup
        self.device = device
        self.serial_type = serial_type
        
        self.logger = logging.getLogger('rfxcom')
        self.stopping = False
        self.last_messages = []
        self.last_timestamps = []

    def _connect(self):
        self.fin = self.serial_type(device=self.device, baudrate=4800)

    def setup(self):
        self.logger.info('Connecting...')
        self._connect()

        retries = 5
        while retries > 0:
            try:
                self._setup()
                return
            except RFXError:
                self.logger.info('Failed, retrying (%d more retries)' % retries)
                retries -= 1
                time.sleep(1)


    def _setup(self):
        self.fin.flush()

        # enable RFXCOM variable length mode
        self.fin.write('\xf0\x2c')
        self.expect('\x2c')

        # version request, unnecessary and slow without slave
        #self.fin.write('\xf0\x20')
        #self.re_expect('M.(S.)?')

        # enable all possible receiving modes
        self.fin.write('\xf0\x2a')
        self.expect('\x2c') # 2c not 2a as expected??

        self.logger.info('Initialised successfully')

    def expect(self, expected):
        r = self.fin.read(len(expected))
        if r != expected:
            raise RFXError('Expected %r got %r' % (expected, r))

    def re_expect(self, expected, length=None):
        if not length:
            length = len(expected)
        r = self.fin.read(length)
        regex = re.compile('^'+expected+'$')
        if not regex.match(r):
            raise RFXError('Expected %r got %r' % (expected, r))

    def run(self):
        while not self.stopping:
            message = self.run_once()
            if message:
                self.on_message(message)
            
    def run_once(self):
        self.fin.timeout = 1.00 # wait forever
        while not self.stopping:
            b = self.fin.read(1)
            if b:
                break
        if self.stopping:
            return

        length = ord(b) # number of bits to follow
        bytes = int(((length & 0x7F) + 7) / 8)
        
        self.fin.timeout = .030 # 30ms
        data = self.fin.read(bytes)
        if len(data) == bytes:
            return self.decode(length, data)
        else:
            self.logger.error('Read short - expected %d, received %d bytes' % (bytes, len(data)))
            return None

    def stop(self):
        self.stopping = True

    def decode(self, length, packet):
        packet = struct.unpack('%dB' % len(packet), packet)

        self.logger.debug('Processing data: [%s]' % (' '.join('%02x' % d for d in packet)))

        for parser in self.parsers:
            message = parser.parse(length, packet)
            if message:
                # clear old messages
                now = time.time()
                expire_before = now - self.dedup
                while self.last_messages and self.last_timestamps[0] < expire_before:
                    self.last_messages.pop(0)
                    self.last_timestamps.pop(0)

                # duplicate message?
                if message in self.last_messages:
                    # update timestamp and move to front so continuous transmissions are treated as one
                    # (I'm looking at you HomeEasy 403 PIR)
                    i = self.last_messages.index(message)
                    self.last_messages.pop(i)
                    self.last_timestamps.pop(i)
                    self.last_messages.append(message)
                    self.last_timestamps.append(now)
                    
                    self.logger.debug('Suppressed duplicate message %s' % message)
                    return None

                # record for future suppression
                self.last_messages.append(message)
                self.last_timestamps.append(now)

                self.logger.info('Message: %s' % message)
                return message
        
        self.logger.warn('Unhandled data: [%s]' % (' '.join('%02x' % d for d in packet)))
        return None

