
import sys
sys.path.append('/amaroq/hass/pylib')

from homeassistant.const import (ATTR_STATE, CONF_DEVICE, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol
import logging
import hass_rfxcom
import threading

DOMAIN="rfxcom_rx"
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICE): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    data = {}
    data['sources'] = {}

    def on_message(message):
        source = message['source']

        if source in data['sources']:
            for value, newVal in message.values.items():
                if value in data['sources'][source]:
                    data['sources'][source][value]._update(newVal)
        else:
            _LOGGER.warning("Got data from unknown source: {}".format(source))

    data['dev'] = hass_rfxcom.RFXCom(on_message,device=config[DOMAIN].get(CONF_DEVICE))

    def rxrun():
        data['dev'].setup()
        data['dev'].run()
        _LOGGER.error("Daemon died")

    threading.Thread(target=rxrun).start()

    hass.data[DOMAIN] = data
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, data['dev'].stop)

    return True

