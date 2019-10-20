#!/usr/bin/env python3

def eprint(msg):
    print(msg)

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
        cnt = 0

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
                self.time  = time.time()
                self.rtime = time.time()

                eprint("Entering inner loop")
                try:
                    while ((time.time() - self.time) < 300):
                        img = QPixmap.fromImage(QImage.fromData(base64.b64decode(sub.recv())))
                        self.imageUpdate.emit(img)
                        count += 1
                        cnt += 1

                        if (time.time() - self.rtime) > 30.0:
                            print("Frame rate {}".format(cnt/(time.time()-self.rtime)))
                            cnt = 0
                            self.rtime = time.time()


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

app = QApplication(sys.argv)
win = CamImage (int(640*1.5),int(480*1.5),'tcp://aliska.amaroq.net:9020',None)
win.show()
app.exec_()
win.close()

