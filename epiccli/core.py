# BSD 3 - Clause License

# Copyright(c) 2020, Zenotech
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and / or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#         SERVICES
#         LOSS OF USE, DATA, OR PROFITS
#         OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import errno
from configparser import ConfigParser

from .exceptions import ConfigurationException, CommandError, ResponseError


class EpicConfig(object):
    """ Class for loading and checking CLI configuration """

    def __init__(self, epic_url=None, epic_token=None, config_file=None, config_section="default"):
        super(EpicConfig, self).__init__()
        self._load_config(epic_url, epic_token, config_file, config_section)
        self._check_config()

    def _load_config(self, epic_url=None, epic_token=None, config_file=None, config_section='default'):
        """
        Load client config, order of precedence = args > env > config_file
        """
        self.EPIC_API_URL = None
        self.EPIC_TOKEN = None
        if config_file is not None:
            self._load_config_file(config_file, config_section)
            self._config_file = config_file
        self.EPIC_API_URL = os.environ.get("EPIC_API_ENDPOINT", self.EPIC_API_URL)
        self.EPIC_TOKEN = os.environ.get("EPIC_TOKEN", self.EPIC_TOKEN)
        if epic_url is not None:
            self.EPIC_API_URL = epic_url
        if epic_token is not None:
            self.EPIC_TOKEN = epic_token

    def _check_config(self):
        if self.EPIC_API_URL is None:
            raise ConfigurationException(
                "Missing EPIC URL, set EPIC_API_URL or supply a configuration file"
            )
        elif self.EPIC_TOKEN is None:
            raise ConfigurationException(
                "Missing EPIC URL, set EPIC_TOKEN or supply a configuration file"
            )

    def _load_config_file(self, file, config_section):
        parser = ConfigParser(allow_no_value=True)
        if os.path.isfile(file):
            parser.read(file)
            if parser.has_section(config_section):
                self.EPIC_API_URL = parser.get(config_section, "url")
                self.EPIC_TOKEN = parser.get(config_section, "token")
            else:
                raise ConfigurationException(f"Invalid EPIC configuration, cannot find section {config_section}")
        else:
            raise ConfigurationException(f"Invalid EPIC configuration file {file}")
