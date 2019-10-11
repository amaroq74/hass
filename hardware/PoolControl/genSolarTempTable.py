
from collections import OrderedDict
import operator

# Temperature vs resistance table
PoolSolarTableRaw = { 185: 150,    208: 145,    234: 140,    264: 135,    300: 130,
                      341: 125,    389: 120,    438: 116,    444: 115,    472: 113,
                      510: 110,    552: 107,    587: 105,    596: 104,    646: 102,
                      679: 100,    701: 99,     761: 96,     787: 95,     827: 93,
                      900: 91,     916: 90,     980: 88,     1071: 85,    1168: 82,
                      1256: 80,    1278: 79,    1400: 77,    1480: 75,    1535: 74,
                      1686: 71,    1752: 70,    1854: 68,    2041: 66,    2083: 65,
                      2251: 63,    2487: 60,    2750: 57,    2985: 55,    3047: 54,
                      3381: 52,    3602: 50,    3757: 49,    4182: 46,    4367: 45,
                      4663: 43,    5209: 41,    5326: 40,    5826: 38,    6530: 35,
                      7331: 32,    8056: 30,    8250: 29,    9298: 27,    10000: 25,
                      10500: 24,   11880: 21,   12500: 20,   13480: 18,   15310: 16,
                      15700: 15,   17440: 13,   19900: 10,   22760: 7,    25400: 5,
                      26100: 5,    30000: 2,    32600: 0,    34560: -1,   39910: -4,
                      42300: -5,   46230: -7,   53640: -9,   55300: -10,  62480: -12,
                      72910: -15,  85350: -18,  97000: -20,  100200: -21, 118000: -23,
                      130300: -25, 139300: -26, 165100: -29, 176800: -30, 196300: -32,
                      234100: -34, 242500: -35, 280100: -37, 336200: -40, 471500: -45,
                      669500: -50 }

PoolSolarTable = OrderedDict(sorted(PoolSolarTableRaw.items(), key=operator.itemgetter(0)))

with open ('SolarTemps.h','w') as f:
    f.write('\n\n')
    f.write('float SolarTempTable[] = {')

    for i in range(1024):
        volt = (float(i) / 1024.0) * 5.0
        res  = (volt * 10000.0) / (5.0 - volt)

        resAbove = None
        resBelow = None

        for resCmp in PoolSolarTable:
            tempVal = PoolSolarTable[resCmp]
            if resCmp > res:
                resAbove  = resCmp
                tempAbove = tempVal
                break
            else:
                resBelow  = resCmp
                tempBelow = tempVal
     
        if resAbove is not None and resBelow is not None:
            slope = (float(tempAbove)-float(tempBelow)) / (float(resAbove) - float(resBelow))
            temp = tempBelow + ((res - resBelow) * slope)
        else:
            temp = 0.0

        f.write('{:0.2f}'.format(temp))

        if i != 1023:
            if (i != 0) and (((i+1) % 16) == 0):
                f.write(',\n')
                f.write('                         ')

            else:
                f.write(', ')

    f.write('};\n\n')

