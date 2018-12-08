
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
            cursor1 = conn.cursor(MySQLdb.cursors.DictCursor)
            cursor2 = conn.cursor(MySQLdb.cursors.DictCursor)

            # Compute time
            cursor2.execute("select year(now()) as year, month(now()) as month, day(now()) as day, hour(now()) as hour, minute(now()) as minute, now() as ts")
            curr = cursor2.fetchone()
            min_st = int(curr['minute'] / 15) * 15

            # Log current
            cursor1.execute("insert into sensor_log (type,device,current,units,sparsed,time) values " +
                            "('{}','{}','{}','{}','1','{}')".format(typ,device,current,units,curr['ts']))

            # Attempt to get existing 15min record
            query =  "select * from sensor_log_15min "
            query += "where time = '{}-{}-{} {}:{}:00' ".format(curr['year'],curr['month'],curr['day'],curr['hour'],min_st)
            query += "and type = '{}' and device = '{}'".format(typ,device)
            cursor2.execute(query)
            rec = cursor2.fetchone()
 
            # Update old record
            if rec is not None:
                rec['count'] += 1
                rec['sum'] += current
                rec['average'] = round(rec['sum'] / rec['count'],2)
                rec['last'] = current

                if current > rec['max']:
                    rec['max'] = current
                    rec['max_time'] = curr['ts']

                if current < rec['min']:
                    rec['min'] = current
                    rec['min_time'] = curr['ts']

                query  = "update sensor_log_15min set "
                query += "last = '{}', ".format(current)
                query += "average = '{}', ".format(rec['average'])
                query += "count = '{}', ".format(rec['count'])
                query += "sum = '{}', ".format(rec['sum'])
                query += "min = '{}', ".format(rec['min'])
                query += "max = '{}', ".format(rec['max'])
                query += "min_time = '{}', ".format(rec['min_time'])
                query += "max_time = '{}' ".format(rec['max_time'])
                query += "where id = {}".format(rec['id'])
                cursor1.execute(query)

            # Create new record
            else:
                query  = "insert into sensor_log_15min (time, type, device, units, first, last, average, count, sum, min, max, min_time, max_time,sparsed) "
                query += "values ('{}-{}-{} {}:{}:00',".format(curr['year'],curr['month'],curr['day'],curr['hour'],min_st)
                query += "'{}','{}','{}','{}','{}',".format(typ,device,units,current,current)
                query += "'{}','{}','{}','{}','{}','{}','{}','1')".format(current,1,current,current,current,curr['ts'],curr['ts'])
                cursor1.execute(query)

            # Attempt to get existing day record
            query =  "select * from sensor_log_day "
            query += "where day = '{}-{}-{}' ".format(curr['year'],curr['month'],curr['day'])
            query += "and type = '{}' and device = '{}'".format(typ,device)
            cursor2.execute(query)
            rec = cursor2.fetchone()
 
            # Update old record
            if rec is not None:
                rec['count'] += 1
                rec['sum'] += current
                rec['average'] = round(rec['sum'] / rec['count'],2)
                rec['last'] = current

                if current > rec['max']:
                    rec['max'] = current
                    rec['max_time'] = curr['ts']

                if current < rec['min']:
                    rec['min'] = current
                    rec['min_time'] = curr['ts']

                query  = "update sensor_log_day set "
                query += "last = '{}', ".format(current)
                query += "average = '{}', ".format(rec['average'])
                query += "count = '{}', ".format(rec['count'])
                query += "sum = '{}', ".format(rec['sum'])
                query += "min = '{}', ".format(rec['min'])
                query += "max = '{}', ".format(rec['max'])
                query += "min_time = '{}', ".format(rec['min_time'])
                query += "max_time = '{}' ".format(rec['max_time'])
                query += "where id = {}".format(rec['id'])
                cursor1.execute(query)

            # Create new record
            else:
                query  = "insert into sensor_log_day (day, type, device, units, first, last, average, count, sum, min, max, min_time, max_time) "
                query += "values ('{}-{}-{}',".format(curr['year'],curr['month'],curr['day'])
                query += "'{}','{}','{}','{}','{}',".format(typ,device,units,current,current)
                query += "'{}','{}','{}','{}','{}','{}','{}')".format(current,1,current,current,current,curr['ts'],curr['ts'])
                cursor1.execute(query)

