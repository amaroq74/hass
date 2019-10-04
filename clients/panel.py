#!/usr/bin/env python3

ferr = open("/amaroq/home/media-family/panel.log","a")

def eprint(*args, **kwargs):
    global ferr
    print(*args, file=ferr, **kwargs)
    ferr.flush()

eprint("----------------------- Starting ----------------------------")

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

import vlc
import threading
import cv2


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
               {'label':'Pool Temp',    'key':'sensor.pool_temperature',     'conv':disp_temp,      'box':None } ]

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
            lab = QLabel(sen['label'] + ':')
            lab.setFont(lfont)
            gl.addWidget(lab,idx,0,1,1,Qt.AlignRight)
            sen['box'] = QLabel('')
            sen['box'].setFont(vfont)
            gl.addWidget(sen['box'],idx,1,1,1,Qt.AlignLeft)
            idx += 1

        self.dateBox = QLabel('Date')
        self.timeBox = QLabel('Time')
        self.dateBox.setFont(lfont)
        self.timeBox.setFont(lfont)
        gl.addWidget(self.dateBox,idx,0,1,2,Qt.AlignCenter)
        gl.addWidget(self.timeBox,idx+1,0,1,2,Qt.AlignCenter)
        self.setLayout(gl)

    def stateUpdate (self, key, value ):
        for sen in StatusList:
            if sen['key'] == key and value != 'unknown' and value is not None:
                sen['conv'](value,sen['box'])

        self.dateBox.setText(datetime.datetime.now().strftime("%m/%d/%y"))
        self.timeBox.setText(datetime.datetime.now().strftime("%H:%M:%S"))


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

        for idx in range(0,8):
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
            url = "http://api.wunderground.com/api/" + secrets.wunder_api + "/forecast/q/94062.xml"

            with urllib.request.urlopen(url) as fh:
                ures = fh.read().rstrip()

            root = ET.fromstring(ures)

            for day in root.findall('./forecast/txt_forecast/forecastdays/forecastday'):
                per  = int(day.findall('./period')[0].text)
                dow  = day.findall('./title')[0].text
                cond = day.findall('./fcttext')[0].text 
                iurl = day.findall('./icon_url')[0].text 

                if per < 10:
                    with urllib.request.urlopen(iurl) as imgReq:
                        icon = imgReq.read()

                    self.dayName[per].setText(dow) 
                    self.dayInfo[per].setText(cond)
                    self.dayPixmap[per].loadFromData(icon) 
                    self.dayLabel[per].setPixmap(self.dayPixmap[per])
                    self.dayLabel[per].update()

        except Exception as e:
            eprint("go forecast exception: {}".format(e))

        QTimer.singleShot(10 * 60 * 1000,self.refreshForecast) # 15 minutes

#class CamVlc(QWidget):
#    def __init__(self, width, height, url, parent=None):
#        super(CamVlc, self).__init__(parent)
#
#        self.setFixedSize(width,height)
#
#        self.vlc = vlc.Instance(['--video-on-top', '--no-audio'])
#
#        self.video = QFrame()
#
#        self.player = self.vlc.media_player_new()
#        self.player.audio_set_mute(True)
#        self.player.set_mrl(url)
#        self.player.set_xwindow(int(self.winId()))
#        self.player.play()

class CamImage(QWidget):
    def __init__(self, width, height, url, parent=None):
        super(CamImage, self).__init__(parent)

        self.height=height
        self.width=width

        self.url = url
        self.time = time.time()

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.label = QLabel()
        self.label.setFixedSize(width,height)
        self.label.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)

        vb.addWidget(self.label)

        self.thread=threading.Thread(target=self.refresh)
        self.thread.start()

    def refresh(self):
        while True:
            try:

                cap = cv2.VideoCapture(self.url) # it can be rtsp or http stream
                ret, frame = cap.read()

                while ret and ((time.time() - self.time) < 300):
                    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    h, w, ch = rgbImage.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = PyQt5.QtGui.QImage(rgbImage.data, w, h, bytesPerLine, PyQt5.QtGui.QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(self.width, self.height, Qt.KeepAspectRatio)

                    self.label.setPixmap(QPixmap.fromImage(p))
                    self.label.update()

                    time.sleep(0.1)
                    ret, frame = cap.read()

            except Exception as e:
                eprint("got camera exception: {}".format(e))

            time.sleep(1)
            self.time = time.time()
            eprint("Restarting {}".format(self.url))

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

        # 640 x 480
        # 620 x 465
        # 600 x 450
        # 560 x 420
                                                                                                      #  R  C  RS CS
        qbox.addWidget(CamImage (600,450,'rtsp://view:lolhak@172.16.20.5:554/h264Preview_02_sub',self),  1, 1, 4, 2, Qt.AlignCenter | Qt.AlignVCenter)
        qbox.addWidget(CamImage (300,225,'rtsp://view:lolhak@172.16.20.5:554/h264Preview_01_sub',self),  5, 1, 2, 1, Qt.AlignCenter | Qt.AlignVCenter)
        qbox.addWidget(CamImage (300,225,'rtsp://view:lolhak@172.16.20.5:554/h264Preview_03_sub',self),  5, 2, 2, 1, Qt.AlignCenter | Qt.AlignVCenter)
        qbox.addWidget(CamImage (300,225,'rtsp://view:lolhak@172.16.20.5:554/h264Preview_04_sub',self),  1, 3, 2, 1, Qt.AlignCenter | Qt.AlignVCenter)
        qbox.addWidget(CamImage (300,225,'rtsp://view:lolhak@172.16.20.5:554/h264Preview_05_sub',self),  3, 3, 2, 1, Qt.AlignCenter | Qt.AlignVCenter)
        qbox.addWidget(CamImage (300,225,'http://coopcam.amaroq.net/video.cgi',self),                    5, 3, 2, 1, Qt.AlignCenter | Qt.AlignVCenter)
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

