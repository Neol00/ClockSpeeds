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

import logging
from log_setup import get_logger
from config_setup import config_manager

class GlobalState:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.SPACING = 5
        self.SCALE_MIN = int(config_manager.get_setting('Settings', 'SCALE_MIN', 1))
        self.SCALE_MAX = int(config_manager.get_setting('Settings', 'SCALE_MAX', 6000))
        self.TDP_SCALE_MIN = int(config_manager.get_setting('Settings', 'TDP_SCALE_MIN', 1))
        self.TDP_SCALE_MAX = int(config_manager.get_setting('Settings', 'TDP_SCALE_MAX', 400))
        self.y_offset = 0

        self.unique_governors = set()
        self.boost_enabled = None
        self.disable_scale_limits = False
        self.sync_scales = False
        self.max_tdp_value = None

        self.save_settings()

    def save_settings(self):
        try:
            if not config_manager.get_setting('Settings', 'SCALE_MIN'):
                config_manager.set_setting('Settings', 'SCALE_MIN', str(self.SCALE_MIN))
            if not config_manager.get_setting('Settings', 'SCALE_MAX'):
                config_manager.set_setting('Settings', 'SCALE_MAX', str(self.SCALE_MAX))
            if not config_manager.get_setting('Settings', 'TDP_SCALE_MIN'):
                config_manager.set_setting('Settings', 'TDP_SCALE_MIN', str(self.TDP_SCALE_MIN))
            if not config_manager.get_setting('Settings', 'TDP_SCALE_MAX'):
                config_manager.set_setting('Settings', 'TDP_SCALE_MAX', str(self.TDP_SCALE_MAX))
            if not config_manager.get_setting('Settings', 'LoggingLevel'):
                config_manager.set_setting('Settings', 'LoggingLevel', 'WARNING')

            self.logger.info("Settings saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")

# Create an instance of GlobalState
global_state = GlobalState()

class GuiComponents:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.components = {}

    def add_widget(self, name, widget):
        self.components[name] = widget
        self.logger.info(f"Added widget: {name}")

    def __getitem__(self, key):
        return self.components.get(key)

    def __setitem__(self, key, value):
        self.components[key] = value
        self.logger.info(f"Set widget: {key}")

    def __delitem__(self, key):
        if key in self.components:
            del self.components[key]
            self.logger.info(f"Deleted widget: {key}")

# Create an instance of GuiComponents
gui_components = GuiComponents()
