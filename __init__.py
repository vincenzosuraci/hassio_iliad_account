from datetime import timedelta
import logging
from os import replace

import requests
import voluptuous as vol

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from bs4 import BeautifulSoup

# Setting log
_LOGGER = logging.getLogger('iliad_account_init')
_LOGGER.setLevel(logging.DEBUG)

# This is needed, it impact on the name to be called in configurations.yaml
# Ref: https://developers.home-assistant.io/docs/en/creating_integration_manifest.html
DOMAIN = 'iliad_account'

REQUIREMENTS = ['beautifulsoup4']

OBJECT_ID_CREDIT = 'credit'

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

        self._credit = {
            'voice_seconds': 0,
            'voice_seconds_max': None,
            'sms': 0,
            'sms_max': None,
            'mms': 0,
            'mms_max': None,
            'data_GB': 0,
            'data_GB_max': None,
            'renew': None
        }

        # login and fetch data
        hass.async_create_task(self.async_update_credits())

        # starting timers
        hass.async_create_task(self.async_start_timer())

    async def async_start_timer(self):

        # This is used to update the Meross Devices status periodically
        _LOGGER.info('Iliad credit will be updated each ' + str(self.update_status_interval))
        async_track_time_interval(self._hass,
                                  self.async_update_credits,
                                  self.update_status_interval)

        return True

    def _get_max(self, elem):
        for content in elem.contents:
            content = str(content).strip()
            if content[:1] == '/':
                return content[1:].strip()
        return None

    async def async_update_credits(self, now=None):
        # login url
        url = 'https://www.iliad.it/account/'
        # set POST https params
        params = {'login-ident': self._username, 'login-pwd': self._password}
        # get response to POST request
        response = requests.post(url, params)
        # get http status code
        http_status_code = response.status_code
        # check response is okay
        if http_status_code != 200:
            _LOGGER.error('login page (' + url + ') error: ' + str(http_status_code))
        else:
            # get html in bytes
            content = response.content
            # generate soup object
            soup = BeautifulSoup(content, 'html.parser')
            # end offerta
            divs = soup.findAll("div", {"class": "end_offerta"})
            if len(divs) == 1:
                self._credit['renew'] = divs[0].text.strip()
            # find div tags having class conso__text
            divs = soup.findAll("div", {"class": "conso__text"})
            for div in divs:
                # find span tags having class red
                spans = div.findAll("span", {"class": "red"})
                for span in spans:
                    text = span.text
                    if text[-1:] == 's':
                        # voice seconds
                        self._credit['voice_seconds'] = int(text[:-1])
                        max = self._get_max(div)
                        if max is not None:
                            self._credit['voice_seconds_max'] = int(max[:-1])
                    elif text[-2:] == 'GB':
                        # GB of data
                        GB = text[:-2].replace(',', '.')
                        self._credit['data_GB'] = float(GB)
                        max = self._get_max(div)
                        if max is not None:
                            self._credit['data_GB_max'] = float(max[:-2].replace(',', '.'))
                    elif text[-3:] == 'SMS':
                        # sms
                        self._credit['sms'] = int(text[:-3].strip())
                        max = self._get_max(div)
                        if max is not None:
                            self._credit['sms_max'] = int(max[:-3].strip())
                    elif text[-3:] == 'MMS':
                        # sms
                        self._credit['mms'] = int(text[:-3].strip())
                        max = self._get_max(div)
                        if max is not None:
                            self._credit['mms_max'] = int(max[:-3].strip())

            #_LOGGER.info(self._credit)

            for k, v in self._credit.items():
                self._hass.states.async_set(DOMAIN + "." + OBJECT_ID_CREDIT + "_" + k, v)

            return True
        return False

