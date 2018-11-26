
import time 
import serial
import xml.etree.ElementTree as ET

DEF_BAUD=115200
DEF_TOUT=120

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

class RainforestException(Exception):
        pass


class Rainforest:
    """Class to handle rainforest data reception."""


    def __init__(self, path):
        """ Create RxRainforst class.

        Arguments:
           path:      path to device
        """
        self._path = path
        self._ser  = None
        self._log  = None


    def open(self):
        self._ser = serial.Serial(self._path, DEF_BAUD, timeout=DEF_TOUT)
        self._ser.flushInput()

    def openLog(self):
        self._log = open("power_log.txt","a")

    def close(self):
        self._ser.close()
        self._ser = None

    def factoryReset(self):
        self._ser.write("<Command>\n<Name>factory_reset</Name>\n</Command>\n")

        while(True):
            d = self._ser.readline()

    def restart(self):
        self._ser.write("<Command>\n<Name>restart</Name>\n</Command>\n")

        while(True):
            d = self._ser.readline()

    def getData(self) :
        line  = ""
        block = ""
        last  = time.time()

        while True :
            curr = time.time()
            if (curr - last) > 600 : raise RainforestException("Timeout waiting for data!")

            try:
                line = self._ser.readline()
            except Exception as msg:
                raise RainforestException("Serial error: {}".format(msg))

            if len(line) > 10:
                block = block + line.decode('utf-8')

            # Process block
            try:

                if line.find("</InstantaneousDemand>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("Demand"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    return "current", value, "KW"

                elif line.find("</CurrentSummationDelivered>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("SummationDelivered"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    return "total", value, "KW_Hours"

                elif line.find("</ConnectionStatus>") == 0 or line.find("</TimeCluster>") == 0 :
                    block = ""

            except Exception as msg: # Catch XML errors (occasionally the current cost outputs malformed XML)
                block = ""
                self._ser.flushInput()

