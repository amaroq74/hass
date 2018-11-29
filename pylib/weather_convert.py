
def windDegToCompass ( deg ):
    ideg = float(deg)

    if   ideg < 11.25  : wDir = "N"
    elif ideg < 33.75  : wDir = "NNE"
    elif ideg < 56.25  : wDir = "NE"
    elif ideg < 78.75  : wDir = "ENE"
    elif ideg < 101.25 : wDir = "E"
    elif ideg < 123.75 : wDir = "ESE"
    elif ideg < 146.25 : wDir = "SE"
    elif ideg < 168.75 : wDir = "SSE"
    elif ideg < 191.25 : wDir = "S"
    elif ideg < 213.75 : wDir = "SSW"
    elif ideg < 236.25 : wDir = "SW"
    elif ideg < 258.75 : wDir = "WSW"
    elif ideg < 281.25 : wDir = "W"
    elif ideg < 303.75 : wDir = "WNW"
    elif ideg < 326.25 : wDir = "NW"
    elif ideg < 348.75 : wDir = "NNW"
    else: wDir = "N"

    return wDir

def tempCelToFar ( cel ) :
    return ((float(cel) * 9.0/5.0) + 32.0)

def tempFarToCel ( far ) :
    return((float(far) - 32.0) * (5.0/9.0))

def speedMpsToMph ( mps ):
    return (float(mps) * 2.2369362920544 )

def speedMphToMps ( mph ):
    return (float(mph) / 2.2369362920544 )

def rainMmToIn ( mm ) :
    return (float(mm) / 25.4)

def rainInToMm ( inc ) :
    return (float(inc) * 25.4)

def pressureHpaToInhg ( hpa ) :
    return ( float(hpa) / 33.8638 )

def pressureInhgToHpa ( inhg ) :
    return ( float(inhg) * 33.8638 )

def compDewPtCel ( tempC, humidity ):
    return(float(tempC) - ((100.0 - float(humidity))/5.0))

def compDewPtFar ( tempF, humidity ):
    return tempCelToFar(compDewPtCel(tempFarToCel(tempF),humidity))

