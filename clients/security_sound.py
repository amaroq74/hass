#!/usr/bin/env python2

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

# Libraries
import time

from websocket import create_connection

# Constants
service = "sound_gen"

# Setup
os.system("amixer set PCM 100 -c 0")
soundDir = '/amaroq/hass/sounds'

sounds = { "binary_sensor.car_gate"  : "doorbell.wav",
           "binary_sensor.ped_gate"  : "doorbell.wav",
           "binary_sensor.gate_bell" : "front_door_and_gate_bell.wav",
           "binary_sensor.door_bell" : "front_door_and_gate_bell.wav" }

DcSensors = [ 'binary_sensor.car_gate', 'binary_sensor.ped_gate', 'binary_sensor.garage_door', 
              'binary_sensor.pbath_door', 'binary_sensor.kitchen_door', 'binary_sensor.office_door',
              'binary_sensor.chicken_gate', 'binary_sensor.ivy_gate', 'binary_sensor.garbage_gate' ]

DcSound = "short_beep.wav"

last   = {}
states = {}

for key in sounds:
    last[key] = 0
    states[key] = 'off'

for key in DcSensors:
    last[key] = 0
    states[key] = 'off'

last['switch.dcare_arm'] = 0
states['switch.dcare_arm'] = 'off'

# Mysql
db = hass_mysql.Mysql(service)

lastDc = time.time()

# Daycare Alarm
def testDayCare():
    global db
    global lastDc
    global states
    global last  

    now = time.time()
    if ( (now - lastDc) > 5.0 ):
        lastDc = now

        if states['switch.dcare_arm'] == 'on':

            count = 0
            for sen in DcSensors:
                if states[sen] == 'on':
                    count += 1

            if count != 0:
                cmd = "aplay " + soundDir + "/" + DcSound
                #cmd = "aplay -D hw:0 " + soundDir + "/" + DcSound
                os.system(cmd)

# Update
def soundCb(e):
    global db
    global sounds
    global states
    global last  

    key = e['entity_id']

    if 'climate' in key: 
        val = e['attributes']['temperature']
    else:
        val = e['state']

    if key in last:
        ldiff = time.time() - last[key]
        old   = states[key]
    else:
        ldiff = 0
        old   = val

    states[key] = val
    last[key]   = time.time()

    if ldiff > 60 and val != old and val == "on":
        if key in sounds:
            cmd = "aplay " + soundDir + "/" + sounds[sensor]
            #cmd = "aplay -D hw:0 " + soundDir + "/" + sounds[sensor]
            os.system(cmd)

        elif armDc == 1 and sensor in DcSensors:
            cmd = "aplay " + soundDir + "/" + DcSound
            #cmd = "aplay -D hw:0 " + soundDir + "/" + DcSound
            os.system(cmd)

def swRead(self,ws):
    try:
        message = ws.recv()

        if message is None:
            return False
        d = yaml.load(message)

        if d['type'] == 'result' and d['success']:
            if d['result'] is not None:
                for e in d['result']:
                    soundCb(e)

        elif d['type'] == 'event':
            e = d['event']['data']['new_state'] 
            soundCb(e)
    except:
        return False

    return True

while True:
    ws = create_connection('ws://localhost:8123/api/websocket',timeout=60*10)

    ws.send(json.dumps({'type': 'auth', 'api_password': 'TEST1234'}))
    swResp(ws)

    ws.send(json.dumps({'id': 1, 'type': 'get_states'}))
    swResp(ws)

    ws.send(json.dumps({'id': 2, 'type': 'subscribe_events', 'event_type': 'state_changed'}))
    while self._runEnable:
        if not swResp(ws):
            break
        TestDayCare()

