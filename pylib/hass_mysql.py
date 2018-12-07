
# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import hass_secrets as secrets

import MySQLdb
from contextlib import closing

__version__ = "1.0"

class Mysql(object):
    """Class to handle mysql updates and queries."""

    def __init__(self, service, log = None):
        """ Create mysql class.  """

        self._service = service
        self._conn    = 0
        self._db      = None
        self._log     = log

    def mysqlOpen(self):
        db = MySQLdb.connect(host=secrets.mysql_host,
                             user=secrets.mysql_user,
                             passwd=secrets.mysql_pass,
                             db=secrets.mysql_dbase,
                             port=secrets.mysql_port)
        db.autocommit(True)
        return db

    # Clean log
    def deleteByInterval (self, table, interval) :
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("delete from " + table + " where time < (now() - interval " + interval + ")")

    # Get sensor basic value from 1 hour before
    def getSensorHour (self, sensor, typ ) :
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where time >= (now()-interval 1 hour) " +
                           "and device = '" + sensor + "' and type = '" + typ + "' order by time limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor basic value from start of day
    def getSensorDay (self, sensor, typ ) :
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where time >= current_date() " +
                           "and device = '" + sensor + "' and type = '" + typ + "' order by time limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor basic value from defined hours before
    def getSensorHours (self, sensor, typ, hours):
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where device = '" + sensor + "' and type = '" + typ + 
                           "' and time <= (now() - interval " + str(hours) + " hour) order by time desc limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor array for given previous hours
    def getSensorArrayHours (self, device, typ, hours) :
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current,time,UNIX_TIMESTAMP(time) as utime from sensor_log where device = '" + device + "' and type = '" + typ + 
                           "' and time >= (now() - interval " + str(hours) + " hour) order by time")
            return cursor.fetchall()

    # Set sensor
    def setSensor(self, device, typ, current, units):
        with closing(self.mysqlOpen()) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("insert into sensor_log (type,device,current,units,time) values " +
                           "('" + typ + "','" + device + "','" + str(current) + "','" + units + "',now(3))")


    def sensorSparse15min(self):
        with closing(self.mysqlOpen()) as conn:
            startTime = time.time()

            cursor1 = conn.cursor(MySQLdb.cursors.DictCursor)  
            cursor2 = conn.cursor(MySQLdb.cursors.DictCursor)  
            cursor3 = conn.cursor(MySQLdb.cursors.DictCursor)  

            # Limit to 10 minutes
            while (time.time() - startTime) < 600:

               # Get first non sparsed record
               cursor1.execute("select year(time) as year, month(time) as month, day(time) as day, " +
                               "hour(time) as hour, minute(time) as minute, time, type, device, id " + 
                               "from sensor_log where time < (now()-interval 20 minute) and sparsed = '0' limit 1")
               row = cursor1.fetchone()
               if row == None:
                  break

               year   = row["year"]
               month  = row["month"]
               day    = row["day"]
               hour   = row["hour"]
               min_st = int(row["minute"] / 15) * 15
               type   = row["type"]
               device = row["device"]

               start_time = '%i-%i-%i %i:%i:00' % (year,month,day,hour,min_st)

               if self._log is not None:
                   self._log.info("sensorSparse15min: device = %s, type = %s, id=%i, start=%s" % (device,type,row['id'],start_time))

               # Get all of 15-minute period records
               query  = "select id, time, type, device, current, units, sparsed, time(time) as time from sensor_log "
               query += "where type = '{}' ".format(type)
               query += "and device = '{}' ".format(device)
               query += "and time >=  '{}' ".format(start_time)
               query += "and time < ('{}' + interval 15 minute) ".format(start_time)
               query += "order by time asc"
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

                  query = "update sensor_log set sparsed = '1' where id = '{}'".format(id)
                  cursor3.execute(query)

               # Setup query, avoid null fields
               query  = "insert into sensor_log_15min (time, type, device, units, first, last, average, min, max, min_time, max_time) "
               query += "values ('{}-{}-{} {}:{}:00',".format(year,month,day,hour,min_st)
               query += "'{}','{}','{}','{}','{}',".format(type,device,units,first,last)
               query += "'{}','{}','{}','{}','{}')".format((sum/cnt),min,max,min_time,max_time)

               cursor3.execute(query)
               if self._log is not None:
                   self._log.info("sensorsparse15min: " + query)

    def sensorSparseDay(self):
        with closing(self.mysqlOpen()) as conn:
            cursor1 = db.cursor(MySQLdb.cursors.DictCursor)
            cursor2 = db.cursor(MySQLdb.cursors.DictCursor)
            cursor3 = db.cursor(MySQLdb.cursors.DictCursor)

            # Generate data string for start of today
            d = date.today()
            today = d.strftime("%Y-%m-%d 00:00:00")

            while (1):

               # Get first non sparsed record
               query =  "select year(time) as year, month(time) as month, day(time) as day, type, device from sensor_log_15min "
               query += "where time < '{}' and sparsed = '0' limit 1".format(today)

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
               
               if self._log is not None:
                   self._log.info("sensorSparseDay: " + query)

            query = "delete from sensor_log where time < (now() - interval 30 day) and sparsed = '1'"
            if self._log is not None:
               self._log.info("sensorSparseDay: " + query)
            cursor1.execute(query)

