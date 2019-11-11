import datetime
import socket
import sys

hosts = { '172.16.20.50' :  'pool_control',
          '172.16.20.51' :  'east_sprinklers',
          '172.16.20.52' :  'gate_control',
          '172.16.20.53' :  'coop_control',
          '172.16.20.54' :  'garage_control',
          '172.16.20.55' :  'pantry_control'}

#filt = "pool_control"
#filt = "east_sprinklers"
#filt = "gate_control"
#filt = "coop_control"
#filt = "garage_control"
#filt = "pantry_control"
#filt = None

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind(('',8111))

while True:
    data, address = sock.recvfrom(4096)

    if address[0] in hosts:
        host = hosts[address[0]]
    else:
        host = address[0]

    if filt is None or host == filt:
        now = datetime.datetime.now()
        print("{} - {}: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                   host,
                                   data.decode('utf-8').rstrip()))

