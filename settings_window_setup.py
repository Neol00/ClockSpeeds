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
    def __init__(self, config_manager, logger, global_state, gui_components, widget_factory, settings_applier, cpu_manager, scale_manager):
        # References to instances
        self.config_manager = config_manager
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.settings_applier = settings_applier
        self.cpu_manager = cpu_manager
        self.scale_manager = scale_manager

        # Call methods on startup
        self.setup_main_settings_window()
        self.setup_main_settings_box()
        self.setup_settings_gui()
        self.add_settings_widgets_to_gui_components()

    def setup_main_settings_window(self):
        # Create the settings window
        try:
            self.settings_window = self.widget_factory.create_window("Settings", None, 210, 170)
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

    def setup_settings_gui(self):
        # Setup the settings GUI components directly in the main box
        try:
            # Create a fixed layout container for precise positioning
            settings_fixed = Gtk.Fixed()
            self.main_settings_box.append(settings_fixed)

            # Add some margin around the settings
            settings_fixed.set_margin_start(10)
            settings_fixed.set_margin_end(10)
            settings_fixed.set_margin_top(10)
            settings_fixed.set_margin_bottom(10)

            # Create the Disable Scale Limits checkbutton
            self.disable_scale_limits_checkbutton = self.widget_factory.create_checkbutton(
                settings_fixed, "Disable Scale Limits", self.global_state.disable_scale_limits, self.scale_manager.on_disable_scale_limits_change, x=5, y=10)

            # Create the info button for the Disable Scale Limits checkbutton
            info_button_scale = self.widget_factory.create_info_button(
                settings_fixed, self.scale_info_window, x=160, y=10)

            # Create the MHz to GHz toggle checkbutton
            self.mhz_to_ghz_checkbutton = self.widget_factory.create_checkbutton(
                settings_fixed, "Display GHz", self.global_state.display_ghz, self.on_mhz_to_ghz_toggle, x=5, y=40)

            # Create the info button for the MHz to GHz checkbutton
            info_button_mhz_to_ghz = self.widget_factory.create_info_button(
                settings_fixed, self.mhz_to_ghz_info_window, x=160, y=40)

            # Create the Apply On Boot checkbutton (initially disabled)
            self.apply_on_boot_checkbutton = self.widget_factory.create_checkbutton(
                settings_fixed, "Apply On Boot", None, self.on_apply_on_boot_toggle, x=5, y=70)
            self.apply_on_boot_checkbutton.set_sensitive(False)  # Start disabled, will be enabled by settings applier if appropriate

            # Create the info button for the Apply On Boot checkbutton
            info_button_apply_boot = self.widget_factory.create_info_button(
                settings_fixed, self.apply_boot_info_window, x=160, y=70)

            # Create the Dark Mode toggle checkbutton
            self.dark_mode_checkbutton = self.widget_factory.create_checkbutton(
                settings_fixed, "Dark Mode", self.get_current_theme_preference(), self.on_dark_mode_toggle, x=5, y=100)

            # Create the info button for the Dark Mode checkbutton
            info_button_dark_mode = self.widget_factory.create_info_button(
                settings_fixed, self.dark_mode_info_window, x=160, y=100)

            # Create the update interval label and spinbutton
            interval_label = self.widget_factory.create_label(
                settings_fixed, "Update Interval Seconds:", x=23, y=130)
            interval_spinbutton = self.widget_factory.create_spinbutton(
                settings_fixed, self.cpu_manager.update_interval, 0.1, 20.0, 0.1, 1, 0.1, 1, self.on_interval_changed, x=40, y=155, margin_bottom=10)

            # Adjust window size to fit content properly
            self.settings_window.set_default_size(210, 200)

        except Exception as e:
            self.logger.error(f"Error setting up settings window GUI: {e}")

    def add_settings_widgets_to_gui_components(self):
        # Add the settings widgets to the gui_components dictionary
        try:
            self.gui_components['settings_window'] = self.settings_window
            self.gui_components['disable_scale_limits_checkbutton'] = self.disable_scale_limits_checkbutton
            self.gui_components['apply_on_boot_checkbutton'] = self.apply_on_boot_checkbutton
            self.gui_components['dark_mode_checkbutton'] = self.dark_mode_checkbutton
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
            info_window = self.widget_factory.create_window("Information", self.settings_window, 350, 50)
            info_box = self.widget_factory.create_box(info_window)
            
            # Check if systemd is available to show appropriate message
            if hasattr(self.settings_applier, 'systemd_compatible') and not self.settings_applier.systemd_compatible:
                info_text = ("Apply On Boot is not available on this system.\n\n"
                           "This feature requires systemd, but your system is using\n"
                           "a different init system (such as OpenRC, SysV init, etc.).\n\n"
                           "You will need to manually apply your settings after each reboot.")
            else:
                info_text = ("Enabling this option will apply the settings you have specifically\n"
                           "changed on boot with a systemd service and a complimentary script.\n"
                           "Disabling this option will disable and delete the files.\n\n"
                           "Note: You must first apply settings before this option becomes available.")
            
            info_label = self.widget_factory.create_label(
                info_box,
                info_text,
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
        """Handle Apply On Boot checkbutton toggle with improved error handling"""
        try:
            # Ignore if specifically told to (during programmatic changes)
            if self.global_state.ignore_boot_checkbutton_toggle:
                return
            
            # Check if systemd is compatible before proceeding
            if not self.settings_applier.systemd_compatible:
                self.logger.warning("Apply On Boot toggled but systemd is not compatible")
                # Revert the checkbutton and show explanation
                self.global_state.ignore_boot_checkbutton_toggle = True
                checkbutton.set_active(False)
                self.global_state.ignore_boot_checkbutton_toggle = False
                self.settings_applier.show_systemd_incompatible_dialog()
                return
            
            # Proceed with normal toggle logic
            if checkbutton.get_active():
                self.apply_on_boot_checkbutton.set_sensitive(False)
                self.settings_applier.create_systemd_service()
            else:
                self.apply_on_boot_checkbutton.set_sensitive(False)
                self.settings_applier.remove_systemd_service()
                
        except Exception as e:
            self.logger.error(f"Error in on_apply_on_boot_toggle: {e}")
            # Ensure checkbutton is reset on any error
            self.global_state.ignore_boot_checkbutton_toggle = True
            checkbutton.set_active(False)
            self.apply_on_boot_checkbutton.set_sensitive(False)
            self.global_state.ignore_boot_checkbutton_toggle = False

    def on_interval_changed(self, spinbutton):
        # Update the interval value when the spinbutton value changes
        new_interval = round(spinbutton.get_value(), 1)
        self.cpu_manager.set_update_interval(new_interval)

    def get_current_theme_preference(self):
        # Get the current theme preference from config
        try:
            dark_mode_setting = self.config_manager.get_setting('Settings', 'dark_mode', 'False')
            return dark_mode_setting == 'True'
        except Exception as e:
            self.logger.error(f"Error getting dark mode setting: {e}")
            return False

    def on_dark_mode_toggle(self, checkbutton):
        # Toggle between light and dark themes
        try:
            is_dark = checkbutton.get_active()
            
            # Set the theme preference on default settings
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", is_dark)
            
            # Save the preference to config
            self.config_manager.set_setting('Settings', 'dark_mode', str(is_dark))
            
            # Note: Graphs will automatically update on next redraw cycle
            
        except Exception as e:
            self.logger.error(f"Error toggling dark mode: {e}")

    def refresh_all_graphs(self):
        # Force all CPU graphs to redraw with new theme colors
        try:
            if 'cpu_graphs' in self.gui_components:
                for graph in self.gui_components['cpu_graphs'].values():
                    graph.queue_draw()
            
            if 'avg_usage_graph' in self.gui_components:
                self.gui_components['avg_usage_graph'].queue_draw()
                
        except Exception as e:
            self.logger.error(f"Error refreshing graphs: {e}")

    def dark_mode_info_window(self, widget):
        # Show the information dialog for the Dark Mode checkbutton
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Toggle between light and dark theme for the entire application.\n"
                "CPU graphs will automatically adapt to match the selected theme.",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=126, margin_end=126, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing Dark Mode info window: {e}")

    def init_dark_mode_setting(self):
        # Initialize the dark mode setting on startup
        try:
            is_dark = self.get_current_theme_preference()
            
            # Apply the theme preference to the default settings
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", is_dark)
            
            # Update the checkbutton state
            self.dark_mode_checkbutton.set_active(is_dark)
            
        except Exception as e:
            self.logger.error(f"Error initializing dark mode setting: {e}")