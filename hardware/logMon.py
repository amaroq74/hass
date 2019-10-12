import datetime
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind(('',8111))

while True:
    data, address = sock.recvfrom(4096)
    now = datetime.datetime.now()
    print("{} - {}: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               address[0],
                               data.decode('utf-8').rstrip()))

