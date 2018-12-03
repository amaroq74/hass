
import time 
import operator
from collections import OrderedDict
import logging
import xbee
import serial
import threading

_LOGGER = logging.getLogger(__name__)

# Temperature vs resistance table
PoolSolarTableRaw = { 185: 150,    208: 145,    234: 140,    264: 135,    300: 130,
                      341: 125,    389: 120,    438: 116,    444: 115,    472: 113,
                      510: 110,    552: 107,    587: 105,    596: 104,    646: 102,
                      679: 100,    701: 99,     761: 96,     787: 95,     827: 93,
                      900: 91,     916: 90,     980: 88,     1071: 85,    1168: 82,
                      1256: 80,    1278: 79,    1400: 77,    1480: 75,    1535: 74,
                      1686: 71,    1752: 70,    1854: 68,    2041: 66,    2083: 65,
                      2251: 63,    2487: 60,    2750: 57,    2985: 55,    3047: 54,
                      3381: 52,    3602: 50,    3757: 49,    4182: 46,    4367: 45,
                      4663: 43,    5209: 41,    5326: 40,    5826: 38,    6530: 35,
                      7331: 32,    8056: 30,    8250: 29,    9298: 27,    10000: 25,
                      10500: 24,   11880: 21,   12500: 20,   13480: 18,   15310: 16,
                      15700: 15,   17440: 13,   19900: 10,   22760: 7,    25400: 5,
                      26100: 5,    30000: 2,    32600: 0,    34560: -1,   39910: -4,
                      42300: -5,   46230: -7,   53640: -9,   55300: -10,  62480: -12,
                      72910: -15,  85350: -18,  97000: -20,  100200: -21, 118000: -23,
                      130300: -25, 139300: -26, 165100: -29, 176800: -30, 196300: -32,
                      234100: -34, 242500: -35, 280100: -37, 336200: -40, 471500: -45,
                      669500: -50 }

PoolSolarTable = OrderedDict(sorted(PoolSolarTableRaw.items(), key=operator.itemgetter(0)))


class ArduinoRelayInput(object):
    """Generic Input Class."""

    def __init__(self, parent, entity, name, inverted):
        self._parent   = parent
        self._entity   = entity
        self._name     = name
        self._inverted = inverted
        self._state    = False

    def locInputState(self, state):
        old = self._state

        if self._inverted:
            if state > 0:
                self._state = False
            else:
                self._state = True
        else:
            if state > 0:
                self._state = True
            else:
                self._state = False

        if self._state != old:
            return True
        else:
            return False


class ArduinoRelayOutput(object):
    """Generic Output Class."""

    def __init__(self, parent, entity, name, timeout):
        self._parent   = parent
        self._entity   = entity
        self._name     = name
        self._timeout  = timeout
        self._state    = False
        self._offTime  = 0

    def locOutputState(self):
        if self._state and self._offTime != 0 and time.time() > self._offTime:
            self._offTime = 0
            self._state   = False

        if self._state:
            return 100
        else:
            return 0

    def setState(self,state):
        self._state = state

        if state and self._timeout != 0:
            self._offTime = time.time() + self._timeout

        self._parent.sendMessage()


class ArduinoRelayPoolSolar(object):
    """Pool Solar Temperature."""

    def __init__(self, parent, entity, name, avgPeriod):
        self._parent    = parent
        self._entity    = entity
        self._name      = name
        self._state     = None
        self._avgPeriod = avgPeriod
        self._avgStart  = time.time()
        self._tempSum   = 0.0
        self._tempCnt   = 0.0

    def locInputState(self,state):
        volt = (float(state) / 1023.0) * 5.0
        res  = (volt * 10000.0) / (5.0 - volt)

        resAbove = None
        resBelow = None

        for resCmp in PoolSolarTable:
            tempVal = PoolSolarTable[resCmp]
            if resCmp > res:
                resAbove  = resCmp
                tempAbove = tempVal
                break
            else:
                resBelow  = resCmp
                tempBelow = tempVal
     
        if resAbove is not None and resBelow is not None:
            slope = (float(tempAbove)-float(tempBelow)) / (float(resAbove) - float(resBelow))
            temp = tempBelow + ((res - resBelow) * slope)
            self._tempSum += temp
            self._tempCnt += 1.0

        if self._tempCnt > 0 and (time.time() - self._avgStart) > self._avgPeriod:
            self._avgStart = time.time()
            self._state    = self._tempSum / self._tempCnt
            self._tempSum  = 0.0
            self._tempCnt  = 0.0
            return True
        else:
            return False


class ArduinoRelayDoorGate(object):
    """Input / Output related to a gate or garage door."""

    def __init__(self, parent, entity, name, inverted):
        self._parent   = parent
        self._entity   = entity
        self._name     = name
        self._inverted = inverted
        self._outState = False
        self._state    = None

    def locInputState(self,state):
        old = self._state

        if self._inverted:
            if state > 0:
                self._state = False
            else:
                self._state = True
        else:
            if state > 0:
                self._state = True
            else:
                self._state = False

        if self._state != old:
            return True
        else:
            return False

    def locOutputState(self):
        if self._outState:
            self._outState = False
            return 50
        else:
            return 0

    def setState(self,state):
        if state != self._state:
            self._outState = True
            self._parent.sendMessage()


class ArduinoRelayBoard(object):
    """Class to handle a the arduino relay board."""

    def __init__(self, name, host, address=None):
        self._sendPeriod  = 10
        self._logPeriod   = 60*5
        self._warnPeriod  = 60*60
        self._name        = name
        self._address     = address
        self._addrData    = None
        self._inputs      = [None for i in range(0,4)]
        self._outputs     = [None for i in range(0,6)]
        self._host        = host
        self._logTime     = 0
        self._sendTime    = 0
        self._warnTime    = time.time()
        self._rxCount     = 0
        self._reset       = 1

        _LOGGER.info("Created board={} address={}".format(name,address))

    def addInput(self,idx,inp):
        self._inputs[idx] = inp

    def addOutput(self,idx,out):
        self._outputs[idx] = out

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name

    def rxData(self, addrData, message):
        """ Receive a message."""
        self._rxCount += 1
        self._addrData = addrData
        words = None

        # Split message into pieces
        if isinstance(message,str):
            words = message.split()
       
        # Make sure length is correct and the marker is present
        if words == None or len(words) != 13 or words[0] != "STATUS" : 
            _LOGGER.warning("Bad message from {} : {}".format(self._name,message))
            return

        # Process results
        inStateNew = [int(i,10) for i in words[1:5]]
        tempValue  = (float(words[5]) / 1023.0) * 500.0
        toCount    = int(words[6])
        newValue   = False
        
        # Rx time
        self._warnTime = time.time()

        # Update inputs
        for i in range(len(self._inputs)):
            if self._inputs[i] != None and self._inputs[i].locInputState(inStateNew[i]):
                newValue = True

        # Log is true
        if newValue or (time.time() - self._logTime) > self._logPeriod:
            self._logTime = time.time()
            _LOGGER.info("Got {} messages from {} : {} Temp={} Timeouts={}".format(self._rxCount, self._name, message, tempValue, toCount))
            self._rxCount = 0

    def sendMessage(self,new=True):
        if self._addrData is None:
            _LOGGER.warning("Skipping send for {}".format(self._name))
            self._sendTime = time.time()
            return

        outs = [out.locOutputState() if out else 0 for out in self._outputs]

        msg = "STATE"
        msg += "".join([(" %i" % v) for v in outs])
        msg += " " + str(self._reset)

        if new or self._reset:
            _LOGGER.info("Sending message to {} : {}".format(self._name,msg))

        self._reset = 0
        self._host.txData(self._addrData,msg)
        self._sendTime = time.time()

    def update(self):
        if (time.time() - self._sendTime) > self._sendPeriod:
            self.sendMessage(False)

        # Make sure we are getting message from device
        if (time.time() - self._warnTime) > self._warnPeriod:
           _LOGGER.error("Have not received a message from {} in over an hour!".format(self._name))
           self._warnTime = time.time()


class ArduinoRelayHost(object):

    def __init__(self,name,device,xbeeEn):
        self._name      = name
        self._byName    = {}
        self._byAddr    = {}
        self._lastRx    = time.time()
        self._runEnable = True
        self._device    = device
        self._xb        = None

        # Serial device
        self._ser = serial.Serial(port = device, baudrate = 9600)

        if xbeeEn:
            self._xb = xbee.ZigBee(self._ser, callback=self.message_received, escaped=True)

        # update thread
        self._thread = threading.Thread(target=self.update_run).start()

        _LOGGER.info("Created host={} on device={} xbee={}".format(self._name,self._device,xbeeEn))

    def addNode(self, node):
        self._byName[node.name] = node

        if self._xb is not None:
            self._byAddr[node.address] = node

    def txData(self,addr,msg):
        try:
            if self._xb:
                self._xb.tx(dest_addr=addr['addr'],dest_addr_long=addr['addr_long'],data=msg)
            else:
                self._ser.write((msg + "\n").encode('utf-8'))
        except:
            _LOGGER.error("Transmit exception")

    def stop(self):
        self._runEnable = False
        if self._xb is not None:
            self._xb.halt()

    def update_run(self):
        while self._runEnable:

            if self._xb is not None:
                time.sleep(1)
            elif self._ser.inWaiting() > 0:
                self._lastRx = time.time()
                d = self._ser.readline().decode('utf-8')

                for k,v in self._byName.items():
                    v.rxData("",d)
            else:
               time.sleep(.1)

            for k,v in self._byName.items():
                v.update()

            if (time.time() - self._lastRx) > 900:
                _LOGGER.error("Have not received a message in 15 minutes!")
                self._lastRx = time.time()

    # XBEE callback
    def message_received(self, data):
        if not 'source_addr_long' in data:
            return

        self._lastRx = time.time()

        try:
            src64 = ".".join(["%02X" % b for b in data['source_addr_long']])
            addr = {'addr_long':data['source_addr_long'],'addr':data['source_addr']}

            if 'rf_data' in data and src64 in self._byAddr:
                self._byAddr[src64].rxData(addr,data['rf_data'].decode('utf-8'))
            else:
                _LOGGER.warning("Dropping message from unknown source: {}".format(src64))

        except Exception as err:
            _LOGGER.error("Callback exception in xbee_rx: {}".format(err))
        except :
            _LOGGER.error("Unknown exception in xbee_rx")

