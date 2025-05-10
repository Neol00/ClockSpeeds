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
            min-width: 185px;
        }

        scale slider {
            border-radius: 1000px;
        }

        .button {
            padding: 2px 15px;
            border-radius: 4px;
        }

        .infobutton {
            min-height: 20px;
            min-width: 20px;
            padding: 2px 2px;
            border-radius: 4px;
        }
        checkbutton {
            padding: 2px;
            border-radius: 4px;
        }

        checkbutton label:hover {
            color: grey;
        }

        dropdown * {
            border-radius: 8px;
        }

        .small-header {
            font-weight: bold;
            font-size: 12px;
        }

        .medium-header {
            font-weight: bold;
            font-size: 14px;
        }

        .thick-header {
            font-weight: bold;
            font-size: 16px;
        }

        .small-label
        .package_temp_label {
            font-size: 12px;
        }

        .medium-label{
            font-size: 14px;
        }

        .thick-label{
            font-size: 16px;
        }
    """

    def __init__(self, config_manager, logger):
        # References to instances
        self.config_manager = config_manager
        self.logger = logger

        # Create a CSS provider for applying styles
        self.css_provider = Gtk.CssProvider()

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

    def apply_theme(self):
        # Apply basic system CSS while respecting system theme
        try:
            self.logger.info("Applying system CSS")
            self.apply_css(self.CSS_SYSTEM)
        except Exception as e:
            self.logger.error(f"Error applying CSS: {e}")
