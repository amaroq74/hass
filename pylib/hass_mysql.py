
# Add relative path
import sys
sys.path.append('/amaroq/hass/pylib')

import hass_secrets as secrets

import MySQLdb
from contextlib import closing

__version__ = "1.0"

class Mysql(object):
    """Class to handle mysql updates and queries."""

    def __init__(self, service):
        """ Create mysql class.  """

        self._service = service
        self._conn    = 0
        self._db      = None

    # Clean log
    def deleteByInterval (self, table, interval) :
        with closing(MySQLdb.connect(host=secrets.mysql_host,
                                     user=secrets.mysql_user,
                                     passwd=secrets.mysql_pass,
                                     db=secrets.mysql_dbase,
                                     port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("delete from " + table + " where time < (now() - interval " + interval + ")")

    # Get most recent sensor basic value
    def getSensorRecent (self, sensor, typ ) :
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where time >= (now()-interval 1 hour) " +
                           "and device = '" + sensor + "' and type = '" + typ + "' order by time desc limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor basic value from 1 hour before
    def getSensorHour (self, sensor, typ ) :
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where time >= (now()-interval 1 hour) " +
                           "and device = '" + sensor + "' and type = '" + typ + "' order by time limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor basic value from start of day
    def getSensorDay (self, sensor, typ ) :
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where time >= current_date() " +
                           "and device = '" + sensor + "' and type = '" + typ + "' order by time limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    def getSensorDayStats (self, sensor, typ):
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            query  = "select device, type, avg(sensor_log.current) as avg, "
            query += "max(sensor_log.current) as max, min(sensor_log.current) as min "
            query += "from sensor_log where sensor_log.time >= (now() - interval 24 hour) "
            query += "group by sensor_log.device, sensor_log.type"

            cursor.execute(query)
            return cursor.fetchall()

    # Get sensor basic value from defined hours before
    def getSensorHours (self, sensor, typ, hours):
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current from sensor_log where device = '" + sensor + "' and type = '" + typ + 
                           "' and time <= (now() - interval " + str(hours) + " hour) order by time desc limit 1")
            row = cursor.fetchone()

            if row is None: return None
            else: return row["current"]

    # Get sensor array for given previous hours
    def getSensorArrayHours (self, sensor, typ, hours) :
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("select current,time,UNIX_TIMESTAMP(time) as utime from sensor_log where device = '" + sensor + "' and type = '" + typ + 
                           "' and time >= (now() - interval " + str(hours) + " hour) order by time")
            return cursor.fetchall()

    # Set sensor
    def setSensor(self, device, typ, current, units):
        with closing(MySQLdb.connect(host=secrets.mysql_host,user=secrets.mysql_user,passwd=secrets.mysql_pass,db=secrets.mysql_dbase,port=secrets.mysql_port)) as conn:
            conn.autocommit(True)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("insert into sensor_log (type,device,current,units,time) values " +
                           "('" + typ + "','" + device + "','" + str(current) + "','" + units + "',now(3))")

