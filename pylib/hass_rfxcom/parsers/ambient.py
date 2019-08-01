from hass_rfxcom.message import Message
from hass_rfxcom.parsers.util import *

# ######################################################
# Ambient weather F007PF pool sensor
# ######################################################
# Example Frame:
# 01 0100 0110 1011 0111 0000 0100 1100 0110 0010 1011 0001 0000
#|-- Fixed ---|-- Tag --|Chan|--- Temp -----|--Humid?-|---hash--|
#
# 0000 1111 1111 111
#|---- Next header--|
#
# 01 0100 0110 1011 0111 0000 0100 1100 0110 0010 1011 0001 0000 00000
#|--Fixed-----|--Tag----|Chan|--- Temp------|--Humid?-|---hash--|---tail----|
#
# 00000
#|--tail--|

class AmbientParser(object):
    
    @staticmethod
    def parse(length, p):

        # Verify message matches markers and length
        if length != 15 and p[0] != 0x8a:
            return False

        # Seed hash
        sHash = [0x3e, 0x1f, 0x97, 0xd3, 0xf1, 0xe0, 0x70, 0x38, 0x1c, 0x0e, 
                 0x07, 0x9b, 0xd5, 0xf2, 0x79, 0xa4, 0x52, 0x29, 0x8c, 0x46, 
                 0x23, 0x89, 0xdc, 0x6e, 0x37, 0x83, 0xd9, 0xf4, 0x7a, 0x3d, 
                 0x86, 0x43, 0xb9, 0xc4, 0x62, 0x31, 0x80, 0x40, 0x20, 0x10 ]

        # First convert to bit array, lsb to low index
        # Bit order is MSB first so we have to flip the bytes as
        # decoded by the rfxcom device
        bits = ""
        for d in p:
           bits += bin(d)[2:].zfill(8)[::-1]

        # Cut the message into the two identical bit strings, drop the first two bits
        # of each sub string. The message length is 48  bits
        lBits = bits[2:50]
        rBits = bits[67:115]

        # The two messages must match
        if lBits != rBits:
            return False
        
        # Compute hash
        mHash = 0x64
        for i in range(0,40):
            if lBits[i] == "1":
                mHash = mHash ^ sHash[i]
       
        # Check if hash matches
        if mHash != int(lBits[40:48],2):
            False

        # Decode message
        data = dict()
        data['tag']  = int(lBits[8:16],2)
        data['chan'] = int(lBits[16:20],2) + 1
        data['temp'] = ((int(lBits[20:32],2) / 10.0) - 40.0)
        data['hum']  = int(lBits[32:40],2)
        data['hash'] = mHash

        data['tempc'] = (data['temp'] -32.0) * (5.0/9.0)
        #data['source'] = 'f007pf.%.2x.%.2x' % (data['tag'],data['chan'])
        data['source'] = 'f007pf.%.2x' % (data['chan'])

        return Message('temp', source=data['source'], sensor=data['source'], temp=data['tempc'])

if __name__ == "__main__":
    import doctest
    doctest.testmod()

