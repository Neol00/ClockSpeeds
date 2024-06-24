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

import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk
import logging
from log_setup import get_logger
from config_setup import config_manager

class CssManager:
    # Default system CSS to ensure consistent look
    CSS_SYSTEM = """
        * {
            font-family: 'System-ui';
            font-size: 10pt;
        }

        notebook tab:hover,
        notebook tab:active, 
        notebook tab:checked {
            border-radius: 4px;
        }

        .tab-label {
            font-size: 13pt;
            padding: 5px 85px;
        }

        .settings-tab-label {
            font-size: 11pt;
            padding: 5px 7px;
        }

        .about-tab-label {
            font-size: 11pt;
            padding: 5px 70px;
        }

        scrollbar slider {
            border-radius: 8px;
        }

        menuitem {
            padding: 8px 12px;
            border-radius: 4px;
        }

        menuitem:hover * {
            border-radius: 4px;
        }

        label {
            padding: 2px;
        }

        entry {
            padding: 4px;
            border-radius: 4px;
        }

        scale {
            min-width: 320px;
        }

        scale slider {
            border-radius: 1000px;
        }

        .button {
            padding: 2px 15px;
            border-radius: 4px;
        }

        checkbutton {
            padding: 2px;
            border-radius: 4px;
        }

        checkbutton label:hover {
            color: grey;
        }

        combobox * {
            border-radius: 8px;
        }
    """

    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        # Create a CSS provider for applying styles
        self.css_provider = Gtk.CssProvider()

        # Get the list of valid CSS themes installed on the system
        self.valid_css_themes = self.get_installed_gtk_css()

        # Apply the default system CSS on startup
        self.apply_css(self.CSS_SYSTEM)

    def apply_css(self, css_data):
        # Apply the provided CSS data to the application
        self.css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def apply_theme(self, css_name=None):
        # Apply the specified theme and ensure system CSS is always applied
        try:
            if css_name is None:
                css_name = self.load_css_config()
            self.logger.info(f"Applying CSS: {css_name}")
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-theme-name", css_name)
            self.apply_css(self.CSS_SYSTEM)
        except Exception as e:
            self.logger.error(f"Error applying CSS: {e}")

    def is_valid_css(self, css_name):
        # Check if the provided CSS name is a valid installed theme
        return css_name in self.valid_css_themes

    def save_css_config(self, css_name):
        # Save the selected CSS theme to the configuration file
        try:
            if self.is_valid_css(css_name):
                config_manager.set_setting('CSS', 'selected_css', css_name)
            else:
                self.logger.info(f"Attempted to save invalid CSS theme: {css_name}")
        except Exception as e:
            self.logger.error(f"Error saving CSS configuration: {e}")

    def load_css_config(self):
        # Load the selected CSS theme from the configuration file
        try:
            css_name = config_manager.get_setting('CSS', 'selected_css', default=None)
            if not self.is_valid_css(css_name):
                self.logger.info(f"Attempted to load invalid CSS theme: {css_name}")
            return css_name
        except Exception as e:
            self.logger.error(f"Error loading CSS configuration: {e}")

    def get_installed_gtk_css(self):
        # Get a list of installed GTK themes by searching the theme directories
        try:
            theme_dirs = ['/usr/share/themes', os.path.expanduser('~/.themes')]
            themes = set()
            
            for theme_dir in theme_dirs:
                if os.path.isdir(theme_dir):
                    for theme in os.listdir(theme_dir):
                        themes.add(theme)

            return sorted(themes)
        except Exception as e:
            self.logger.error(f"Error fetching installed GTK themes: {e}")
            return []

# Create an instance of the CssManager
css_manager = CssManager()
