from datetime import timedelta
import logging

import requests
import voluptuous as vol

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval


# Setting log
_LOGGER = logging.getLogger('iliad_account_init')
_LOGGER.setLevel(logging.DEBUG)

# This is needed, it impact on the name to be called in configurations.yaml
# Ref: https://developers.home-assistant.io/docs/en/creating_integration_manifest.html
DOMAIN = 'iliad_account'

DEFAULT_SCAN_INTERVAL = timedelta(seconds=900)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,

        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    })
}, extra=vol.ALLOW_EXTRA)


# ----------------------------------------------------------------------------------------------------------------------
#
# ASYNC SETUP
#
# ----------------------------------------------------------------------------------------------------------------------


async def async_setup(hass, config):

    _LOGGER.debug('async_setup() >>> STARTED')

    # create the Iliad Platform object
    hass.data[DOMAIN] = IliadPlatform(hass, config)

    _LOGGER.debug('async_setup() <<< TERMINATED')

    return True

# ----------------------------------------------------------------------------------------------------------------------
#
# ILIAD PLATFORM
#
# ----------------------------------------------------------------------------------------------------------------------

class IliadPlatform:

    def __init__(self, hass, config):

        self._hass = hass
        self._config = config

        self._username = config[DOMAIN][CONF_USERNAME]
        self._password = config[DOMAIN][CONF_PASSWORD]
        self.update_status_interval = config[DOMAIN][CONF_SCAN_INTERVAL]

        # login
        self.login()

        # first update
        #hass.async_create_task(self.async_update_plugs())

        # starting timers
        #hass.async_create_task(self.async_start_timer())

    async def async_start_timer(self):

        # This is used to update the Meross Devices status periodically
        _LOGGER.info('Meross devices status will be updated each ' + str(self.update_status_interval))
        async_track_time_interval(self._hass,
                                  self.async_update_plugs,
                                  self.update_status_interval)

        return True

    def login(self):
        # login url
        url = 'https://www.iliad.it/account/'
        # set POST https params
        params = {'login-ident': self._username, 'login-pwd': self._password}
        # get response to POST request
        response = requests.post(url, params)
        # get html
        html = response.content.decode("utf-8")
        _LOGGER.debug(type(html))
        # look for credits
        needle = "GB</span> /"
        # find needle
        index = html.find(needle)
        _LOGGER.debug('index: ' + str(index))
        # log data
        _LOGGER.debug('text: "' + html[index: 2] + '"')
        return True

