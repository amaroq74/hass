#!/usr/bin/env python3

WiconDir = "/amaroq/hass/clients/wicons"

ferr = open("/amaroq/home/media-family/panel.log","a")
#ferr = None

def eprint(*args, **kwargs):
    global ferr
    print(*args, file=ferr, **kwargs)

    if ferr is not None:
        ferr.flush()

import datetime
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

eprint("------- Starting {} --------".format(now))

# Add relative path
import sys,datetime
sys.path.append('/amaroq/hass/pylib')

import time, pytz
import hass_mysql as mysql
import hass_secrets as secrets
import weather_convert as convert

from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWebKit  import *
import PyQt5

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import urllib.request
import xml.etree.ElementTree as ET

from subprocess import call

import json
import yaml
from websocket import create_connection

import threading
import zmq
import base64
import os


# Display functions
def disp_temp(val, box):
    box.setText("%2.2F F" % ( float(val) ))

def disp_humid(val, box):
    box.setText("%i %%" % ( float(val) ))

def disp_winddir(val, box):
    box.setText("{}".format(val))

def disp_winddeg(val, box):
    box.setText("%i Deg" % (float(val)))

def disp_speed(val, box):
    box.setText("%2.2F MPH" % ( float(val) ))

def disp_rain(val, box):
    box.setText("%2.2F IN" % ( float(val) ))

def disp_pressure(val, box):
    box.setText("%2.2F INHG" % ( float(val) ))

def disp_power(val, box):
    box.setText("%2.2F KW" % ( float(val) ))

def disp_door(val, box):
    box.setText('Closed' if val == 'off' else 'Open')

def disp_text(val,box):
    box.setText(val)

# Status List
StatusList = [ {'label':'Out Temp',     'key':'sensor.outdoor_temperature',  'conv':disp_temp,      'box':None },
               {'label':'Out Humid',    'key':'sensor.outdoor_humidity',     'conv':disp_humid,     'box':None },
               {'label':'Wind Dir',     'key':'sensor.wind_compass',         'conv':disp_winddir,   'box':None },
               {'label':'Wind Avg',     'key':'sensor.wind_average',         'conv':disp_speed,     'box':None },
               {'label':'Wind Gust',    'key':'sensor.wind_gust',            'conv':disp_speed,     'box':None },
               {'label':'Rain Hour',    'key':'sensor.rain_hour',            'conv':disp_rain,      'box':None },
               {'label':'Rain Today',   'key':'sensor.rain_day',             'conv':disp_rain,      'box':None },
               {'label':'Barometer',    'key':'sensor.indoor_pressure',      'conv':disp_pressure,  'box':None },
               {'label':'House Temp',   'key':'sensor.house_temperature',    'conv':disp_temp,      'box':None },
               {'label':'Thermostat',   'key':'climate.house',               'conv':disp_temp,      'box':None },
               {'label':'Family Temp',  'key':'sensor.indoor_temperature',   'conv':disp_temp,      'box':None },
               {'label':'Family Humid', 'key':'sensor.indoor_humidity',      'conv':disp_humid,     'box':None },
               {'label':'Master Temp',  'key':'sensor.master_temperature',   'conv':disp_temp,      'box':None },
               {'label':'Master Humid', 'key':'sensor.master_humidity',      'conv':disp_humid,     'box':None },
               {'label':'BedR Temp',    'key':'sensor.bedr_temperature',     'conv':disp_temp,      'box':None },
               {'label':'BedR Humid',   'key':'sensor.bedr_humidity',        'conv':disp_humid,     'box':None },
               {'label':'BedTA Temp',   'key':'sensor.bedta_temperature',    'conv':disp_temp,      'box':None },
               {'label':'BedTA Humid',  'key':'sensor.bedta_humidity',       'conv':disp_humid,     'box':None },
               {'label':'Power Use',    'key':'sensor.smartmeter_rate',      'conv':disp_power,     'box':None },
               {'label':'Garage Temp',  'key':'sensor.garage_temperature',   'conv':disp_temp,      'box':None },
               {'label':'Garage Humid', 'key':'sensor.garage_humidity',      'conv':disp_humid,     'box':None },
               {'label':'Shed Temp',    'key':'sensor.shed_temperature',     'conv':disp_temp,      'box':None },
               {'label':'Shed Humid',   'key':'sensor.shed_humidity',        'conv':disp_humid,     'box':None },
               {'label':'Camper Temp',  'key':'sensor.camper_temperature',   'conv':disp_temp,      'box':None },
               {'label':'Chicken Temp', 'key':'sensor.chickens_temperature', 'conv':disp_temp,      'box':None },
               {'label':'Pool Temp',    'key':'sensor.pool_temperature',     'conv':disp_temp,      'box':None },
               {'label':None,           'key':'sensor.time',                 'conv':disp_text,      'box':None },
               {'label':None,           'key':'sensor.date',                 'conv':disp_text,      'box':None } ]

DoorList = [{'label':'Ped<br/>Gate',      'key':'binary_sensor.ped_gate',      'color':Qt.red,    'box':None },
            {'label':'Car<br/>Gate',      'key':'switch.car_gate',             'color':Qt.red,    'box':None },
            {'label':'Ivy<br/>Gate',      'key':'binary_sensor.ivy_gate',      'color':Qt.red,    'box':None },
            {'label':'Garbage<br/>Gate',  'key':'binary_sensor.garbage_gate',  'color':Qt.red,    'box':None },
            {'label':'Patio<br/>Gate',    'key':'binary_sensor.patio_gate',    'color':Qt.red,    'box':None },
            {'label':'Garage<br/>Door',   'key':'switch.garage_door',          'color':Qt.red,    'box':None },
            {'label':'Office<br/>Door',   'key':'binary_sensor.office_door',   'color':Qt.red,    'box':None },
            {'label':'Bath<br/>Door',     'key':'binary_sensor.pbath_door',    'color':Qt.red,    'box':None },
            {'label':'Kitchen<br/>Door',  'key':'binary_sensor.kitchen_door',  'color':Qt.red,    'box':None },
            {'label':'Chicken<br/>Gate',  'key':'binary_sensor.chickens_gate', 'color':Qt.yellow, 'box':None },
            {'label':'Shed<br/>Door',     'key':'binary_sensor.shed_door',     'color':Qt.yellow, 'box':None },
            {'label':'Garage<br/>R Door', 'key':'binary_sensor.garage_rdoor',  'color':Qt.yellow, 'box':None }]

class WindChart(QWidget):
    def __init__(self, db, parent=None):
        super(WindChart, self).__init__(parent)

        self.db = db
        self.fig = Figure((1.0, 1.0),100)
        self.canvas = FigureCanvas(self.fig)

        self.canvas.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.axes = self.fig.add_subplot(111)
        self.axes.tick_params(axis='both', which='major', labelsize='x-small')
        self.axes.tick_params(axis='both', which='minor', labelsize='x-small')

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)

        self.setLayout(vbox)
        self.plotUpdate()

    def plotUpdate (self):

        windAvg = self.db.getSensorArrayHours('Wind','speed_average',6)
        windGust = self.db.getSensorArrayHours('Wind','speed',6)

        is_dst = time.daylight and time.localtime().tm_isdst > 0
        utc_offset = - (time.altzone if is_dst else time.timezone)

        dataA_X = matplotlib.dates.epoch2num([(float(val['utime']) + float(utc_offset)) for val in windGust])
        dataB_X = matplotlib.dates.epoch2num([(float(val['utime']) + float(utc_offset)) for val in windAvg])
        dataA_Y = [convert.speedMpsToMph(val['current']) for val in windGust]
        dataB_Y = [convert.speedMpsToMph(val['current']) for val in windAvg]

        self.axes.clear()
        self.axes.grid(True)

        self.axes.plot_date(dataA_X, dataA_Y, 'r-', label='Gust')
        self.axes.plot_date(dataB_X, dataB_Y, 'b-', label='Avg')

        self.axes.set_ylabel('Wind MPH',fontsize='x-small')
        #self.axes.set_xlabel('Wind Speed',fontsize='x-small')
        self.axes.set_title("Wind Speed: Red=Gust, Blue=Average", fontsize='x-small')
        self.axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

        #self.axes.set_title("Wind Speed",fontsize='x-small')
        #self.axes.legend(loc='upper left',fontsize='x-small')
        #self.fig.tight_layout()
        self.canvas.draw()
        QTimer.singleShot(60 * 1000, self.plotUpdate) # 60 seconds

class TempChart(QWidget):
    def __init__(self, db, parent=None):
        super(TempChart, self).__init__(parent)

        self.db = db
        self.fig = Figure((1.0, 1.0),100)
        self.canvas = FigureCanvas(self.fig)

        self.canvas.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.axes = self.fig.add_subplot(111)
        self.axes.tick_params(axis='both', which='major', labelsize='x-small')
        self.axes.tick_params(axis='both', which='minor', labelsize='x-small')

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)

        self.setLayout(vbox)
        self.plotUpdate()

    def plotUpdate (self):

        inTemp = self.db.getSensorArrayHours('House','temp',6)
        outTemp = self.db.getSensorArrayHours('Outdoor','temp',6)

        is_dst = time.daylight and time.localtime().tm_isdst > 0
        utc_offset = - (time.altzone if is_dst else time.timezone)

        dataA_X = matplotlib.dates.epoch2num([(float(val['utime']) + float(utc_offset)) for val in inTemp])
        dataB_X = matplotlib.dates.epoch2num([(float(val['utime']) + float(utc_offset)) for val in outTemp])
        dataA_Y = [convert.tempCelToFar(val['current']) for val in inTemp]
        dataB_Y = [convert.tempCelToFar(val['current']) for val in outTemp]

        self.axes.clear()
        self.axes.grid(True)

        self.axes.plot_date(dataA_X, dataA_Y, 'r-', label='In')
        self.axes.plot_date(dataB_X, dataB_Y, 'b-', label='Out')

        self.axes.set_ylabel('Temp F',fontsize='x-small')
        #self.axes.set_xlabel('Wind Speed',fontsize='x-small')
        self.axes.set_title("Temperature: Red=House, Blue=Outside", fontsize='x-small')
        self.axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

        #self.axes.set_title("Wind Speed",fontsize='x-small')
        #self.axes.legend(loc='upper left',fontsize='x-small')
        #self.fig.tight_layout()
        self.canvas.draw()
        QTimer.singleShot(60 * 1000, self.plotUpdate) # 60 seconds

class DoorWindow(QWidget):
    def __init__(self, db, parent=None):
        super(DoorWindow, self).__init__(parent)

        self.db = db

        gl = QGridLayout()
        gl.setHorizontalSpacing(0)
        gl.setVerticalSpacing(0)
        idx = 0

        lfont = QFont()
        lfont.setPointSize(13)
        lfont.setBold(True)

        for sen in DoorList:
            sen['box'] = QLabel(sen['label'])

            sen['box'].setFont(lfont)
            sen['box'].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            sen['box'].setMinimumSize( QSize(80, 50) )
            sen['box'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding);

            p = QPalette()
            p.setColor(QPalette.Window,Qt.green)
            p.setColor(QPalette.WindowText,Qt.black)

            sen['box'].setAutoFillBackground(True)
            sen['box'].setPalette(p)

            gl.addWidget(sen['box'],idx/3,(idx%3)*2,1,2,Qt.AlignCenter | Qt.AlignVCenter)
            idx += 1

        self.setLayout(gl)

    def stateUpdate (self, key, value ):
        for sen in DoorList:
            if sen['key'] == key:

                p = QPalette()
                p.setColor(QPalette.WindowText,Qt.black)

                if value == 'on':
                    p.setColor(QPalette.Window,sen['color'])
                else:
                    p.setColor(QPalette.Window,Qt.green)
                sen['box'].setPalette(p)

class StatusWindow(QWidget):
    def __init__(self, db, parent=None):
        super(StatusWindow, self).__init__(parent)

        self.db = db

        gl = QGridLayout()
        idx = 0

        lfont = QFont()
        lfont.setPointSize(14)
        lfont.setBold(True)
        vfont = QFont()
        vfont.setPointSize(12)
        vfont.setBold(True)

        for sen in StatusList:
            if sen['label'] is not None:
                lab = QLabel(sen['label'] + ':')
                lab.setFont(lfont)
                gl.addWidget(lab,idx,0,1,1,Qt.AlignRight)
                sen['box'] = QLabel('')
                sen['box'].setFont(vfont)
                gl.addWidget(sen['box'],idx,1,1,1,Qt.AlignLeft)
            else:
                sen['box'] = QLabel('')
                sen['box'].setFont(lfont)
                gl.addWidget(sen['box'],idx,0,1,2,Qt.AlignCenter)

            idx += 1

        self.setLayout(gl)

    def stateUpdate (self, key, value ):
        for sen in StatusList:
            if sen['key'] == key and value != 'unknown' and value is not None and value != 'unavailable':
                sen['conv'](value,sen['box'])


class ForecastWindow(QWidget):
    def __init__(self, db, parent=None):
        super(ForecastWindow, self).__init__(parent)

        self.db = db

        nfont = QFont()
        nfont.setPointSize(10)
        nfont.setBold(True)
        ifont = QFont()
        ifont.setPointSize(8)
        ifont.setBold(True)

        self.dayName   = [None for i in range(0,10)]
        self.dayLabel  = [None for i in range(0,10)]
        self.dayInfo   = [None for i in range(0,10)]
        self.dayPixmap = [None for i in range(0,10)]

        gl = QGridLayout()

        for idx in range(10):
            self.dayName[idx] = QLabel()
            self.dayName[idx].setAlignment(Qt.AlignCenter)
            self.dayName[idx].setFont(nfont)
            self.dayName[idx].setFixedSize(130,20)
            self.dayName[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            gl.addWidget(self.dayName[idx],0,idx,1,1,Qt.AlignCenter)

            self.dayLabel[idx] = QLabel()
            self.dayLabel[idx].setFixedSize(50,50)
            self.dayLabel[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            gl.addWidget(self.dayLabel[idx],1,idx,1,1,Qt.AlignCenter)

            self.dayInfo[idx] = QLabel()
            self.dayInfo[idx].setAlignment(Qt.AlignCenter)
            self.dayInfo[idx].setFont(ifont)
            self.dayInfo[idx].setFixedSize(130,80)
            self.dayInfo[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            self.dayInfo[idx].setWordWrap(True);
            gl.addWidget(self.dayInfo[idx],2,idx,1,1,Qt.AlignCenter)

            self.dayPixmap[idx] = QPixmap()

        gl.setHorizontalSpacing(0)
        gl.setSpacing(0)
        gl.setContentsMargins(0,0,0,0)

        self.setLayout(gl)
        self.refreshForecast()

    def refreshForecast(self):
        try:

            # Get the forecast
            url = "https://api.weather.com/v3/wx/forecast/daily/5day?postalKey=94062:US&units=e&language=en-US&format=json&apiKey=" + secrets.wunder_api

            with urllib.request.urlopen(url) as fh:
                ures = fh.read().rstrip()

            res = json.loads(ures)

            for i,day in enumerate(res['daypart'][0]['daypartName']):
                if day is not None:
                    cond = res['daypart'][0]['wxPhraseShort'][i]
                    icon = res['daypart'][0]['iconCode'][i]
                    ipath = os.path.join(WiconDir, f"{icon:02d}.png")
                else:
                    cond = ""
                    ipath = os.path.join(WiconDir, "na.png")

                if i < 10:
                    self.dayName[i].setText(day)
                    self.dayInfo[i].setText(cond)
                    self.dayPixmap[i].load(ipath)
                    self.dayLabel[i].setPixmap(self.dayPixmap[i].scaled(50,50,Qt.KeepAspectRatio))
                    self.dayLabel[i].update()


        except Exception as e:
            eprint("go forecast exception: {}".format(e))

        QTimer.singleShot(10 * 60 * 1000,self.refreshForecast) # 15 minutes


class CamImage(QWidget):

    imageUpdate = pyqtSignal(QPixmap)

    def __init__(self, width, height, addr, parent=None):
        super(CamImage, self).__init__(parent)

        self.height=height
        self.width=width

        self.addr = addr
        self.time = time.time()
        self.cnt = 0

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.label = QLabel()
        self.label.setFixedSize(width,height)
        self.label.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)

        self.imageUpdate.connect(self.label.setPixmap)

        vb.addWidget(self.label)

        self.time = time.time()
        self.thread=threading.Thread(target=self.refresh)
        self.thread.start()

    def refresh(self):
        count = 0

        while True:
            eprint("Entering outer loop")
            try:
                eprint("Opening camera link")
                count = 0
                ctx = zmq.Context()
                sub = ctx.socket(zmq.SUB)
                sub.connect(self.addr)
                sub.setsockopt(zmq.SUBSCRIBE,''.encode('utf-8'))
                sub.setsockopt(zmq.RCVTIMEO, 2000)
                self.time = time.time()

                eprint("Entering inner loop")
                try:
                    while ((time.time() - self.time) < 300):
                        img = QPixmap.fromImage(QImage.fromData(base64.b64decode(sub.recv())))
                        self.imageUpdate.emit(img)
                        count += 1
                    eprint("Restarting camera after 5 min. Count={}".format(count))
                except Exception as e:
                    eprint("got inner camera exception: {}".format(e))
                eprint("Exiting inner loop")

                eprint("Closing camera link. Count={}".format(count))
                sub.close(linger=0)
                ctx.destroy(linger=0)
            except Exception as e:
                eprint("got outer camera exception: {}".format(e))
            eprint("Exiting outer loop")
            time.sleep(1)

class HassListener(QThread):

    stateUpdate = pyqtSignal(str,str)

    def __init__(self, parent=None):
        QThread.__init__(self,parent)

        self._runEnable = True
        self.start()

    def halt(self):
        self._runEnable = False

    def _newValue(self,e):
        key = e['entity_id']
        #eprint("{} = {}".format(key,e))

        if 'climate.' in key:
            val = e['attributes']['temperature']
        else:
            val = e['state']

        self.stateUpdate.emit(key,str(val))

    def _read(self,ws):
        try:
            message = ws.recv()

            if message is None:
                return False
            d = yaml.load(message)

            if d['type'] == 'result' and d['success']:
                if d['result'] is not None:
                    for e in d['result']:
                        self._newValue(e)

            elif d['type'] == 'event':
                e = d['event']['data']['new_state']
                self._newValue(e)
        except Exception as emsg:
            eprint("Got Read Exception: {}".format(emsg))
            return False

        return True

    def run(self):

        while self._runEnable:
            try:
                ws = create_connection('ws://aliska.amaroq.net:8123/api/websocket',timeout=60*10)

                ws.send(json.dumps({'type': 'auth', 'access_token': secrets.homemon_key}))
                self._read(ws)

                ws.send(json.dumps({'id': 1, 'type': 'get_states'}))
                self._read(ws)

                ws.send(json.dumps({'id': 2, 'type': 'subscribe_events', 'event_type': 'state_changed'}))

                while self._runEnable:
                    if not self._read(ws):
                        break

            except Exception as emsg:
                eprint("Got Run Exception: {}".format(emsg))

class Panel(QWidget):

    def __init__(self,parent=None):
        super(Panel,self).__init__(parent)

        # Db interface
        self.db = mysql.Mysql("panel")

        # Setup brushes
        bgBrush = QBrush(Qt.white)
        bgBrush.setStyle(Qt.SolidPattern)
        fgBrush = QBrush(Qt.black)
        fgBrush.setStyle(Qt.SolidPattern)

        # Setup palette
        palette = QPalette()
        palette.setBrush(QPalette.Active,   QPalette.WindowText, fgBrush)
        palette.setBrush(QPalette.Active,   QPalette.Text,       fgBrush)
        palette.setBrush(QPalette.Active,   QPalette.Base,       bgBrush)
        palette.setBrush(QPalette.Active,   QPalette.Window,     bgBrush)
        palette.setBrush(QPalette.Disabled, QPalette.WindowText, fgBrush)
        palette.setBrush(QPalette.Disabled, QPalette.Text,       fgBrush)
        palette.setBrush(QPalette.Disabled, QPalette.Base,       bgBrush)
        palette.setBrush(QPalette.Disabled, QPalette.Window,     bgBrush)
        palette.setBrush(QPalette.Inactive, QPalette.WindowText, fgBrush)
        palette.setBrush(QPalette.Inactive, QPalette.Text,       fgBrush)
        palette.setBrush(QPalette.Inactive, QPalette.Base,       bgBrush)
        palette.setBrush(QPalette.Inactive, QPalette.Window,     bgBrush)
        self.setPalette(palette)

        # Windows
        self.temp     = TempChart(self.db,self)
        self.wind     = WindChart(self.db,self)
        self.status   = StatusWindow(self.db,self)
        self.door     = DoorWindow(self.db,self)
        self.forecast = ForecastWindow(self.db,self)

        # Top
        hbox = QHBoxLayout()
        self.setLayout(hbox)

        # Left
        hbox.addWidget(self.status)

        # Right
        qbox = QGridLayout()
        qbox.setSpacing(0)
        qbox.setContentsMargins(0,0,0,0)
        qbox.setHorizontalSpacing(0)

        qbox.addWidget(self.forecast,0,0,1,4)
        qbox.addWidget(self.temp,1,0,2,1)
        qbox.addWidget(self.wind,3,0,2,1)
        qbox.addWidget(self.door,5,0,2,1)

        qbox.addWidget(CamImage (int(640*1.5),int(480*1.5),'tcp://aliska.amaroq.net:9020',self),  1, 1, 6, 3, Qt.AlignCenter | Qt.AlignVCenter)
        hbox.addLayout(qbox)

        # Stretch policy
        for i in range(0,4):
            qbox.setColumnStretch(i,1)

        self.hass = HassListener()

        self.hass.stateUpdate.connect(self.status.stateUpdate)
        self.hass.stateUpdate.connect(self.door.stateUpdate)

        self.showFullScreen()

app = QApplication(sys.argv)
panel = Panel()
panel.show()

call(["xset","s","off"])     # don't activate screensaver
call(["xset","s","noblank"]) # don't blank the video device
call(["xset","-dpms"])       # disable DPMS (Energy Star) features.

app.exec_()
panel.close()

