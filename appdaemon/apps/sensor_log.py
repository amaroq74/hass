#!/usr/bin/env python3

# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')
import hass_secrets as secrets
import hass_mysql

import MySQLdb
from contextlib import closing

import appdaemon.plugins.hass.hassapi as hass
from homeassistant.const import TEMP_FAHRENHEIT
from datetime import datetime, timedelta
import weather_convert
import time

LogSensors = {  'sensor.rain_total'           : {'type':'count',         'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_day'             : {'type':'count_day',     'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_hour'            : {'type':'count_hour',    'device':'Rain',           'units':'mm',       'conv':weather_convert.rainInToMm},
                'sensor.rain_rate'            : {'type':'count_rate',    'device':'Rain',           'units':'mmph',     'conv':weather_convert.rainInToMm},
                'sensor.wind_direction'       : {'type':'direction',     'device':'Wind',           'units':'deg',      'conv':None},
                'sensor.wind_gust'            : {'type':'speed',         'device':'Wind',           'units':'mps',      'conv':weather_convert.speedMphToMps},
                'sensor.wind_average'         : {'type':'speed_average', 'device':'Wind',           'units':'mps',      'conv':weather_convert.speedMphToMps},
                'sensor.outdoor_temperature'  : {'type':'temp',          'device':'Outdoor',        'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.outdoor_dewpoint'     : {'type':'temp',          'device':'Outdoor_DewPt',  'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.outdoor_humidity'     : {'type':'humidity',      'device':'Outdoor',        'units':'%',        'conv':None},
                'sensor.indoor_temperature'   : {'type':'temp',          'device':'Indoor',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.indoor_humidity'      : {'type':'humidity',      'device':'Indoor',         'units':'%',        'conv':None},
                'sensor.indoor_pressure'      : {'type':'pressure',      'device':'Indoor',         'units':'hpa',      'conv':weather_convert.pressureInhgToHpa},
                'sensor.garage_temperature'   : {'type':'temp',          'device':'Garage',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.garage_humidity'      : {'type':'humidity',      'device':'Garage',         'units':'%',        'conv':None},
                'sensor.shed_temperature'     : {'type':'temp',          'device':'Shed',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.shed_humidity'        : {'type':'humidity',      'device':'Shed',           'units':'%',        'conv':None},
                'sensor.master_temperature'   : {'type':'temp',          'device':'Master',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.master_humidity'      : {'type':'humidity',      'device':'Master',         'units':'%',        'conv':None},
                'sensor.bedr_temperature'     : {'type':'temp',          'device':'BedR',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.bedr_humidity'        : {'type':'humidity',      'device':'BedR',           'units':'%',        'conv':None},
                'sensor.bedta_temperature'    : {'type':'temp',          'device':'BedTA',          'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.bedta_humidity'       : {'type':'humidity',      'device':'BedTA',          'units':'%',        'conv':None},
                'sensor.camper_temperature'   : {'type':'temp',          'device':'Camper',         'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.chickens_temperature' : {'type':'temp',          'device':'Chickens',       'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_temperature'     : {'type':'temp',          'device':'Pool',           'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_solar_in'        : {'type':'temp',          'device':'Pool_Solar_In',  'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.pool_solar_out'       : {'type':'temp',          'device':'Pool_Solar_Out', 'units':'c',        'conv':weather_convert.tempFarToCel},
                'sensor.smartmeter_rate'      : {'type':'current',       'device':'SmartMeter',     'units':'KW',       'conv':None},
                'sensor.smartmeter_total'     : {'type':'total',         'device':'SmartMeter',     'units':'KW_Hours', 'conv':None},
                'sensor.ups_input_voltage'    : {'type':'line_voltage',  'device':'UPS',            'units':'V',        'conv':None},
                'sensor.ups_load'             : {'type':'load',          'device':'UPS',            'units':'%',        'conv':None} }
 

class SensorLog(hass.Hass):

    def initialize(self):
        self._db = hass_mysql.Mysql("hass-app")

        # Log as they come in
        for k,v in LogSensors.items():
            self.listen_state(self.sensor_rx, k)

        # Log envery 5 min
        self.run_every(self.sensor_all, datetime.now() + timedelta(seconds=60), 60*5)

        # 15 min sparese
        self.run_every(self.sparse_15min, datetime.now() + timedelta(seconds=60), 60*15)

        # Run once per day
        #self.run_daily(self.sparse_day,datetime.time(02, 15, 0))

    def sensor_rx(self, entity, attribute, old, new, *args, **kwargs):
        self.log("Got new value for {} = {}".format(entity,new))
        ent = LogSensors[entity]

        if ent['conv'] is not None:
            val = ent['conv'](float(new))
        else:
            val = float(new)

        self._db.setSensor(ent['device'], ent['type'], val, ent['units'])

    def sensor_all(self, *args, **kwargs):
        self.log("Logging all sensors")
        for k,ent in LogSensors.items():
            new = self.get_state(k)

            if new is not None and new != 'unknown':
                if ent['conv'] is not None:
                    val = ent['conv'](float(new))
                else:
                    val = float(new)

                self._db.setSensor(ent['device'], ent['type'], val, ent['units'])

    def sparse_15min(self, *arg, **kwargs):
        startTime = time.time()

        with closing(MySQLdb.connect(host=secrets.mysql_host,
                                     user=secrets.mysql_user,
                                     passwd=secrets.mysql_pass,
                                     db=secrets.mysql_dbase,
                                     port=secrets.mysql_port)) as conn:                                                                                        

            conn.autocommit(True)                                                                                               
            cursor1 = conn.cursor(MySQLdb.cursors.DictCursor)  
            cursor2 = conn.cursor(MySQLdb.cursors.DictCursor)  
            cursor3 = conn.cursor(MySQLdb.cursors.DictCursor)  

            # Limit to 10 minutes
            while (time.time() - startTime) < 600:

               # Get first non sparsed record
               cursor1.execute("select year(time) as year, month(time) as month, day(time) as day, hour(time) as hour, " +
                               "minute(time) as minute, time, type, device, id " + 
                               "from sensor_log where time < (now()-interval 20 minute) and sparsed = '0' limit 1")
               row = cursor1.fetchone()
               if row == None:
                  break

               year   = row["year"]
               month  = row["month"]
               day    = row["day"]
               hour   = row["hour"]
               min_st = (row["minute"] / 15) * 15
               type   = row["type"]
               device = row["device"]

               start_time = '%i-%i-%i %i:%i:00' % (year,month,day,hour,min_st)
               self.log("device = %s, type = %s, id=%i, start=%s" % (device,type,row['id'],start_time))

               # Get all of 15-minute period records
               query  = "select id, time, type, device, current, units, sparsed, time(time) as time from sensor_log where type = '" + str(type) + "' "
               query += "and device = '" + str(device) + "' and time >= '" + start_time + "' "
               query += "and time < ('" + start_time + "' + interval 15 minute) order by time asc"
               cursor2.execute(query)

               new = 1
               while (1):
                  row = cursor2.fetchone()
                  if row == None:
                     break

                  id = row["id"]

                  # Init min/max
                  if new == 1:
                     new      = 0
                     first    = row["current"]
                     last     = row["current"]
                     min      = row["current"]
                     max      = row["current"]
                     units    = row["units"]
                     sum      = 0.0
                     cnt      = 0
                     min_time = row["time"]
                     max_time = row["time"]

                  # Adjust min/max
                  if row["current"] > max:
                     max      = row["current"]
                     max_time = row["time"]
                  if row["current"] < min:
                     min      = row["current"]
                     min_time = row["time"]

                  # Set last
                  last = row["current"]

                  # For average
                  sum = sum + row["current"]
                  cnt = cnt + 1

                  query = "update sensor_log set sparsed = '1' where id = '" + str(id) + "'"
                  #self.log("Query: " + query)
                  cursor3.execute(query)

               # Setup query, avoid null fields
               query  = "insert into sensor_log_15min (time, type, device, units, first, last, average, min, max, min_time, max_time) "
               query += "values ('" + str(year) + "-" + str(month) + "-" + str(day) + " " + str(hour) + ":" + str(min_st) + ":00','" + str(type) + "','" + str(device)
               query += "','" + str(units) + "','" + str(first) + "','" + str(last) + "','" + str(sum/cnt) + "','" + str(min) + "','" + str(max) + "','" + str(min_time)
               query += "','" + str(max_time) + "')"
               cursor3.execute(query)
               self.log("Query: " + query)


    def sparse_day(self, *args, **kwargs):
        startTime = time.time()

        with closing(MySQLdb.connect(host=secrets.mysql_host,
                                     user=secrets.mysql_user,
                                     passwd=secrets.mysql_pass,
                                     db=secrets.mysql_dbase,
                                     port=secrets.mysql_port)) as conn:                                                                                        

            cursor1 = db.cursor(MySQLdb.cursors.DictCursor)
            cursor2 = db.cursor(MySQLdb.cursors.DictCursor)
            cursor3 = db.cursor(MySQLdb.cursors.DictCursor)

            # Generate data string for start of today
            d = date.today()
            today = d.strftime("%Y-%m-%d 00:00:00")

            while (1):

               # Get first non sparsed record
               query =  "select year(time) as year, month(time) as month, day(time) as day, type, device from sensor_log_15min "
               query += "where time < '" + str(today) + "' and sparsed = '0' limit 1"

               cursor1.execute(query)
               row = cursor1.fetchone()
               if row == None:
                  break

               year   = row["year"]
               month  = row["month"]
               day    = row["day"]
               type   = row["type"]
               device = row["device"]

               # Get all of day period records
               query  = "select id, time, type, device, units, first, last, average, min, max, min_time, max_time, sparsed "
               query += "from sensor_log_15min where type = '" + str(type) + "' and device = '" + str(device) + "' "
               query += "and time >= '" + str(year) + "-" + str(month) + "-" + str(day) + " 00:00:00' "
               query += "and time <= '" + str(year) + "-" + str(month) + "-" + str(day) + " 23:59:59' order by time asc"
               cursor2.execute(query)

               new = 1
               while (1):
                  row = cursor2.fetchone()
                  if row == None:
                     break

                  id = row["id"]

                  # Init min/max
                  if new == 1:
                     new = 0
                     units    = row["units"]
                     first    = row["first"]
                     last     = row["last"]
                     avg      = row["average"]
                     min      = row["min"]
                     max      = row["max"]
                     min_time = row["min_time"]
                     max_time = row["max_time"]
                     sum      = 0.0
                     cnt      = 0

                  # Adjust min/max
                  if row["max"] > max:
                     max      = row["max"]
                     max_time = row["max_time"]
                  if row["min"] < min:
                     min      = row["min"]
                     min_time = row["min_time"]

                  # Set last
                  last = row["last"]

                  # For average
                  sum = sum + row["average"]
                  cnt = cnt + 1

                  query = "update sensor_log_15min set sparsed = '1' where id = '" + str(id) + "'"
                  cursor3.execute(query)

               # Setup query, avoid null fields
               query  = "insert into sensor_log_day (day, type, device, units, first, last, average, min, max, min_time, max_time)"
               query += "values ('" + str(year) + "-" + str(month) + "-" + str(day) + "','" + str(type) + "','" + str(device) 
               query += "','" + str(units) + "','" + str(first) + "','" + str(last) + "','" + str(sum/cnt) + "','" + str(min)
               query += "','" + str(max) + "','" + str(min_time) + "','" + str(max_time) + "')"
               cursor3.execute(query)
               self.log("Query: " + query)

            query = "delete from sensor_log where time < (now() - interval 30 day) and sparsed = '1'"
            self.log("Query: " + query)
            cursor1.execute(query)


