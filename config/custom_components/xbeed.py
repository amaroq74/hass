#!/usr/bin/env python2
import serial

# Add relative path
import sys,os
sys.path.append(os.path.dirname(__file__) + "/../pylib")

# Libraries
import time
import xbee
from amaroq_home import mysql
from amaroq_home import arduino_relay
from amaroq_home import xbee_node
from amaroq_home import usb_paths

# Constants
usbPath = "2-1.4.3:1.0"
service = "xbeed"

# Variables
error = False

# Timeout
lastRx = time.time()

# Boards
nodes = {}

#############################
# Front Sprinklers
#############################
node = arduino_relay.ArduinoRelayBoard("Front_Sprinklers", 300, 10)

# Outputs
node.addOutput(0, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Front_Lawn_1", "OnOff", False, 60*60))
node.addOutput(1, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Front_Lawn_2", "OnOff", False, 60*60))
node.addOutput(2, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Front_Lawn_3", "OnOff", False, 60*60))
node.addOutput(3, arduino_relay.ArduinoRelayOutput  ("Irrigation", "West_Trees",   "OnOff", False, 60*60))

# Linked Input/Output
temp = arduino_relay.ArduinoRelayDoorGate("Security", "Car_Gate", 300, True)
node.addOutput(5, temp)
node.addInput(0, temp)

# Add to dictionary
nodes['00.13.A2.00.40.8B.2D.43'] = node

#############################
# Garage Controller
#############################
node = arduino_relay.ArduinoRelayBoard("Garage_Control", 300, 10)

# Outputs
node.addOutput(0, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Rear_Patio_1",  "OnOff", False, 60*60))
node.addOutput(1, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Rear_Patio_2",  "OnOff", False, 60*60))
node.addOutput(2, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Rear_Patio_3",  "OnOff", False, 60*60))
node.addOutput(3, arduino_relay.ArduinoRelayOutput  ("Irrigation", "Front_Flowers", "OnOff", False, 60*60))

# Linked Input/Output
temp = arduino_relay.ArduinoRelayDoorGate("Security", "Garage_Door", 300, False)
node.addOutput(5, temp)
node.addInput(0, temp)

# Add to dictionary
nodes['00.13.A2.00.40.69.4E.CD'] = node

#############################
# East Sprinklers
#############################
node = arduino_relay.ArduinoRelayBoard("East_Sprinklers", 300, 10)

# Outputs
node.addOutput(0, arduino_relay.ArduinoRelayOutput  ("Irrigation", "East_Lawn_1", "OnOff", False, 60*60))
node.addOutput(1, arduino_relay.ArduinoRelayOutput  ("Irrigation", "East_Lawn_2", "OnOff", False, 60*60))
node.addOutput(3, arduino_relay.ArduinoRelayOutput  ("Irrigation", "East_Lemon",  "OnOff", False, 60*60))

# Add to dictionary
nodes['00.13.A2.00.40.79.C1.A8'] = node

#############################
# Pool Control
#############################
node = arduino_relay.ArduinoRelayBoard("Pool_Control", 300, 10)

# Outputs
node.addOutput(0, arduino_relay.ArduinoRelayOutput  ("Pool", "Pool_Main",  "OnOff", False, 60*60*12))
node.addOutput(1, arduino_relay.ArduinoRelayOutput  ("Pool", "Pool_Sweep", "OnOff", False, 60*60*12))
node.addOutput(2, arduino_relay.ArduinoRelayOutput  ("Pool", "Pool_Heat",  "OnOff", False, 60*60*12))

# Inputs
node.addInput(2, arduino_relay.ArduinoRelayPoolSolar ("Pool_Solar_In",  60))
node.addInput(3, arduino_relay.ArduinoRelayPoolSolar ("Pool_Solar_Out", 60))

# Add to dictionary
nodes['00.13.A2.00.40.6F.DC.78'] = node

#############################
# Gate Sensor
#############################
#node = xbee_node.XbeeNode("Ped_Gate",300)
#node.addDigitalInput(4,xbee_node.XbeeNodeSecurity("Ped_Gate",300,True))
#nodes['00.13.A2.00.40.E8.35.3A'] = node

# Mysql
db = mysql.Mysql(service)
db.setLog("inf", "main", "Starting!")

devPath = usb_paths.findUsbDevice(usbPath)
db.setLog("inf", "main", "Using device " + devPath)

# XBEE callback
def message_received(data):
    global nodes
    global db
    global lastRx

    lastRx = time.time()

    if not data.has_key('source_addr_long'):
        #print "Unkown: " + str(data)
        return

    try:
        src64 = ".".join(["%02X" % ord(b) for b in data['source_addr_long']])
        addr = {'addr_long':data['source_addr_long'],'addr':data['source_addr']}
        got = False

        if nodes.has_key(src64):
            if data.has_key('rf_data'): 
                nodes[src64].rxData(addr,data['rf_data'])
                got = True
            elif data.has_key('samples'): 
                nodes[src64].rxData(addr,data['samples'])
                got = True
        if not got:
            #print "Uknown: " + src64 + ": " + str(data)
            return
    except Exception,err:
        db.setLog("err","xbee_rx","Callback exception: " + str(err))
        print "Callback exception: " + str(err)
    except :
        db.setLog("err","xbee_rx","Unknown exception")
        print "Unknown exception"


# Serial device
ser = serial.Serial(port = devPath, baudrate = 9600)
xb = xbee.ZigBee(ser, callback=message_received, escaped=True)


# Transmit function
def xbTransmit(addr,msg):
    global xb
    xb.tx(dest_addr=addr['addr'],dest_addr_long=addr['addr_long'],data=msg)


# Setup and generate device list
db.deleteDevices(service)
devList = {}

for node in nodes:
    devList.update(nodes[node].setupNode(service,db,xbTransmit))

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

print "Xbee Daemon Starting"

# Setup network
db.pollEnable(0.1)

# Process received data and update devices
while not error:
    try:
        time.sleep(1)
        for node in nodes:
            nodes[node].update()

        if (time.time() - lastRx) > 900:
           db.setLog('err','main',"Its been 15 minutes since last Rx!")
           error = True

    except KeyboardInterrupt:
        break

db.setLog("inf", "main", "Stopping!")

xb.halt()
db.deleteDevices(service)
db.pollDisable()
db.disconnect()
print "Xbee Daemon Stopped"

