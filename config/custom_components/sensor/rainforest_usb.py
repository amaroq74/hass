
from homeassistant.const import (CONF_RESOURCES)
from homeassistant.helpers.entity import Entity
from custom_components.rainforest_usb import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    cfg = hass.data[DOMAIN]
    lst = []

    for resource in config[CONF_RESOURCES]:
        channel = resource.lower()

        entity_id = '{}_{}'.format(cfg['name'].lower(),channel)
        name      = '{} {}'.format(cfg['name'],channel)

        sen = RainforestSensor(channel, entity_id, name)
        lst.append(sen)
        cfg['channels'][channel] = sen

    async_add_entities(lst)


class RainforestSensor(Entity):

    def __init__(self, channel, entity_id, name):
        if channel == 'rate':
            self._units = 'KW'
        elif channel == 'total':
            self._units = 'KWH'
        else:
            self._units = ''

        self._icon  = 'mdi:flash'
        self._value = None
        self._name  = name
        self._id    = entity_id

    @property
    def unique_id(self):
        return self._id

    @property
    def icon(self):
        self._icon

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._value

    @property
    def unit_of_measurement(self):
        return self._units

    def _update(self,value):
        self._value = value
        self.async_update_ha_state()


