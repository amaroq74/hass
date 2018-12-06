
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
    data['ids'] = {}
    data['new'] = None

    def on_message(message):
        source = message['source']
        topic  = message.topic

        for key, newValue in message.values.items():
            if key != 'topic' and key != 'source' and key != 'sensor':
                uid = topic + '_' + key + '_' + source.replace('.','_')

                if uid in data['ids']:
                    data['ids'][uid]._update(newValue)
                elif data['new'] is not None:
                    _LOGGER.warning("Auto adding new entity: {}".format(uid))
                    data['new'](uid,topic,key,newValue)

    data['dev'] = hass_rfxcom.RFXCom(on_message,device=config[DOMAIN].get(CONF_DEVICE))

    def stop_rfxcom(*args, **kwargs):
        data['dev'].stop()

    def rxrun():
        data['dev'].setup()
        data['dev'].run()
        _LOGGER.error("Daemon died")

    threading.Thread(target=rxrun).start()

    hass.data[DOMAIN] = data
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_rfxcom)

    return True

