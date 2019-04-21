#!/usr/bin/env python3

import sys
sys.path.append('/amaroq/hass/pylib')
import hass_mysql

db = hass_mysql.Mysql("hass-app")
db.deleteByInterval('sensor_log','60 day')

