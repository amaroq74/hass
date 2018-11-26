
import time 
import serial
import xml.etree.ElementTree as ET
import threading

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
                    print("Opened serial port")
                except Exception as msg:
                    print("Got exception: {}".format(msg))
                    time.sleep(1)
                    continue

            # No Data
            curr = time.time()
            if (curr - last) > 600 :
                print("Timeout closing")
                ser = None
                time.sleep(1)
                continue

            # Attempt to read
            try:
                line = ser.readline().decode('utf-8')
                print("Read line: {}".format(line))
            except Exception as msg:
                print("Got exception: {}".format(msg))
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
                    self._cb('current', value, 'KW')
                    block = ''

                elif line.find("</CurrentSummationDelivered>") == 0 :
                    tree  = ET.XML( block )
                    value = float(int(tree.findtext("SummationDelivered"),0))
                    mult  = float(int(tree.findtext("Multiplier"),0))
                    div   = float(int(tree.findtext("Divisor"),0))

                    if div > 0 : value = (value * mult) / div
                    self._cb('total', value, 'KW_Hours')
                    block = ''

                elif line.find("</ConnectionStatus>") == 0 or line.find("</TimeCluster>") == 0 :
                    block = ''

            except Exception as msg:
                print("Got exception: {}".format(msg))
                block = ''
                ser.flushInput()


# Test program
if __name__ == "__main__":

    def dump(key, value, units):
        print("{} = {} {}".format(key,value,units))

    rf = Rainforest('/dev/serial/by-id/usb-Rainforest_RFA-Z106-RA-PC_RAVEn_v2.3.21-if00-port0',dump)

    while True:
        time.sleep(1)

