#!/usr/bin/python3

import sys
import time
import threading
import zmq
import base64
import numpy as np
import cv2

urls = ['rtsp://view:lolhak@172.16.20.5:554/h264Preview_01_sub',
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_02_sub',
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_03_sub',
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_04_sub',
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_05_sub',
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_06_sub',
        'http://coopcam.amaroq.net/video.cgi']

class ImgReceiver(object):
    def __init__(self, url):
        self.url  = url
        self.img  = None
        self.cap  = None
        self.cnt  = 0
        self.time = 0

        print("Opening {}".format(self.url))
        self.thread = threading.Thread(target=self.worker)
        self.thread.start()

    def worker(self):
        while True:
            self.cap = cv2.VideoCapture(self.url)
            self.time = time.time()
            print("Opened {}".format(self.url))

            ret, frame = self.cap.read()

            while ret and ((time.time() - self.time) < 300):
                self.img = frame
                self.cnt += 1

                if (time.time() - self.time) > 5.0:
                    print("Frame rate from {} = {}".format(self.url,self.cnt/(time.time()-self.time)))
                    self.cnt = 0
                    self.time = time.time()

                ret, frame = self.cap.read()

            print("Reopening {}".format(self.url))
            self.cap = None
            time.sleep(1)

imgRx = [ImgReceiver(u) for u in urls]
ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind('tcp://*:9020')

while True:
    try:
        time.sleep(0.25)

        newImg = np.zeros((int(480*1.5) , int(640*1.5),3),np.uint8)

        # Large upper left, gate
        if imgRx[1].img is not None:
            newImg[0:480,0:640] = imgRx[1].img

        # Lower left, garage
        if imgRx[0].img is not None:
            newImg[480:720,0:320] = cv2.resize(imgRx[0].img,(320,240))

        # Lower middle, front
        if imgRx[2].img is not None:
            newImg[480:720,320:640] = cv2.resize(imgRx[2].img,(320,240))

        # Upper right, rear
        if imgRx[3].img is not None:
            newImg[0:240,640:960] = cv2.resize(imgRx[3].img,(320,240))

        # Middle right, Roses
        if imgRx[5].img is not None:
            newImg[240:480,640:960] = cv2.resize(imgRx[5].img,(320,240))

        # Lower right, Side
        if imgRx[4].img is not None:
            newImg[480:720,640:960] = cv2.resize(imgRx[4].img,(320,240))

        # Overlay, Coop
        if imgRx[6].img is not None:
            newImg[200:440,0:320] = cv2.resize(imgRx[6].img,(320,240))

        encoded, buf = cv2.imencode('.jpg',newImg)
        if encoded:
            pub.send(base64.b64encode(buf))

    except Exception as e:
        print("Got exception {}".format(e))
        time.sleep(1)


