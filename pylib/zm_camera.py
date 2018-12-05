
import socket
import time 
import threading

import sys
sys.path.append('/amaroq/hass/pylib')

import hass_secrets as secrets

class ZmCamera(threading.Thread):
    """Class to handle a zoneminder camera."""

    def __init__(self, camera):
        """ Create ZmCamera class. A trigger cancel thread is started.

        Arguments:
           camera:    Camera ID
        """
        threading.Thread.__init__(self)
        self._host      = secrets.zm_trig_host
        self._port      = secrets.zm_trig_port
        self._camera    = camera
        self._trigTime  = 0
        self._triggered = 0
        self._enable    = 1
        self._sensor    = ""
        self._lock      = threading.Lock()
        self.start()
 
    def halt(self):
        """ Stop the thread. """
        self._enable=0
        self.join()
        self.cancelCamera()

    def triggerCamera ( self, sensor, text, period ):
        """ Trigger the camera. Pass sensor value and period to trigger for. """
        self._lock.acquire()

        self._triggered = 1
        self._trigTime  = time.time() + period

        self._lock.release()

        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((self._host,self._port))

        msg = '{}|on|255|{}|{}|\n'.format(self._camera,sensor,text)
        s.send(msg.encode('utf-8'))
        s.close()

    def cancelCamera ( self ):
        """ Cancel the camera trigger."""
        self._lock.acquire()

        self._triggered = 0
        self._trigTime  = 0

        self._lock.release()

        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((self._host,self._port))

        msg = '{}|on|0|||\n'.format(self._camera)
        s.send(msg.encode('utf-8'))
        s.close()

    def run(self):

        # Loop while thread is enabled
        while self._enable == 1:

            # Triggered and time has elasped
            if self._triggered == 1 and self._trigTime < time.time():
                try:
                    self.cancelCamera()
                except :
                    time.sleep(.25)
            else:
                time.sleep(.25)

