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
gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk
import logging
from log_setup import get_logger
from shared import global_state, gui_components
from create_widgets import widget_factory
from cpu_management import cpu_manager
from css_setup import css_manager
from scale_management import scale_manager
from ryzen_smu_installer import ryzen_smu_installer

class SettingsWindow:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        # Create the settings window
        self.settings_window = Gtk.Window(title="Settings")
        self.settings_window.set_default_size(200, 200)
        self.settings_window.set_resizable(False)
        self.settings_window.connect("delete-event", self.close_settings_window)

        # Call methods on startup
        self.setup_main_settings_box()
        self.create_settings_notebook()
        self.create_settings_tabs()
        self.setup_settings_gui()
        self.add_settings_widgets_to_gui_components()
        self.update_enhanced_control_checkbutton()

    def setup_main_settings_box(self):
        # Setup the main settings box
        try:
            self.main_settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=global_state.SPACING)
            self.settings_window.add(self.main_settings_box)
        except Exception as e:
            self.logger.error(f"Error setting up main settings box: {e}")

    def create_settings_notebook(self):
        # Create the settings notebook
        try:
            self.notebook = widget_factory.create_notebook(self.main_settings_box)
        except Exception as e:
            self.logger.error(f"Error creating settings notebook: {e}")

    def create_settings_tabs(self):
        # Create the general and theme tabs
        try:
            self.general_tab = widget_factory.create_settings_tab(self.notebook, "General")
            self.css_tab = widget_factory.create_settings_tab(self.notebook, "Theme")
        except Exception as e:
            self.logger.error(f"Error creating settings tabs: {e}")

    def setup_settings_gui(self):
        # Setup the settings GUI components
        try:
            self.general_fixed = Gtk.Fixed()
            self.general_tab.add(self.general_fixed)

            # Create the disable scale limits checkbutton
            self.disable_scale_limits_checkbutton = widget_factory.create_checkbutton(
                self.general_fixed, "Disable Scale Limits", global_state.disable_scale_limits, scale_manager.on_disable_scale_limits_change, x=5, y=10)

            # Create the info button for the disable scale limits checkbutton
            info_button_scale = widget_factory.create_info_button(
                self.general_fixed, self.show_scale_info_dialog, x=150, y=10)
            
            # Create the sync scales checkbutton
            self.sync_scales_checkbutton = widget_factory.create_checkbutton(
                self.general_fixed, "Sync All Scales", global_state.sync_scales, scale_manager.on_sync_scales_change, x=5, y=40)

            # Create the info button for the sync scales checkbutton
            info_button_sync = widget_factory.create_info_button(
                self.general_fixed, self.show_sync_info_dialog, x=150, y=40)

            # Create the enhanced control checkbutton
            is_installed = ryzen_smu_installer.is_ryzen_smu_installed()
            self.enhanced_control_checkbutton = widget_factory.create_checkbutton(
                self.general_fixed, "Enhanced Ryzen Control", is_installed, self.show_enhanced_control_warning_dialog, x=5, y=70)
            self.enhanced_control_checkbutton.set_sensitive(not is_installed)

            # Create the update interval label and spinbutton
            interval_label = widget_factory.create_label(
                self.general_fixed, "Update Interval Seconds:", x=20, y=100)

            interval_spinbutton = widget_factory.create_spinbutton(
                self.general_fixed, cpu_manager.update_interval, 0.1, 20.0, 0.1, 1, 0.1, 1, self.on_interval_changed, x=45, y=125)

            # Create the CSS combobox
            css_values = css_manager.get_installed_gtk_css()
            self.css_combobox = widget_factory.create_combobox(
                self.css_tab, css_values, self.on_css_change, x=0, y=0)

            # Set the active CSS theme
            saved_css = css_manager.load_css_config()
            if saved_css in css_values:
                active_index = css_values.index(saved_css)
                self.css_combobox.set_active(active_index)
        except Exception as e:
            self.logger.error(f"Error setting up settings window GUI: {e}")

    def open_settings_window(self, widget=None, data=None):
        # Open the settings window
        try:
            if not self.settings_window.get_visible():
                self.settings_window.show_all()
            else:
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

    def add_settings_widgets_to_gui_components(self):
        # Add the settings widgets to the GUI components dictionary
        try:
            gui_components['disable_scale_limits_checkbutton'] = self.disable_scale_limits_checkbutton
            gui_components['sync_scales_checkbutton'] = self.sync_scales_checkbutton
            gui_components['enhanced_control_checkbutton'] = self.enhanced_control_checkbutton

            self.logger.info("Settings widgets added to gui_components.")
        except Exception as e:
            self.logger.error(f"Error adding settings widget to gui_components: {e}")

    def show_scale_info_dialog(self, widget):
        # Show the information dialog for the disable scale limits checkbutton
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self.settings_window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Disable Scale Limits",
            )
            dialog.format_secondary_text(
                "Enabling this option allows setting CPU speeds beyond standard limits. Note: values outside your CPU's allowed range may not work as expected."
            )
            dialog.run()
            dialog.destroy()
        except Exception as e:
            self.logger.error(f"Error showing scale info dialog: {e}")

    def show_sync_info_dialog(self, widget):
        # Show the information dialog for the sync scales checkbutton
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self.settings_window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Sync All Scales",
            )
            dialog.format_secondary_text(
                "Enabling this option will synchronize the CPU scales across all threads."
            )
            dialog.run()
            dialog.destroy()
        except Exception as e:
            self.logger.error(f"Error showing sync info dialog: {e}")

    def on_interval_changed(self, spinbutton):
        # Update the interval value when the spinbutton value changes
        new_interval = round(spinbutton.get_value(), 1)
        cpu_manager.set_update_interval(new_interval)

    def on_css_change(self, combo):
        # Handle the change of CSS theme from the combobox
        try:
            model = combo.get_model()
            iter = combo.get_active_iter()

            if iter is not None:
                css = model[iter][0]
                css_manager.save_css_config(css)
                css_manager.apply_theme(css)
                self.logger.info(f"CSS changed to: {css}")
            else:
                self.logger.info("No css selected.")
        except Exception as e:
            self.logger.error(f"Error changing css: {e}")

    def show_enhanced_control_warning_dialog(self, widget):
        # Show the warning dialog for enabling enhanced Ryzen control
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self.settings_window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Enable Enhanced Ryzen Control",
            )
            dialog.format_secondary_text(
                "This option requires the installation of ryzen_smu. "
                "It will also require installing other dependencies. "
                "This program does not provide a way to uninstall ryzen_smu. "
                "You can also install ryzen_smu manually to enable this feature. "
                "Are you sure that you want to continue?"
            )

            # Run the dialog and capture the response
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                # If the user confirms, enable enhanced control
                self.logger.info("User confirmed to enable enhanced Ryzen control.")
                self.enable_enhanced_control()
            else:
                # If the user cancels, reset the checkbutton state
                self.logger.info("User canceled enabling enhanced Ryzen control.")
                widget.handler_block_by_func(self.show_enhanced_control_warning_dialog)
                widget.set_active(False)
                widget.handler_unblock_by_func(self.show_enhanced_control_warning_dialog)
        except Exception as e:
            self.logger.error(f"Error showing enhanced control warning dialog: {e}")

    def enable_enhanced_control(self):
        # Enable enhanced control for Ryzen CPUs by installing ryzen_smu
        try:
            # Disable the checkbutton to prevent further interactions during the process
            self.enhanced_control_checkbutton.set_sensitive(False)
            Gtk.main_iteration()  # Process events to update the UI

            # Attempt to enable enhanced control using ryzen_smu_installer
            if ryzen_smu_installer.enable_enhanced_control():
                # Show a success message dialog if enhanced control is enabled successfully
                Gtk.MessageDialog(
                    self.settings_window,
                    0,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    "Enhanced Ryzen Control enabled successfully.",
                ).run()
                # Update the checkbutton to reflect the new state
                self.enhanced_control_checkbutton.set_active(True)
                self.enhanced_control_checkbutton.set_sensitive(False)
            else:
                # Show an error message dialog if enabling enhanced control fails
                Gtk.MessageDialog(
                    self.settings_window,
                    0,
                    Gtk.MessageType.ERROR,
                    Gtk.ButtonsType.OK,
                    "Failed to enable Enhanced Ryzen Control.",
                ).run()
                # Re-enable the checkbutton to allow further attempts
                self.enhanced_control_checkbutton.set_active(False)
                self.enhanced_control_checkbutton.set_sensitive(True)
        except Exception as e:
            self.logger.error(f"Error enabling Ryzen enhanced control: {e}")

    def update_enhanced_control_checkbutton(self):
        # Update the status of the enhanced control checkbutton
        is_installed = ryzen_smu_installer.is_ryzen_smu_installed()
        self.enhanced_control_checkbutton.handler_block_by_func(self.show_enhanced_control_warning_dialog)
        self.enhanced_control_checkbutton.set_active(is_installed)
        self.enhanced_control_checkbutton.set_sensitive(not is_installed)
        self.enhanced_control_checkbutton.handler_unblock_by_func(self.show_enhanced_control_warning_dialog)

# Create an instance of the SettingsWindow
settings_window = SettingsWindow()
