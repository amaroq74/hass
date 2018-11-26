
import time 
import operator
from collections import OrderedDict

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

    def __init__(self,name,period,inverted):
        self._inName     = name
        self._inStatus   = 0
        self._inTime     = 0
        self._inPeriod   = period
        self._inInverted = inverted
        self._db         = None

    def setDb(self,db):
        self._db = db

    def setStatus(self,status):
        newStatus = (status if (not self._inInverted) else (1 if status == 0 else 0))

        if self._inStatus != newStatus or (time.time() - self._inTime) > self._inPeriod:
            self._inStatus = newStatus
            self._inTime   = time.time()
            return True
        return False

class ArduinoRelayOutput(object):
    """Generic Output Class."""

    def __init__(self,category,name,type,hidden,timeout):
        self._outParent   = None
        self._outCategory = category
        self._outName     = name
        self._outType     = type
        self._outHidden   = hidden
        self._outTimeout  = timeout
        self._outLevel    = 0
        self._outOffTime  = 0
        self._db          = None

    def setupOut(self,service,parent,db):
        self._outParent = parent
        self._db = db
        db.insertDevice(service,self._outCategory,self._outName,self._outType,self._outHidden)
        return {self._outName:self}

    def getLevel(self):
        if self._outLevel > 0 and self._outOffTime != 0 and time.time() > self._outOffTime:
            self._db.setLog('wrn', 'setLevel', "Turning off " + self._outName + " after timeout!")
            self._outLevel   = 0
            self._outOffTime = 0
            self._db.statusDevice(self._outName,self._outLevel)

        # Toggle
        if self._outLevel == 50:
            self._outLevel = 0
            return 50

        return self._outLevel

    def setLevel(self,level):
        self._outLevel = level
        self._outOffTime = time.time() + self._outTimeout
        self._db.setLog('inf', 'setLevel', "Setting " + self._outName + " to " + str(level))
        self._db.statusDevice(self._outName,level)
        self._outParent.sendMessage(True)

class ArduinoRelayPoolSolar(ArduinoRelayInput):
    """Pool Solar Temperature."""

    def __init__(self,name,period):
        ArduinoRelayInput.__init__(self,name,period,False)
        self._tempSum = 0.0
        self._tempCnt = 0.0

    def setStatus(self,status):
        self._inStatus = status

        volt = (float(self._inStatus) / 1023.0) * 5.0
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
     
        if resAbove and resBelow :
            slope = (float(tempAbove)-float(tempBelow)) / (float(resAbove) - float(resBelow))
            temp = tempBelow + ((res - resBelow) * slope)
            self._tempSum += temp
            self._tempCnt += 1.0

        if self._tempCnt > 0 and (time.time() - self._inTime) > self._inPeriod:
            self._inTime = time.time()
            temp = self._tempSum / self._tempCnt
            self._db.setSensor(self._inName,'temp',temp,'C')
            self._tempSum = 0.0
            self._tempCnt = 0.0

        # Don't trigger log
        return False

class ArduinoRelaySecurity(ArduinoRelayInput):
    """Security Input."""

    def __init__(self,name,period,inverted):
        ArduinoRelayInput.__init__(self,name,period,inverted)

    def setStatus(self,status):
        if ArduinoRelayInput.setStatus(self,status):
            event = 'normal' if self._inStatus == 0 else 'alert'
            self._db.setSecurity(self._inName, event )
            return True
        return False

class ArduinoRelayButton(ArduinoRelayInput):
    """Button Input."""

    def __init__(self,name,period,inverted):
        ArduinoRelayInput.__init__(self,name,period,inverted)

    def setStatus(self,status):
        if ArduinoRelayInput.setStatus(self,status):
            if self._inStatus == 1:
               self._db.setDevice(self._inName, 50)
               return True
        return False

class ArduinoRelayDoorGate(ArduinoRelayInput,ArduinoRelayOutput):
    """Input / Output related to a gate or garage door."""

    def __init__(self,category,name,period,inverted):
        ArduinoRelayInput.__init__(self,name,period,inverted)
        ArduinoRelayOutput.__init__(self,category,name,"OpenCloseToggle",False,0)

    def setParent(self,parent):
        ArduinoRelayInput.setParent(parent)
        ArduinoRelayOutput.setParent(parent)

    def setStatus(self,status):
        if ArduinoRelayInput.setStatus(self,status):
            event = 'normal' if self._inStatus == 0 else 'alert'
            self._db.setSecurity(self._inName, event )
            level = 0 if self._inStatus == 0 else 100
            self._db.statusDevice(self._inName,level)
            return True
        return False

    def setLevel(self,level):
        if level == 100 and self._inStatus == 0:
            self._db.setLog('inf', 'setLevel', "Opening " + self._outName)
            self._outLevel = 50
        elif level == 0 and self._inStatus != 0:
            self._db.setLog('inf', 'setLevel', "Closing " + self._outName)
            self._outLevel = 50
        elif level == 50:
            self._db.setLog('inf', 'setLevel', "Toggling " + self._outName)
            self._outLevel = 50
        else:
            self._outLevel = 0

        self._outParent.sendMessage(True)

class ArduinoRelayBoard(object):
    """Class to handle a the arduino relay board."""

    def __init__(self, name, logPeriod, sendPeriod):
        """ Create ArduinoRelay class.

        Arguments:
        name: Name of the relay board.
        """
        self._name        = name
        self._address     = None
        self._inputs      = [None for i in range(0,4)]
        self._outputs     = [None for i in range(0,6)]
        self._db          = None
        self._txFunction  = None
        self._rawTemp     = 0
        self._toCount     = 0
        self._logPeriod   = logPeriod
        self._logTime     = 0
        self._sendPeriod  = sendPeriod
        self._sendTime    = 0
        self._warnTime    = time.time()
        self._rxCount     = 0
        self._reset       = 1

    def addInput(self,idx,inp):
        self._inputs[idx] = inp

    def addOutput(self,idx,out):
        self._outputs[idx] = out

    def setupNode(self,service,db,txFunction):
        self._db = db
        self._txFunction = txFunction
        ret = {}

        for inp in self._inputs:
            if inp != None: inp.setDb(db)

        for out in self._outputs:
            if out != None: 
                ret.update(out.setupOut(service,self,db))

        return ret

    def rxData(self, addr, message):
        """ Receive a message."""

        self._rxCount += 1
        self._address = addr
        log = False
        words = None

        # Split message into pieces
        if isinstance(message,basestring):
            words = message.split()
       
        # Make sure length is correct and the marker is present
        if words == None or len(words) != 13 or words[0] != "STATUS" : 
            self._db.setLog('err', 'rxData', "Bad message from " + self._name + ": " + str(message))
            return

        # Process results
        inStateNew   = [int(i,10) for i in words[1:5]]
        tempValueNew = int(words[5],10)
        toCountNew   = int(words[6],10)
        
        # Rx time
        self._warnTime = time.time()

        # Update inputs
        i = 0
        for inp in self._inputs:
            if inp != None and inp.setStatus(inStateNew[i]):
                log = True
            i += 1

        # Check log time
        if (time.time() - self._logTime) > self._logPeriod:
            temp = (float(tempValueNew) / 1023.0) * 500.0
            #self._db.setSensor(self._name,'temp',temp,'C')
            #self._db.setSensor(self._name,'timeout',toCountNew,'')
            log = True

        # Log is true
        if log:
            self._logTime = time.time()
            msg = "Got " + str(self._rxCount) + " messages from " + self._name + ": " + str(message)
            self._db.setLog('inf', 'rxData', msg)
            self._rxCount = 0

    def sendMessage(self,new):
        if self._address == None:
            self._db.setLog('wrn', 'sendMessage', "Skipping send for " + self._name)
            self._sendTime = time.time()
            return

        outs = [out.getLevel() if out else 0 for out in self._outputs]

        msg = "STATE"
        msg += "".join([(" %i" % v) for v in outs])
        msg += " " + str(self._reset)

        if new or self._reset:
            self._db.setLog('inf', 'sendMessage', "Sending message to " + self._name + ": " + str(msg))

        self._reset = 0
        self._txFunction(self._address,msg)
        self._sendTime = time.time()

    def update(self):
        if (time.time() - self._sendTime) > self._sendPeriod:
            self.sendMessage(False)

        # Make sure we are getting message from device
        if (time.time() - self._warnTime) > 60*60:
           self._db.setLog('err', 'update', "Have not received a message from " + self._name + " in over an hour!")
           self._warnTime = time.time()

