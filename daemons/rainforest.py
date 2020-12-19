#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import serial
import xml.etree.ElementTree as ET
import threading
import logging
import sys

DEF_BAUD=115200
DEF_TOUT=120
DEF_DEVICE="/dev/serial/by-id/usb-Rainforest_RFA-Z106-RA-PC_RAVEn_v2.3.21-if00-port0"

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

    def __init__(self, path, server):
        threading.Thread.__init__(self)
        self._path   = path
        self._runEn  = True
        self._server = server

        self._client = mqtt.Client("rainforest")
        self._client.connect(server)

        self.start()

    def stop(self, *args, **kwargs):
        self._runEn = False
        self.join()

    def running(self):
        return self._runEn

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
                    sys.stderr.write("Opened serial port\n")
                    last = time.time()
                except Exception as msg:
                    sys.stderr.write(f"Got exception: {msg}\n")
                    time.sleep(1)
                    continue

            # No Data
            if (time.time() - last) > 600 :
                sys.stderr.write("Timeout closing\n")
                time.sleep(1)
                ser = None
                continue

            # Attempt to read
            try:
                line = ser.readline().decode('utf-8')
                last = time.time()
            except Exception as msg:
                sys.stderr.write("Got exception: {msg}\n")
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

                    self._client.publish('stat/rainforest/rate',value)
                    self._client.publish('stat/rainforest/lastrx',time.ctime())
                    block = ''

                elif line.find("</CurrentSummationDelivered>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("SummationDelivered"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    self._client.publish('stat/rainforest/total',value)
                    self._client.publish('stat/rainforest/lastrx',time.ctime())
                    block = ''

                elif line.find("</ConnectionStatus>") == 0 or line.find("</TimeCluster>") == 0 :
                    block = ''

            except Exception as msg:
                block = ''
                sys.stderr.write(f"Got exception: {msg}\n")
                self._runEn = False
                #ser.flushInput()

rf = Rainforest(DEF_DEVICE,'127.0.0.1')
time.sleep(5)

while rf.running():
    time.sleep(1)

rf.stop()

