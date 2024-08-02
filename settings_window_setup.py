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

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

class SettingsWindow:
    def __init__(self, config_manager, logger, global_state, gui_components, widget_factory, settings_applier, cpu_manager, scale_manager, css_manager):
        # References to instances
        self.config_manager = config_manager
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.settings_applier = settings_applier
        self.cpu_manager = cpu_manager
        self.scale_manager = scale_manager
        self.css_manager = css_manager

        # Call methods on startup
        self.setup_main_settings_window()
        self.setup_main_settings_box()
        self.create_settings_notebook()
        self.create_settings_tabs()
        self.setup_settings_gui()
        self.add_settings_widgets_to_gui_components()

    def setup_main_settings_window(self):
        # Create the settings window
        try:
            self.settings_window = self.widget_factory.create_window("Settings", None, 200, 200)
            self.settings_window.connect("close-request", self.close_settings_window)
        except Exception as e:
            self.logger.error(f"Error setting up settings window: {e}")

    def open_settings_window(self, widget=None, data=None):
        # Open the settings window
        try:
            self.settings_window.present()
        except Exception as e:
            self.logger.error(f"Error opening settings window: {e}")

    def close_settings_window(self, *args):
        # Close the settings window
        try:
            self.settings_window.hide()
            return True
        except Exception as e:
            self.logger.error(f"Error closing settings window: {e}")

    def setup_main_settings_box(self):
        # Setup the main settings box
        try:
            self.main_settings_box = self.widget_factory.create_box(self.settings_window)
        except Exception as e:
            self.logger.error(f"Error setting up settings box: {e}")

    def create_settings_notebook(self):
        # Create the settings notebook
        try:
            self.notebook = self.widget_factory.create_notebook(self.main_settings_box)
        except Exception as e:
            self.logger.error(f"Error creating settings notebook: {e}")

    def create_settings_tabs(self):
        # Create the general and theme tabs
        try:
            self.general_tab = self.widget_factory.create_settings_tab(self.notebook, "General")
            self.css_tab = self.widget_factory.create_settings_tab(self.notebook, "Theme")
        except Exception as e:
            self.logger.error(f"Error creating settings tabs: {e}")

    def setup_settings_gui(self):
        # Setup the settings GUI components
        try:
            general_fixed = Gtk.Fixed()
            self.general_tab.append(general_fixed)

            # Create the Disable Scale Limits checkbutton
            self.disable_scale_limits_checkbutton = self.widget_factory.create_checkbutton(
                general_fixed, "Disable Scale Limits", self.global_state.disable_scale_limits, self.scale_manager.on_disable_scale_limits_change, x=5, y=10)

            # Create the info button for the Disable Scale Limits checkbutton
            info_button_scale = self.widget_factory.create_info_button(
                general_fixed, self.scale_info_window, x=160, y=10)
            
            # Create the Sync Scales checkbutton
            self.sync_scales_checkbutton = self.widget_factory.create_checkbutton(
                general_fixed, "Sync All Scales", self.global_state.sync_scales, self.scale_manager.on_sync_scales_change, x=5, y=40)

            # Create the info button for the Sync Scales checkbutton
            info_button_sync = self.widget_factory.create_info_button(
                general_fixed, self.sync_info_window, x=160, y=40)

            # Create the MHz to GHz toggle checkbutton
            self.mhz_to_ghz_checkbutton = self.widget_factory.create_checkbutton(
                general_fixed, "Display GHz", self.global_state.display_ghz, self.on_mhz_to_ghz_toggle, x=5, y=70)

            # Create the info button for the Sync Scales checkbutton
            info_button_mhz_to_ghz = self.widget_factory.create_info_button(
                general_fixed, self.mhz_to_ghz_info_window, x=160, y=70)

            # Create the Apply On Boot checkbutton
            self.apply_on_boot_checkbutton = self.widget_factory.create_checkbutton(
                general_fixed, "Apply On Boot", None, self.on_apply_on_boot_toggle, x=5, y=100)

            # Create the info button for the Apply On Boot checkbutton
            info_button_apply_boot = self.widget_factory.create_info_button(
                general_fixed, self.apply_boot_info_window, x=160, y=100)

            # Create the update interval label and spinbutton
            interval_label = self.widget_factory.create_label(
                general_fixed, "Update Interval Seconds:", x=23, y=130)
            interval_spinbutton = self.widget_factory.create_spinbutton(
                general_fixed, self.cpu_manager.update_interval, 0.1, 20.0, 0.1, 1, 0.1, 1, self.on_interval_changed, x=40, y=155, margin_bottom=10)

            # Create the CSS drop down
            css_values = self.css_manager.get_installed_gtk_css()
            css_dropdown = self.widget_factory.create_dropdown(
                self.css_tab, css_values, self.on_css_change, x=0, y=0, margin_start=10, margin_end=10, margin_top=20, margin_bottom=20, hexpand=True, vexpand=True)

            # Set the active CSS theme
            saved_css = self.css_manager.load_css_config()
            if saved_css in css_values:
                active_index = css_values.index(saved_css)
                css_dropdown.set_active(active_index)
        except Exception as e:
            self.logger.error(f"Error setting up settings window GUI: {e}")

    def add_settings_widgets_to_gui_components(self):
        # Add the settings widgets to the gui_components dictionary
        try:
            self.gui_components['settings_window'] = self.settings_window
            self.gui_components['disable_scale_limits_checkbutton'] = self.disable_scale_limits_checkbutton
            self.gui_components['sync_scales_checkbutton'] = self.sync_scales_checkbutton
            self.gui_components['apply_on_boot_checkbutton'] = self.apply_on_boot_checkbutton
            self.logger.info("Settings widgets added to gui_components.")
        except Exception as e:
            self.logger.error(f"Error adding settings_window widgets to gui_components: {e}")

    def scale_info_window(self, widget):
        # Show the information dialog for the Disable Scale Limits checkbutton
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Enabling this option allows setting CPU speeds beyond standard limits.\n"
                "Note: values outside your CPU's allowed range may not work as expected.",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=164, margin_end=164, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing Disable Scale Limits info window: {e}")

    def sync_info_window(self, widget):
        # Show the information dialog for the Sync All Scales checkbutton
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Enabling this option will synchronize the minimum and maximum CPU\n"
                "frequency scales across all threads.",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=154, margin_end=154, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing Sync All Scales info window: {e}")

    def mhz_to_ghz_info_window(self, widget):
        # Show the information dialog for the MHz to GHz checkbutton
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Enabling this option will display labels in GHz instead of MHz",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=126, margin_end=126, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing MHz to GHz info window: {e}")

    def apply_boot_info_window(self, widget):
        # Show the information dialog for the Apply On Boot checkbutton
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Enabling this option will apply the settings you have specifically\n"
                "changed on boot with a systemd service and a complimentary script.\n"
                "Disabling this option will disable and delete the files",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=147, margin_end=147, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing Apply On Boot info window: {e}")

    def on_mhz_to_ghz_toggle(self, checkbutton):
        self.global_state.display_ghz = checkbutton.get_active()
        self.cpu_manager.update_clock_speeds()
        self.widget_factory.update_frequency_scale_labels()
        self.config_manager.set_setting('Settings', 'display_ghz', str(self.global_state.display_ghz))

    def init_display_ghz_setting(self):
        display_ghz_setting = self.config_manager.get_setting('Settings', 'display_ghz', 'False')
        self.global_state.display_ghz = display_ghz_setting == 'True'
        self.widget_factory.update_frequency_scale_labels()
        self.mhz_to_ghz_checkbutton.set_active(self.global_state.display_ghz)

    def on_apply_on_boot_toggle(self, checkbutton):
        if self.global_state.ignore_boot_checkbutton_toggle:
            return
        if checkbutton.get_active():
            self.apply_on_boot_checkbutton.set_sensitive(False)
            self.settings_applier.create_systemd_service()
        else:
            self.apply_on_boot_checkbutton.set_sensitive(False)
            self.settings_applier.remove_systemd_service()

    def on_interval_changed(self, spinbutton):
        # Update the interval value when the spinbutton value changes
        new_interval = round(spinbutton.get_value(), 1)
        self.cpu_manager.set_update_interval(new_interval)

    def on_css_change(self, combo):
        # Handle the change of CSS theme from the dropdown
        try:
            model = combo.get_model()
            iter = combo.get_active_iter()

            if iter is not None:
                css = model[iter][0]
                self.css_manager.save_css_config(css)
                self.css_manager.apply_theme(css)
                self.logger.info(f"CSS changed to: {css}")
            else:
                self.logger.info("No css selected.")
        except Exception as e:
            self.logger.error(f"Error changing css: {e}")
