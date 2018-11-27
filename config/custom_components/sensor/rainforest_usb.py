
from homeassistant.components.rainforest_usb import RainforestSensor

SRC_DOMAIN="rainforest_usb"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    cfg = hass[SRC_DOMAIN]
    lst = []

    for resource in config[CONF_RESOURCES]:
        channel = resource.lower()

        entity_id = '{}_{}'.format(cfg['name'].lower(),channel)
        name      = '{} {}'.format(cfg['name'],channel)

        sen = RainforestSensor(channel, entity_id, name)
        lst.append(sen)
        cfg['channels'][channel] = sen

    async_add_entities(lst)

