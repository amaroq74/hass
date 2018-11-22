
def windDegToCompass ( deg ):
    if   deg < 11.25  : wDir = "N"
    elif deg < 33.75  : wDir = "NNE"
    elif deg < 56.25  : wDir = "NE"
    elif deg < 78.75  : wDir = "ENE"
    elif deg < 101.25 : wDir = "E"
    elif deg < 123.75 : wDir = "ESE"
    elif deg < 146.25 : wDir = "SE"
    elif deg < 168.75 : wDir = "SSE"
    elif deg < 191.25 : wDir = "S"
    elif deg < 213.75 : wDir = "SSW"
    elif deg < 236.25 : wDir = "SW"
    elif deg < 258.75 : wDir = "WSW"
    elif deg < 281.25 : wDir = "W"
    elif deg < 303.75 : wDir = "WNW"
    elif deg < 326.25 : wDir = "NW"
    elif deg < 348.75 : wDir = "NNW"
    else: wDir = "N"

    return wDir

def tempCelToFar ( cel ) :
    return ((cel * 9.0/5.0) + 32.0)

def tempFarToCel ( far ) :
    return((far - 32.0) * (5.0/9.0))

def speedMpsToMph ( mps ):
    return (mps * 2.2369362920544 )

def speedMphToMps ( mph ):
    return (mph / 2.2369362920544 )

def rainMmToIn ( mm ) :
    return (mm / 25.4)

def rainInToMm ( inc ) :
    return (inc * 25.4)

def pressureHpaToInhg ( hpa ) :
    return ( hpa / 33.8638 )

def pressureInhgToHpa ( inhg ) :
    return ( inhg * 33.8638 )

def compDewPtCel ( tempC, humidity ):
    return(tempC - ((100.0 - float(humidity))/5.0))

def compDewPtFar ( tempF, humidity ):
    return tempCelToFar(compDewPtCel(tempFarToCel(tempF),humidity))

