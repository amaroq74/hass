
import sys
sys.path.append('/amaroq/smarthome/pylib')
from amaroq_home import mysql

from homeassistant.components.climate import ( ClimateDevice,
    STATE_HEAT, STATE_COOL, STATE_FAN_ONLY, STATE_IDLE,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, SUPPORT_AWAY_MODE)
from homeassistant.const import ( STATE_ON, STATE_OFF, ATTR_TEMPERATURE )

SUPPORT_FLAGS = (SUPPORT_OPERATION_MODE | SUPPORT_TARGET_TEMPERATURE | SUPPORT_AWAY_MODE)

# Mysql
db = mysql.Mysql('hass')

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Awesome Light platform."""

    lst = [ {'name' : 'Thermostat',   'group':'House_Heat',    'temp' : 'House',    'min' : 45.0, 'holdEn' : True  },
            {'name' : 'Pool Heat',    'group':'Pool_Heat',     'temp' : 'Pool',     'min' : 32.0, 'holdEn' : True  },
            {'name' : 'Garage Heat',  'group':'Garage_Heat',   'temp' : 'Garage',   'min' : 32.0, 'holdEn' : True  },
            {'name' : 'Chicken Heat', 'group':'Chicken_Light', 'temp' : 'Chickens', 'min' : 32.0, 'holdEn' : False } ]

    # Add devices
    async_add_entities([SmarthomeThermostat(hass, l) for l in lst])

class SmarthomeThermostat(ClimateDevice):
    """Simplified interface to a denson.cc thermostat."""

    def __init__(self, hass, info):
        """Initialize a DCC_Thermostat."""

        self._info  = info
        self._name  = info['name']
        self._mode  = STATE_HEAT
        self._state = STATE_IDLE
        self._units = hass.config.units.temperature_unit

        self._target_temp = db.getVariable(self._info['group'],'setpoint')

        v = db.getSensorCurrent(self._info['temp'],'temp')
        if v is None:
            self._cur_temp = self.CtoF(0)
        else:
            self._cur_temp = self.CtoF(v)

        if self._info['holdEn']:
            self._away = (db.getVariable(self._info['group'],'hold') == 1)
        else:
            self._away = False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS
    
    @property
    def name(self):
        """Return the display name of this thermostat."""
        return self._name

    @property
    def state(self):
        """Return the current dynamic state."""
        return self._state
    
    @property
    def current_operation(self):
        """Return current set operation ie. heat, cool, fan, idle."""
        return self._mode

    @property
    def is_on(self):
        """Return true if on."""
        return self._state != STATE_OFF

    @property
    def operation_list(self):
        return [STATE_HEAT, STATE_OFF]

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._units

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return int(round(self._cur_temp))

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return int(round(self._target_temp))

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._info['min']

    async def async_update(self):
        self._target_temp = db.getVariable(self._info['group'],'setpoint')

        v = db.getSensorCurrent(self._info['temp'],'temp')
        if v is None:
            self._cur_temp = self.CtoF(0)
        else:
            self._cur_temp = self.CtoF(v)

        if self._info['holdEn']:
            self._away = (db.getVariable(self._info['group'],'hold') == 1)
        else:
            self._away = False

        info = db.getDeviceInfo('House_Heat')

        if info is not None and info['status'] == 100:
            self._state = STATE_HEAT
        else:
            self._state = STATE_IDLE

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temp = temperature
        db.setVariable(self._info['group'],'setpoint',self._target_temp)

    async def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        return

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._away

    async def async_turn_away_mode_on(self):
        """Turn away mode on by setting it on away hold indefinitely."""
        if self._info['holdEn']:
            self._away = True
            db.setVariable(self._info['group'],'hold',1)

    async def async_turn_away_mode_off(self):
        """Turn away off."""
        if self._info['holdEn']:
            self._away = False
            db.setVariable(self._info['group'],'hold',0)

    def CtoF(self, C):
        return (float(C)*1.8)+32.0

    def FtoC(self, F):
        return (float(F)-32.0)/1.8

