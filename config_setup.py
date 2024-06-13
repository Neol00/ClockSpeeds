#!/usr/bin/env python

# ClockSpeeds - CPU Monitoring and Control Application for Linux
# Copyright (c) 2024 Noel Ejemyr <noelejemyr@protonmail.com>
#
# ClockSpeeds is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClockSpeeds is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import configparser
from pathlib import Path
import logging

class ConfigManager:
    def __init__(self, config_dir=None, config_file='config.ini'):
        self.logger = logging.getLogger(__name__)
        if config_dir is None:
            config_dir = Path.home() / '.config' / 'ClockSpeeds'
        self.config_dir = Path(config_dir)
        self.config_file_path = self.config_dir / config_file

        # Ensure the configuration directory exists
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create configuration directory: {e}")
            raise

    def load_config(self):
        self.config = configparser.ConfigParser()
        try:
            if not self.config.read(self.config_file_path):
                self.logger.info("No configuration file found, creating a new one.")
                self.save_config()
        except configparser.Error as e:
            self.logger.error(f"Error reading configuration file: {e}")
            raise

    def save_config(self):
        try:
            with self.config_file_path.open('w') as configfile:
                self.config.write(configfile)
            self.logger.info("Configuration saved successfully.")
        except IOError as e:
            self.logger.error(f"IOError while saving configuration: {e}")
            raise

    def get_setting(self, section, option, default=None):
        if not hasattr(self, 'config'):
            self.load_config()
        try:
            return self.config.get(section, option, fallback=default)
        except configparser.Error as e:
            self.logger.error(f"Error getting setting '{option}' from section '{section}': {e}")
            return default

    def set_setting(self, section, option, value):
        if not hasattr(self, 'config'):
            self.load_config()

        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, option, value)
            self.save_config()
        except configparser.Error as e:
            self.logger.error(f"Error setting '{option}' in section '{section}': {e}")
            raise

# Create an instance of ConfigManager
config_manager = ConfigManager()
