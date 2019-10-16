#!/usr/bin/python3
import sys
sys.path.append('/usr/local/lib/video_ai')

import os
import time
import threading
import zmq
import base64
import numpy as np
import cv2
import tensorflow as tf

from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util

# Path to frozen detection graph. This is the actual model that is used for the object detection.
MODEL_NAME = 'ssd_mobilenet_v1_coco_11_06_2017'
PATH_TO_CKPT = os.path.join('/usr/local/lib/video_ai', 'object_detection', MODEL_NAME, 'frozen_inference_graph.pb')

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join('/usr/local/lib/video_ai', 'object_detection', 'data', 'mscoco_label_map.pbtxt')

NUM_CLASSES = 90

# Loading label map
label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

urls = ['rtsp://view:lolhak@172.16.20.5:554/h264Preview_01_sub', # 0
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_02_sub', # 1
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_03_sub', # 2
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_04_sub', # 3
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_05_sub', # 4
        'rtsp://view:lolhak@172.16.20.5:554/h264Preview_06_sub', # 5
        'http://coopcam.amaroq.net/video.cgi']                   # 6


def detect_objects(image_np, sess, detection_graph):
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

    # Each box represents a part of the image where a particular object was detected.
    boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

    # Each score represent how level of confidence for each of the objects.
    # Score is shown on the result image, together with the class label.
    scores = detection_graph.get_tensor_by_name('detection_scores:0')
    classes = detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

    # Actual detection.
    (boxes, scores, classes, num_detections) = sess.run(
        [boxes, scores, classes, num_detections],
        feed_dict={image_tensor: image_np_expanded})

    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        np.squeeze(boxes),
        np.squeeze(classes).astype(np.int32),
        np.squeeze(scores),
        category_index,
        use_normalized_coordinates=True,
        line_thickness=4)
    return image_np


class ImgReceiver(object):
    def __init__(self, url,i):
        self.url   = url
        self.img   = None
        self.cap   = None
        self.cnt   = 0
        self.time  = 0
        self.itime = 0
        self.rtime = 0
        self.i     = i
        self.sess  = None

        if i in [0,1,2,3]:

            # Load detection graph
            self.detection_graph = tf.Graph()
            with self.detection_graph.as_default():
                od_graph_def = tf.compat.v1.GraphDef()

                with tf.compat.v1.io.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
                    serialized_graph = fid.read()
                    od_graph_def.ParseFromString(serialized_graph)
                    tf.import_graph_def(od_graph_def, name='')

                self.sess = tf.compat.v1.Session(graph=self.detection_graph)

        print("Opening {}".format(self.url))
        self.thread = threading.Thread(target=self.worker)
        self.thread.start()

    def worker(self):
        while True:
            self.cap = cv2.VideoCapture(self.url)
            self.time  = time.time()
            self.itime = time.time()
            self.rtime = time.time()
            print("Opened {}".format(self.url))

            ret, frame = self.cap.read()

            while ret and ((time.time() - self.time) < 300):

                if (time.time() - self.itime) > 0.25:

                    if self.i == 6:
                        frame = cv2.resize(frame,(300,225))
                    elif self.i != 1:
                        frame = cv2.resize(frame,(320,240))

                    if self.sess:
                        rgbImg = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self.img = detect_objects(rgbImg, self.sess, self.detection_graph)
                    else:
                        self.img = frame

                    self.cnt += 1
                    self.itime = time.time()

                if (time.time() - self.rtime) > 30.0:
                    print("Frame rate from {} = {}".format(self.url,self.cnt/(time.time()-self.time)))
                    self.cnt = 0
                    self.rtime = time.time()

                ret, frame = self.cap.read()

            print("Reopening {}".format(self.url))
            self.cap = None
            time.sleep(1)
        sess.close()

imgRx = []
for i in range(len(urls)):
    imgRx.append(ImgReceiver(urls[i],i))

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
            newImg[480:720,0:320] = imgRx[0].img

        # Lower middle, front
        if imgRx[2].img is not None:
            newImg[480:720,320:640] = imgRx[2].img

        # Upper right, rear
        if imgRx[3].img is not None:
            newImg[0:240,640:960] = imgRx[3].img

        # Middle right, Roses
        if imgRx[5].img is not None:
            newImg[240:480,640:960] = imgRx[5].img

        # Lower right, Side
        if imgRx[4].img is not None:
            newImg[480:720,640:960] = imgRx[4].img

        # Overlay, Coop
        if imgRx[6].img is not None:
            newImg[215:440,0:300] = imgRx[6].img

        rgbImg = cv2.cvtColor(newImg, cv2.COLOR_BGR2RGB)

        encoded, buf = cv2.imencode('.jpg',newImg)
        if encoded:
            pub.send(base64.b64encode(buf))

    except Exception as e:
        print("Got exception {}".format(e))
        time.sleep(1)


