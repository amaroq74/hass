#!/usr/bin/env python3

# Add relative path
import sys,datetime
sys.path.append('/amaroq/hass/pylib')

import time, pytz
import hass_mysql as mysql
import weather_convert as convert

from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWebKit  import *

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import urllib
import xml.etree.ElementTree as ET

from subprocess import call

import json
import yaml
from websocket import create_connection

# Display functions
def disp_temp(val, box):
    box.setText("%2.2F F" % ( float(val) )) 

def disp_humid(val, box):
    box.setText("%i %%" % ( float(val) ))

def disp_winddir(val, box):
    box.setText(convert.windDegToCompass(float(val)))

def disp_winddeg(val, box):
    box.setText("%i Deg" % (float(val)))

def disp_speed(val, box):
    box.setText("%2.2F MPH" % ( convert.speedMpsToMph(float(val)) ))

def disp_rain(val, box):
    box.setText("%2.2F IN" % ( convert.rainMmToIn(float(val)) ))

def disp_pressure(val, box):
    box.setText("%2.2F INHG" % ( convert.pressureHpaToInhg(float(val)) ))

def disp_power(val, box):
    box.setText("%2.2F KW" % ( float(val) ))

def disp_door(val, box):
    box.setText('Closed' if val == 'off' else 'Open')

# Status List
StatusList = [ {'label':'Out Temp',     'key':'sensor.outdoor_temp',       'conv':disp_temp,      'box':None },
               {'label':'Out Humid',    'key':'sensor.outdoor_humidity',   'conv':disp_humid,     'box':None },
               {'label':'Wind Dir',     'key':'sensor.wind',               'conv':disp_winddir,   'box':None },
               {'label':'Wind Avg',     'key':'sensor.wind_avg',           'conv':disp_speed,     'box':None },
               {'label':'Wind Gust',    'key':'sensor.wind_gust',          'conv':disp_speed,     'box':None },
               {'label':'Rain Rate',    'key':'sensor.rain_rate',          'conv':disp_rain,      'box':None },
               {'label':'Rain Today',   'key':'sensor.rain_day',           'conv':disp_rain,      'box':None },
               {'label':'Barometer',    'key':'sensor.indoor_pressure',    'conv':disp_pressure,  'box':None },
               {'label':'House Temp',   'key':'sensor.house_temp',         'conv':disp_temp,      'box':None },
               {'label':'Thermostat',   'key':'climate.house',             'conv':disp_temp,      'box':None },
               {'label':'Family Temp',  'key':'sensor.indoor_temp',        'conv':disp_temp,      'box':None },
               {'label':'Family Humid', 'key':'sensor.indoor_humidity',    'conv':disp_humid,     'box':None },
               {'label':'Master Temp',  'key':'sensor.master_temp',        'conv':disp_temp,      'box':None },
               {'label':'Master Humid', 'key':'sensor.master_humidity',    'conv':disp_humid,     'box':None },
               {'label':'BedR Temp',    'key':'sensor.bedr_temp',          'conv':disp_temp,      'box':None },
               {'label':'BedR Humid',   'key':'sensor.bedr_humidity',      'conv':disp_humid,     'box':None },
               {'label':'BedTA Temp',   'key':'sensor.bedta_temp',         'conv':disp_temp,      'box':None },
               {'label':'BedTA Humid',  'key':'sensor.bedta_humidity',     'conv':disp_humid,     'box':None },
               {'label':'Power Use',    'key':'sensor.smartmeter_rate',    'conv':disp_power,     'box':None },
               {'label':'Garage Temp',  'key':'sensor.garage_temp',        'conv':disp_temp,      'box':None },
               {'label':'Garage Humid', 'key':'sensor.garage_humidity',    'conv':disp_humid,     'box':None },
               {'label':'Shed Temp',    'key':'sensor.shed_temp',          'conv':disp_temp,      'box':None },
               {'label':'Shed Humid',   'key':'sensor.shed_humidity',      'conv':disp_humid,     'box':None },
               {'label':'Camper Temp',  'key':'sensor.camper_temp',        'conv':disp_temp,      'box':None },
               {'label':'Chicken Temp', 'key':'sensor.chickens_temp',      'conv':disp_temp,      'box':None },
               {'label':'Pool Temp',    'key':'sensor.pool_temp',          'conv':disp_temp,      'box':None } ]

# Camera List
CamList = { 'Garage'   : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=4&scale=100&maxfps=2&user=home&pass=monitor",
            'Gate'     : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=1&scale=100&maxfps=2&user=home&pass=monitor",
            'Front'    : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=2&scale=100&maxfps=2&user=home&pass=monitor",
            'Rear'     : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=3&scale=100&maxfps=1&user=home&pass=monitor",
            'Side'     : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=5&scale=100&maxfps=1&user=home&pass=monitor",
            'Chickens' : "https://www.amaroq.net/cgi-bin/nph-zms?mode=jpeg&monitor=6&scale=100&maxfps=1&user=home&pass=monitor"}

DoorList = [{'label':'Ped<br/>Gate',      'key':'binary_sensor.ped_gate',     'box':None },
            {'label':'Car<br/>Gate',      'key':'binary_sensor.car_gate',     'box':None },
            {'label':'Chicken<br/>Gate',  'key':'binary_sensor.chicken_gate', 'box':None },
            {'label':'Ivy<br/>Gate',      'key':'binary_sensor.ivy_gate',     'box':None },
            {'label':'Garbage<br/>Gate',  'key':'binary_sensor.garbage_gate', 'box':None },
            {'label':'Garage<br/>Door',   'key':'binary_sensor.garage_door',  'box':None },
            {'label':'Office<br/>Door',   'key':'binary_sensor.office_door',  'box':None },
            {'label':'Bath<br/>Door',     'key':'binary_sensor.pbath_door',   'box':None },
            {'label':'Kitchen<br/>Door',  'key':'binary_sensor.kitchen_door', 'box':None }]

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
        idx = 0

        lfont = QFont()
        lfont.setPointSize(13)
        lfont.setBold(True)

        for sen in DoorList:
            sen['box'] = QTextEdit(sen['label'])
            sen['box'].setFont(lfont)
            sen['box'].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            sen['box'].setReadOnly(True)

            p = QPalette()
            p.setColor(QPalette.Base,Qt.red)
            p.setColor(QPalette.Text,Qt.black)
            sen['box'].setPalette(p)  

            gl.addWidget(sen['box'],idx/3,idx%3,1,1,Qt.AlignCenter)
            idx += 1

        self.setLayout(gl)

    def stateUpdate (self, key, value ):
        for sen in DoorList:
            if sen['key'] == key:

                p = QPalette()
                p.setColor(QPalette.Text,Qt.black)

                if value == 'on':
                    p.setColor(QPalette.Base,Qt.red)
                else:
                    p.setColor(QPalette.Base,Qt.green)
                sen['box'].setPalette(p)

class StatusWindow(QWidget):
    def __init__(self, db, parent=None):
        super(StatusWindow, self).__init__(parent)

        self.db = db

        gl = QGridLayout()
        idx = 0

        lfont = QFont()
        lfont.setPointSize(16)
        lfont.setBold(True)
        vfont = QFont()
        vfont.setPointSize(14)
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
            if sen['key'] == key:
                sen['conv'](value,sen['box'])

        self.dateBox.setText(datetime.datetime.now().strftime("%m/%d/%y"))
        self.timeBox.setText(datetime.datetime.now().strftime("%H:%M:%S"))


class ForecastWindow(QWidget):
    def __init__(self, db, parent=None):
        super(ForecastWindow, self).__init__(parent)

        self.db = db

        nfont = QFont()
        nfont.setPointSize(12)
        nfont.setBold(True)
        ifont = QFont()
        ifont.setPointSize(10)
        ifont.setBold(True)

        self.dayName   = [None for i in range(0,10)]
        self.dayLabel  = [None for i in range(0,10)]
        self.dayInfo   = [None for i in range(0,10)]
        self.dayPixmap = [None for i in range(0,10)]

        gl = QGridLayout()

        for idx in range(0,10):
            self.dayName[idx] = QLabel()
            self.dayName[idx].setAlignment(Qt.AlignCenter)
            self.dayName[idx].setFont(nfont)
            self.dayName[idx].setFixedSize(120,45)
            self.dayName[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            gl.addWidget(self.dayName[idx],0,idx,1,1,Qt.AlignCenter)

            self.dayLabel[idx] = QLabel()
            self.dayLabel[idx].setFixedSize(50,50)
            self.dayLabel[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            gl.addWidget(self.dayLabel[idx],1,idx,1,1,Qt.AlignCenter)

            self.dayInfo[idx] = QLabel()
            self.dayInfo[idx].setAlignment(Qt.AlignCenter)
            self.dayInfo[idx].setFont(ifont)
            self.dayInfo[idx].setFixedSize(120,50)
            self.dayInfo[idx].setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            gl.addWidget(self.dayInfo[idx],2,idx,1,1,Qt.AlignCenter)

            self.dayPixmap[idx] = QPixmap()

        gl.setHorizontalSpacing(0)
        gl.setSpacing(0)
        gl.setContentsMargins(0,0,0,0)

        self.setLayout(gl)
        self.refreshForecast()

    def refreshForecast(self):

        # Get the forecast
        with urllib.request.urlopen("http://api.wunderground.com/api/1fa664001be84d7a/forecast10day/q/94062.xml") as fh:
            ures = fh.read().rstrip()

        try:

            root = ET.fromstring(ures)

            for day in root.findall('./forecast/simpleforecast/forecastdays/forecastday'):
                per  = int(day.findall('./period')[0].text) - 1
                dow  = day.findall('./date/weekday')[0].text
                high = day.findall('./high/fahrenheit')[0].text
                low  = day.findall('./low/fahrenheit')[0].text
                cond = day.findall('./conditions')[0].text
                iurl = day.findall('./icon_url')[0].text
                pop  = day.findall('./pop')[0].text

                with urllib.request.urlopen(iurl) as imgReq:
                    icon = imgReq.read()

                self.dayName[per].setText(dow) 
                self.dayInfo[per].setText("%s\nH %s  L %s\nPrec %s %%" % (cond,high,low,pop))

                self.dayPixmap[per].loadFromData(icon) 
                self.dayLabel[per].setPixmap(self.dayPixmap[per])
                self.dayLabel[per].update()
        except Exception as e:
            print("got forecast exception: {}".format(e))

        QTimer.singleShot(10 * 60 * 1000,self.refreshForecast) # 15 minutes

class CamListener(QThread):

    newFrame = pyqtSignal(str,object)

    def __init__(self, db, camName, parent=None):
        QThread.__init__(self,parent)

        self.db = db
        self._camName = camName
        self._pause = False
        self._last = time.time()
        self._fh   = None

        # Start threads
        self._runEnable = True
        self.start()
        self.selfCheck()

    def halt(self):
        self._runEnable = False

    def pause(self):
        self._pause = True
        self._fh.close()
        self._fh = None

    def resume(self):
        self._pause = False

    def selfCheck(self):
        if self._fh != None and (time.time() - self._last) > 60:
            try:
                self._fh.close()
            except:
                pass
            self._fh = None
            time.sleep(1)

        QTimer.singleShot(60000,self.selfCheck) # One minute

    def run(self):

        while self._runEnable:

            try:

                if self._pause:
                    if self._fh != None: self._fh.close()
                    self._fh = None

                    while self._pause:
                        self._last = time.time()
                        time.sleep(1)

                if self._fh == None:
                    self._last = time.time()
                    self._fh = urllib.request.urlopen(CamList[self._camName])

                # Find marker
                d = self._fh.readline()
                while d.decode('utf-8').rstrip() != '--ZoneMinderFrame': 
                    d = self._fh.readline()

                # Skip lines and extract length
                self._fh.readline()
                count = int(self._fh.readline().decode('utf-8').rstrip().split(':')[1])
                self._fh.readline()

                # Read image
                img = self._fh.read(count)
                self._last = time.time()
                self.newFrame.emit(self._camName,img)

            except Exception as e:
                print("got camera exception: {}".format(e))
                try:
                    self._fh.close()
                    self._fh = None
                except:
                    pass

class CamWindow(QWidget):
    def __init__(self, height, camName, parent=None):
        super(CamWindow, self).__init__(parent)

        self.label   = QLabel()
        self.height  = height
        self.camName = camName
        self.timeOut = 0

        gr = QGridLayout()
        gr.addWidget(self.label,0,0)
        self.setLayout(gr)

    def newFrame(self,camName,img):
        if self.timeOut != 0 and time.time() > self.timeOut:
            self.camName = 'popup'
            self.timeOut = 0
            self.close()

        if self.camName == camName:
            pixmap = QPixmap()
            pixmap.loadFromData(img)
            pixmap = pixmap.scaledToHeight(self.height)
            self.label.setPixmap(pixmap)
            self.label.update()

#class ControlWindow(QDialog):
#    def __init__(self,db,parent=None):
#        super(ControlWindow,self).__init__(parent)
#        self.db = db
#
#        vbox = QVBoxLayout()
#        self.setLayout(vbox)
#
#        gl = QGridLayout()
#        vbox.addLayout(gl)
#
#        # Thermostat Control
#        col = 0
#        self.addHeader(gl,0,col,'Thermostat')
#        self.addVariable(gl,1,col,'House_Heat','setpoint','Set Point') 
#
#        # Get device list
#        dList = self.db.getDeviceList()
#        dListIdx = {dev['name']:dev for dev in dList}
#
#        # Light Control
#        self.addHeader(gl,2,col,'Lights & Other')
#        row = 3
#        for dev in dList:
#            if dev['category'] == 'Lights' or dev['category'] == 'Other' and dev['hidden'] == 0:
#                self.addDevice(gl,row,col,dev)
#                row += 1
#
#        # Pool Controls
#        col = 7
#        row = 0
#        self.addHeader(gl,row,col,'Pool')
#        self.addDevice(gl,row+1,col,dListIdx['Pool_Main'])
#        self.addDevice(gl,row+2,col,dListIdx['Pool_Sweep'])
#        self.addVariable(gl,row+3,col,'Pool_Heat','setpoint','Set Point')
#
#        # Garage and gate
#        self.addHeader(gl,row+4,col,'Garage & Gate')
#        self.addDevice(gl,row+5,col,dListIdx['Car_Gate'])
#        self.addDevice(gl,row+6,col,dListIdx['Garage_Door'])
#
#        # Irrigation
#        row = 7
#        self.addHeader(gl,row,col,'Irrigation')
#        row += 1
#        for dev in dList:
#            if dev['category'] == 'Irrigation' and dev['hidden'] == 0:
#                self.addDevice(gl,row,col,dev)
#                row += 1
#
#        # Variables
#        self.addHeader(gl,row,col,'Security')
#
#        self.addVariable(gl,row+1,col,'Security','dcare_arm','Dcare Arm') 
#        self.addVariable(gl,row+2,col,'Security','house_arm','House Arm') 
#        self.addVariable(gl,row+3,col,'Security','door_arm','Door Arm') 
#
#        cl = QPushButton('Close')
#        cl.clicked.connect(self.accept)
#        vbox.addWidget(cl)
#
#        self.setWindowTitle("Home Control")
#
#    def addVariable(self, lo, row, col, group, name, title):
#        varInfo = self.db.getVariableInfo(group,name)
#        lo.addWidget(QLabel(title), row, col, 1, 1, Qt.AlignRight)
#        val = QSpinBox()
#        val.setRange(varInfo['range_min'],varInfo['range_max'])
#        val.setValue(varInfo['value'])
#
#        bset = QPushButton('Set')
#        bset.clicked.connect(lambda: self.setVariable(group,name,val))
#
#        lo.addWidget (val, row, col+1, 1, 1, Qt.AlignHCenter )
#        lo.addWidget (bset, row, col+2, 1, 1, Qt.AlignHCenter )
#
#    def addHeader(self, lo, row, col, text):
#        lab = QLabel("<P><b><i><FONT COLOR='#0000FF' FONT SIZE = 4>%s</i></b></P>" % (text))
#        lab.setFrameStyle(QFrame.Panel | QFrame.Sunken)
#        lo.addWidget (lab, row, col, 1, 3, Qt.AlignHCenter)
#
#    def addDevice(self,lo, row,col,dev):
#        lo.addWidget(QLabel(dev['name'] + ':'), row, col, 1, 1, Qt.AlignRight )
#
#        if dev['type'] == 'OnOff':
#            on = QPushButton('On')
#            on.clicked.connect(lambda: self.setDevice(dev['name'],100))
#            lo.addWidget(on, row, col+1, 1, 1, Qt.AlignHCenter )
#
#            off = QPushButton('Off')
#            off.clicked.connect(lambda: self.setDevice(dev['name'],0))
#            lo.addWidget(off, row, col+2, 1, 1, Qt.AlignHCenter )
#
#        elif dev['type'] == 'OpenCloseToggle':
#            on = QPushButton('Open')
#            on.clicked.connect(lambda: self.setDevice(dev['name'],100))
#            lo.addWidget(on, row, col+1, 1, 1, Qt.AlignHCenter )
#
#            off = QPushButton('Close')
#            off.clicked.connect(lambda: self.setDevice(dev['name'],0))
#            lo.addWidget(off, row, col+2, 1, 1, Qt.AlignHCenter )
#
#            tog = QPushButton('Toggle')
#            tog.clicked.connect(lambda: self.setDevice(dev['name'],50))
#            lo.addWidget(tog, row, col+3, 1, 1, Qt.AlignHCenter )
#
#        elif dev['type'] == 'Fan':
#            on = QPushButton('Low')
#            on.clicked.connect(lambda: self.setDevice(dev['name'],20))
#            lo.addWidget(on, row, col+1, 1, 1, Qt.AlignHCenter )
#
#            off = QPushButton('Med')
#            off.clicked.connect(lambda: self.setDevice(dev['name'],50))
#            lo.addWidget(off, row, col+2, 1, 1, Qt.AlignHCenter )
#
#            off = QPushButton('High')
#            off.clicked.connect(lambda: self.setDevice(dev['name'],50))
#            lo.addWidget(off, row, col+3, 1, 1, Qt.AlignHCenter )
#
#            off = QPushButton('Off')
#            off.clicked.connect(lambda: self.setDevice(dev['name'],100))
#            lo.addWidget(off, row, col+4, 1, 1, Qt.AlignHCenter )
#
#    def setDevice(self,name,level):
#        self.db.setDevice(name,level)
#
#    def setVariable(self,group,name,sbox):
#        self.db.setVariable(group,name,sbox.value())

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

        if 'climate' in key: 
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
        except Exception as e:
            return False

        return True

    def run(self):

        while self._runEnable:
            try:
                ws = create_connection('ws://aliska.amaroq.net:8123/api/websocket',timeout=60*10)

                ws.send(json.dumps({'type': 'auth', 'api_password': 'TEST1234'}))
                self._read(ws)

                ws.send(json.dumps({'id': 1, 'type': 'get_states'}))
                self._read(ws)

                ws.send(json.dumps({'id': 2, 'type': 'subscribe_events', 'event_type': 'state_changed'}))

                while self._runEnable:
                    if not self._read(ws):
                        break

            except Exception as e:
                pass

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

        self.camWin = {}
        for cam in CamList:
            if cam == 'Gate':
                self.camWin[cam] = CamWindow(440,cam,self)
            else:
                self.camWin[cam] = CamWindow(220,cam,self)

        # Top
        hbox = QHBoxLayout()
        self.setLayout(hbox)

        # Left
        hbox.addWidget(self.status)

        # Right
        qbox = QGridLayout()
        qbox.setSpacing(0)
        qbox.setContentsMargins(0,0,0,0)

        qbox.addWidget(self.forecast,0,0,1,4)

        qbox.addWidget(self.temp,1,0,2,1)
        qbox.addWidget(self.wind,3,0,2,1)
        qbox.addWidget(self.door,5,0,2,1)

        qbox.addWidget(self.camWin['Gate'],1,1,4,2)
        qbox.addWidget(self.camWin['Garage'],5,1,2,1)
        qbox.addWidget(self.camWin['Front'],5,2,2,1)
        qbox.addWidget(self.camWin['Rear'],1,3,2,1)
        qbox.addWidget(self.camWin['Side'],3,3,2,1)
        qbox.addWidget(self.camWin['Chickens'],5,3,2,1)
        hbox.addLayout(qbox)

        # Stretch policy
        for i in range(0,4):
            qbox.setColumnStretch(i,1)

        self.camGen = {}
        for cam in CamList:
            self.camGen[cam] = CamListener(self.db,cam,self)
            self.camGen[cam].newFrame.connect(self.camWin[cam].newFrame)

        self.hass = HassListener()

        self.hass.stateUpdate.connect(self.status.stateUpdate)
        self.hass.stateUpdate.connect(self.door.stateUpdate)

        self.showFullScreen()

#    def mouseReleaseEvent(self, mouseEvent):
#        for cam in CamList:
#            self.camGen[cam].pause()
#
#        control = ControlWindow(self.db,self)
#        control.exec_()
#
#        for cam in CamList:
#            self.camGen[cam].resume()
 
app = QApplication(sys.argv)
panel = Panel()
panel.show()

call(["xset","s","off"])     # don't activate screensaver
call(["xset","s","noblank"]) # don't blank the video device
call(["xset","-dpms"])       # disable DPMS (Energy Star) features.

app.exec_()
panel.close()

