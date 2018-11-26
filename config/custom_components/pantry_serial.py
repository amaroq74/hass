#!/usr/bin/env python2
import serial

# Add relative path
import sys,os
sys.path.append(os.path.dirname(__file__) + "/../pylib")

# Libraries
import time
from amaroq_home import mysql
from amaroq_home import arduino_relay
from amaroq_home import usb_paths

# Constants
usbPath = "2-1.1:1.0"
service = "pantry"

# Variables
error = False

# Mysql
db = mysql.Mysql(service)
db.setLog("inf", "main", "Starting!")

devPath = usb_paths.findUsbDevice(usbPath)
db.setLog("inf", "main", "Using device " + devPath)

# Serial device
ser = serial.Serial(port = devPath, baudrate = 9600)

# Timeout 
lastRx = time.time()

# Setup Device
rboard = arduino_relay.ArduinoRelayBoard("Pantry",300,10)

# Oututs
rboard.addOutput(0, arduino_relay.ArduinoRelayOutput ("Other", "House_Heat", "OnOff", True,  60*35))
rboard.addOutput(1, arduino_relay.ArduinoRelayOutput ("Other", "House_Fan",  "OnOff", False, 60*60*2))

# Inputs
rboard.addInput (0, arduino_relay.ArduinoRelaySecurity ("Gate_Bell", 300, False))
rboard.addInput (1, arduino_relay.ArduinoRelaySecurity ("Door_Bell", 300, False))
rboard.addInput (3, arduino_relay.ArduinoRelayButton   ("Car_Gate",  300, False))


# Transmit function
def serTransmit(addr,msg):
    global ser
    global error

    try:
        ser.write(msg + "\n")
    except:
        db.setLog("err", "serTransmit", "Write exception!")
        error = True


# Setup and generate device list
db.deleteDevices(service)
devList = rboard.setupNode(service,db,serTransmit)
lastCmd = {i:0 for i in devList}


# Mysql command processor
def mysql_cmd(cmd):
    global devList
    global lastCmd

    if cmd['age'] < 10 and cmd['time'] != lastCmd[cmd['name']]:
        lastCmd[cmd['name']] = cmd['time']
        devList[cmd['name']].setLevel(cmd['level'])


# Mysql callbacks
db.addPollCallback(mysql_cmd,"devices",{'service':service})

print "Pantry Daemon Starting"

# Setup network
db.pollEnable(0.1)

# Process received data and update devices
while not error:
    try:

        # Check for serial data
        if ser.inWaiting() > 0:
           lastRx = time.time()
           rboard.rxData("",ser.readline())
        else:
           time.sleep(.01)

        # Update device
        rboard.update()

        # Its been a while since we have received a message
        if (time.time() - lastRx) > 300:
            db.setLog("err", "main", "Its been 5 minutes since last message rx!")
            error = True

    except KeyboardInterrupt:
        break

db.setLog("inf", "main", "Stopping!")

db.deleteDevices(service)
db.pollDisable()
db.disconnect()
print "Pantry Daemon Stopped"

