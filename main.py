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
from gi.repository import Gtk, GLib
from config_setup import ConfigManager
from log_setup import LogSetup
from shared import GlobalState, GuiComponents
from create_widgets import WidgetFactory
from cpu_file_search import CPUFileSearch
from privileged_actions import PrivilegedActions
from apply_settings import SettingsApplier
from cpu_management import CPUManager
from scale_management import ScaleManager
from css_setup import CssManager
from settings_window_setup import SettingsWindow

class ClockSpeedsApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.ClockSpeeds")

        # Set up the directory and icon paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(self.script_dir, "icon", "ClockSpeeds-Icon.png")

        # Create instances
        self.config_manager = ConfigManager()
        self.log_setup = LogSetup(
            self.config_manager)
        self.logger = self.log_setup.logger
        self.global_state = GlobalState(
            self.config_manager, self.logger)
        self.gui_components = GuiComponents(
            self.logger)
        self.widget_factory = WidgetFactory(
            self.logger, self.global_state)
        self.cpu_file_search = CPUFileSearch(
            self.logger)
        self.privileged_actions = PrivilegedActions(
            self.logger)
        self.settings_applier = SettingsApplier(
            self.logger, self.global_state, self.gui_components, self.cpu_file_search, self.privileged_actions)
        self.cpu_manager = CPUManager(
            self.config_manager, self.logger, self.global_state, self.gui_components, self.widget_factory,
            self.cpu_file_search, self.privileged_actions, self.settings_applier)
        self.scale_manager = ScaleManager(
            self.config_manager, self.logger, self.global_state, self.gui_components, self.widget_factory,
            self.cpu_file_search, self.cpu_manager)
        self.css_manager = CssManager(
            self.config_manager, self.logger)
        self.settings_window = SettingsWindow(
            self.config_manager, self.logger, self.global_state, self.gui_components, self.widget_factory,
            self.settings_applier, self.cpu_manager, self.scale_manager, self.css_manager)

        self.is_tdp_installed()

    def do_activate(self):
        # Create the main application window
        try:
            if not hasattr(self, 'window'):
                self.window = Gtk.ApplicationWindow(application=self)
                self.window.set_title("ClockSpeeds")
                self.window.set_default_size(535, 400)
                self.window.set_resizable(False)
                self.window.connect("close-request", self.close_main_window)
                self.window.present()

                self.call_main_methods()
        except Exception as e:
            self.logger.error(f"Error setting up main window: {e}")

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def close_main_window(self, window):
        try:
            window.destroy()
        except Exception as e:
            self.logger.error(f"Error closing the main window: {e}")

    def call_main_methods(self):
        try:
            self.setup_main_box()
            self.create_main_notebook()
            self.create_more_button()
            self.create_grids()
            self.create_cpu_widgets()
            self.add_widgets_to_gui_components()
            self.setup_gui_components()
            self.update_cpu_widgets()
            self.update_scales()
            self.set_tdp_widgets()
            self.set_pbo_widgets()
            self.set_epb_widget()
            self.settings_applier.update_checkbutton_sensitivity()
            self.settings_window.init_display_ghz_setting()
            self.global_state.save_settings()
        except Exception as e:
            self.logger.error(f"Error calling main methods: {e}")

    def setup_main_box(self):
        # Set up the main box layout
        try:
            self.main_box = self.widget_factory.create_box(self.window)
        except Exception as e:
            self.logger.error(f"Error setting up main box: {e}")

    def create_main_notebook(self):
        # Create the main notebook widget with tabs
        try:
            self.notebook = self.widget_factory.create_notebook(
                self.main_box)
            self.monitor_tab = self.widget_factory.create_tab(
                self.notebook, 'Monitor')
            self.control_tab = self.widget_factory.create_tab(
                self.notebook, 'Control')

            # Connect the switch-page signal
            self.notebook.connect("switch-page", self.on_tab_switch)
        except Exception as e:
            self.logger.error(f"Error creating notebook: {e}")

    def on_tab_switch(self, notebook, page, page_num):
        # Stop or start the periodic tasks on tab switch
        if page_num == 0:  # Monitor tab
            self.cpu_manager.schedule_monitor_tasks()
            self.cpu_manager.stop_control_tasks()
        elif page_num == 1:  # Control tab
            self.cpu_manager.schedule_control_tasks()
            self.cpu_manager.stop_monitor_tasks()
        else:
            self.cpu_manager.stop_monitor_tasks()
            self.cpu_manager.stop_control_tasks()

    def create_grids(self):
        # Create grids for the monitor and control tabs
        try:
            self.monitor_grid = self.widget_factory.create_grid()
            self.control_grid = self.widget_factory.create_grid()

            self.monitor_tab.append(self.monitor_grid)
            self.control_tab.append(self.control_grid)
        except Exception as e:
            self.logger.error(f"Error creating grids: {e}")

    def create_more_button(self):
        # Create the "more" button to show additional options
        try:
            self.more_button = self.widget_factory.create_button(
                self.main_box, None, self.show_more_options, margin_start=10, margin_end=10, margin_top=5, margin_bottom=5)
            self.more_button.set_icon_name("open-menu-symbolic")
        except Exception as e:
            self.logger.error(f"Error creating more ... button: {e}")

    def show_more_options(self, widget):
        # Show the more options popover
        try:
            more_popover = Gtk.Popover()
            more_box = self.widget_factory.create_box(more_popover)

            settings_button = self.widget_factory.create_button(
                more_box, "Settings", self.settings_window.open_settings_window, margin_start=5, margin_end=5, margin_bottom=5)
            system_button = self.widget_factory.create_button(
                more_box, "System", self.open_system_window, margin_start=5, margin_end=5, margin_bottom=5)
            about_button = self.widget_factory.create_button(
                more_box, "About", self.open_about_dialog, margin_start=5, margin_end=5)

            more_popover.set_position(Gtk.PositionType.TOP)
            more_popover.set_parent(self.more_button)
            more_popover.popup()
        except Exception as e:
            self.logger.error(f"Error showing more options: {e}")

    def open_system_window(self, widget=None):
        # Open the system information window
        try:
            # Get CPU information from the CPU manager
            cpu_info = self.cpu_manager.get_cpu_info()
            if not cpu_info:
                self.logger.warning("Failed to retrieve CPU info.")
                return

            # Create a new Gtk.Window for the system information
            system_window = self.widget_factory.create_window("System", self.window, 330, 300)

            def on_destroy(widget):
                system_window.close()

            system_window.connect("close-request", on_destroy)

            # Create a vertical box to hold the content
            system_box = self.widget_factory.create_box(system_window)

            # Create a grid to layout the system information
            system_grid = self.widget_factory.create_grid()
            system_fixed = Gtk.Fixed()
            system_box.append(system_grid)
            system_grid.attach(system_fixed, 0, 0, 1, 1)

            # Add a label for the system information title
            self.widget_factory.create_label(
                system_fixed, markup="<b>System Information</b>", x=105, y=10)

            y_offset = 40
            for key, value in cpu_info.items():
                # Skip certain keys to avoid displaying them
                if key not in ["Min (MHz)", "Max (MHz)", "Physical Cores", "Virtual Cores (Threads)", "Total RAM (MB)", "Cache Sizes"]:
                    self.widget_factory.create_label(
                        system_fixed, text=f"{key}: {value}", x=10, y=y_offset)
                    y_offset += 30

            # Display cache sizes if available
            if "Cache Sizes" in cpu_info:
                cache_sizes = cpu_info["Cache Sizes"]
                self.widget_factory.create_label(
                    system_fixed, text="Cache Sizes:", x=10, y=y_offset)
                y_offset += 30
                for cache_type, size in cache_sizes.items():
                    self.widget_factory.create_label(
                        system_fixed, text=f"{cache_type}: {size}", x=10, y=y_offset)
                    y_offset += 30

            # Display physical and virtual cores
            self.widget_factory.create_label(
                system_fixed, text=f"Cores: {cpu_info['Physical Cores']}  Virtual Cores (Threads): {cpu_info['Virtual Cores (Threads)']}", x=10, y=y_offset)
            y_offset += 30

            # Display total RAM
            self.widget_factory.create_label(
                system_fixed, text=f"Total RAM (MB): {cpu_info['Total RAM (MB)']}", x=10, y=y_offset)
            y_offset += 30

            min_frequencies = cpu_info.get("Min (MHz)", [])
            max_frequencies = cpu_info.get("Max (MHz)", [])

            # Display allowed CPU frequencies if available
            if min_frequencies and max_frequencies:
                self.widget_factory.create_label(
                    system_fixed, markup="<b>Allowed CPU Frequencies</b>", x=88, y=y_offset)
                y_offset += 30

                # Group threads by their min and max frequencies
                thread_groups = {}
                for i, (min_freq, max_freq) in enumerate(zip(min_frequencies, max_frequencies)):
                    key = (min_freq, max_freq)
                    if key not in thread_groups:
                        thread_groups[key] = []
                    thread_groups[key].append(i)

                # Display thread groups with their frequency ranges
                for (min_freq, max_freq), threads in thread_groups.items():
                    thread_ranges = []
                    start = threads[0]
                    for i in range(1, len(threads)):
                        if threads[i] != threads[i-1] + 1:
                            end = threads[i-1]
                            if start == end:
                                thread_ranges.append(f"Thread {start}")
                            else:
                                thread_ranges.append(f"Thread {start}-{end}")
                            start = threads[i]
                    end = threads[-1]
                    if start == end:
                        thread_ranges.append(f"Thread {start}")
                    else:
                        thread_ranges.append(f"Thread {start}-{end}")

                    self.widget_factory.create_label(
                        system_fixed, text=f"{', '.join(thread_ranges)}: {min_freq:.2f} MHz - {max_freq:.2f} MHz", x=10, y=y_offset, margin_bottom=10)
                    y_offset += 30

            # Present the system information window
            system_window.present()

        except Exception as e:
            self.logger.error(f"Error opening system window: {e}")

    def open_about_dialog(self, widget=None):
        # Open the about dialog
        try:
            # Create a new Gtk.Window for the about dialog
            about_window = self.widget_factory.create_window("About", self.window, 350, 205)

            def on_destroy(widget):
                about_window.close()

            about_window.connect("close-request", on_destroy)

            # Create a vertical box to hold the content
            about_box = self.widget_factory.create_box(about_window)

            # Create a notebook to hold the tabs
            about_notebook = self.widget_factory.create_notebook(
                about_box)

            # About Tab
            about_tab = self.widget_factory.create_about_tab(
                about_notebook, "About")
            about_grid = self.widget_factory.create_grid()
            about_fixed = Gtk.Fixed()
            about_tab.append(about_grid)
            about_grid.attach(about_fixed, 0, 0, 1, 1)

            # Load, scale, and add the icon to the about box
            icon = Gtk.Image.new_from_file(self.icon_path)
            icon.set_size_request(128, 128)
            about_fixed.put(icon, 0, 10)

            # Add a label with information about the application
            self.widget_factory.create_label(
                about_fixed,
                markup="<b>ClockSpeeds</b>\n\n"
                       "CPU Monitoring and Control Application for Linux\n\n"
                       "Version 0.12",
                x=120, y=30)

            # Credits Tab
            credits_tab = self.widget_factory.create_about_tab(
                about_notebook, "Credits")
            credits_grid = self.widget_factory.create_grid()
            credits_fixed = Gtk.Fixed()
            credits_tab.append(credits_grid)
            credits_grid.attach(credits_fixed, 0, 0, 1, 1)

            # Add a label with credits information
            self.widget_factory.create_label(
                credits_fixed,
                markup="Main developer: Noel Ejemyr\n\n"
                       "This application is licensed under the <a href='https://www.gnu.org/licenses/gpl-3.0.html'>GNU General Public License v3</a>.\n\n"
                       "This application uses <a href='https://www.gtk.org/'>GTK</a> for its graphical interface.\n\n"
                       "This application uses <a href='https://github.com/leogx9r/ryzen_smu'>ryzen_smu</a> for controlling Ryzen CPUs.",
                x=10, y=10)

            # Present the about window
            about_window.present()

        except Exception as e:
            self.logger.error(f"Error opening about dialog: {e}")

    def create_monitor_widgets(self):
        # Create the widgets for the monitor tab
        try:
            monitor_fixed = Gtk.Fixed()
            self.monitor_grid.attach(monitor_fixed, 0, 0, 1, 1)

            self.clock_labels = {}
            self.progress_bars = {}

            for i in range(self.cpu_file_search.thread_count):
                row = i // 2
                col = i % 2
                x_offset = col * 250  # Adjust horizontal spacing
                y_offset = row * 50   # Adjust vertical spacing

                description_label = self.widget_factory.create_label(
                    monitor_fixed, f"Thread {i}:", x=x_offset + 10, y=y_offset + 15)
                clock_label = self.widget_factory.create_entry(
                    monitor_fixed, "N/A MHz", False, width_chars=10, x=x_offset + 80, y=y_offset + 10)
                progress_bar, percentage_label = self.widget_factory.create_progressbar(
                    monitor_fixed, x=x_offset + 175, y=y_offset)

                self.clock_labels[i] = clock_label
                self.progress_bars[i] = (progress_bar, percentage_label)

            y_offset += 60

            average_description_label = self.widget_factory.create_label(
                monitor_fixed, "Average:", x=16, y=y_offset + 5)
            self.average_clock_entry = self.widget_factory.create_entry(
                monitor_fixed, "N/A MHz", False, width_chars=10, x=80, y=y_offset)
            self.average_progress_bar = self.widget_factory.create_progressbar(
                monitor_fixed, x=175, y=y_offset - 10)

            package_temp_label = self.widget_factory.create_label(
                monitor_fixed, "Package Temp:", x=280, y=y_offset + 4)
            self.package_temp_entry = self.widget_factory.create_entry(
                monitor_fixed, "N/A °C", False, width_chars=10, x=380, y=y_offset)

            self.thermal_throttle_label = self.widget_factory.create_label(
                monitor_fixed, "Throttling", x=392, y=y_offset + 32)
            self.thermal_throttle_label.set_visible(False)

            self.current_governor_label = self.widget_factory.create_label(
                monitor_fixed, "", x=170, y=y_offset + 50, margin_bottom=10)

            self.logger.info("Monitor widgets created.")
        except Exception as e:
            self.logger.error(f"Error creating monitor widgets: {e}")

    def create_control_widgets(self):
        # Create the widgets for the control tab
        try:
            control_fixed = Gtk.Fixed()
            self.control_grid.attach(control_fixed, 0, 0, 1, 1)

            self.cpu_max_min_checkbuttons = {}
            self.cpu_min_scales = {}
            self.cpu_max_scales = {}

            # Block the signal handlers to prevent multiple calls to update_check_all_state
            self.initialization_complete = False
            self.debounce_timeout_id = None

            for i in range(self.cpu_file_search.thread_count):
                y_offset = i * 100  # Adjust vertical spacing

                cpu_max_min_checkbutton = self.widget_factory.create_checkbutton(
                    control_fixed, f"Thread {i}", None, lambda button, i=i: self.debounced_update_check_all_state(), x=10, y=y_offset + 27)
                cpu_max_min_checkbutton.set_active(True)
                cpu_max_min_checkbutton.set_tooltip_text("Toggle whether minimum and maximum frequency should be applied")

                cpu_max_scale = self.widget_factory.create_scale(
                    control_fixed, self.scale_manager.update_min_max_labels, self.global_state.SCALE_MIN, self.global_state.SCALE_MAX, x=100, y=y_offset + 10, Frequency=True)
                cpu_max_scale.set_name(f'cpu_max_scale_{i}')
                cpu_max_scale.set_tooltip_text("Maximum frequency")
                cpu_max_desc = self.widget_factory.create_label(
                    control_fixed, f"Maximum", x=440, y=y_offset + 10)

                cpu_min_scale = self.widget_factory.create_scale(
                    control_fixed, self.scale_manager.update_min_max_labels, self.global_state.SCALE_MIN, self.global_state.SCALE_MAX, x=100, y=y_offset + 50, Frequency=True)
                cpu_min_scale.set_name(f'cpu_min_scale_{i}')
                cpu_min_scale.set_tooltip_text("Minimum frequency")
                cpu_min_desc = self.widget_factory.create_label(
                    control_fixed, f"Minimum", x=440, y=y_offset + 50)

                self.cpu_max_min_checkbuttons[i] = cpu_max_min_checkbutton
                self.cpu_max_scales[i] = cpu_max_scale
                self.cpu_min_scales[i] = cpu_min_scale

            # Add Check All checkbutton
            self.check_all_checkbutton = self.widget_factory.create_checkbutton(
                control_fixed, "Check All", None, self.on_check_all_toggled, x=10, y=y_offset + 98)
            self.check_all_checkbutton.set_tooltip_text("Toggle all thread checkbuttons")

            self.apply_max_min_button = self.widget_factory.create_button(
                control_fixed, "Apply Speed Limits", self.cpu_manager.apply_cpu_clock_speed_limits, x=194, y=y_offset + 95)
            self.apply_max_min_button.set_tooltip_text("Apply minimum and maximum speed limits")

            self.governor_combobox = self.widget_factory.create_combobox(
                control_fixed, self.global_state.unique_governors, self.cpu_manager.set_cpu_governor, x=100, y=y_offset + 128)

            self.boost_checkbutton = self.widget_factory.create_checkbutton(
                control_fixed, "Enable CPU Boost Clock", self.global_state.boost_enabled, self.cpu_manager.toggle_boost, x=265, y=y_offset + 130)

            self.tdp_label = self.widget_factory.create_label(
                control_fixed, "TDP:", x=60, y=y_offset + 160)
            self.tdp_scale = self.widget_factory.create_scale(
                control_fixed, None, self.global_state.TDP_SCALE_MIN, self.global_state.TDP_SCALE_MAX, x=100, y=y_offset + 160)
            self.tdp_scale.set_tooltip_text("Adjust the TDP in watts")
            self.apply_tdp_button = self.widget_factory.create_button(
                control_fixed, "Apply TDP", self.cpu_manager.set_intel_tdp, x=220, y=y_offset + 205, margin_bottom=10)

            # Add PBO Curve Offset Scale
            self.pbo_curve_label = self.widget_factory.create_label(
                control_fixed, "PBO Offset:", x=23, y=y_offset + 235)
            self.pbo_curve_scale = self.widget_factory.create_scale(
                control_fixed, None, self.global_state.PBO_SCALE_MIN, self.global_state.PBO_SCALE_MAX, x=100, y=y_offset + 235, Negative=True)
            self.pbo_curve_scale.set_tooltip_text("Adjust the negative PBO curve offset")
            self.apply_pbo_button = self.widget_factory.create_button(
                control_fixed, "Apply PBO Offset", self.cpu_manager.set_pbo_curve_offset, x=190, y=y_offset + 280, margin_bottom=10)

            # Add Energy Performance Bias ComboBox
            self.epb_combobox = self.widget_factory.create_combobox(
                control_fixed, ["Select Energy Performance Bias", "0 Performance", "4 Balance-Performance", "6 Normal", "8 Balance-Power", "15 Power"],
                self.cpu_manager.set_energy_perf_bias, x=155, y=y_offset + 245, margin_bottom=10)
            self.epb_combobox.set_active(0)
            self.epb_combobox.set_tooltip_text("Select Intel performance and energy bias hint")

            self.initialization_complete = True
            self.update_check_all_state(None)
            self.logger.info("Control widgets created.")
        except Exception as e:
            self.logger.error(f"Error creating control widgets: {e}")

    def create_cpu_widgets(self):
        # Create both monitor and control widgets
        try:
            self.create_monitor_widgets()
            self.create_control_widgets()
        except Exception as e:
            self.logger.error(f"Error creating CPU widgets: {e}")

    def add_widgets_to_gui_components(self):
        # Add created widgets to the shared GUI components dictionary
        try:
            self.gui_components['clock_labels'] = self.clock_labels
            self.gui_components['progress_bars'] = self.progress_bars
            self.gui_components['average_clock_entry'] = self.average_clock_entry
            self.gui_components['average_progress_bar'] = self.average_progress_bar
            self.gui_components['package_temp_entry'] = self.package_temp_entry
            self.gui_components['current_governor_label'] = self.current_governor_label
            self.gui_components['thermal_throttle_label'] = self.thermal_throttle_label
            self.gui_components['cpu_max_min_checkbuttons'] = self.cpu_max_min_checkbuttons
            self.gui_components['cpu_min_scales'] = self.cpu_min_scales
            self.gui_components['cpu_max_scales'] = self.cpu_max_scales
            self.gui_components['apply_max_min_button'] = self.apply_max_min_button
            self.gui_components['governor_combobox'] = self.governor_combobox
            self.gui_components['boost_checkbutton'] = self.boost_checkbutton
            self.gui_components['tdp_scale'] = self.tdp_scale
            self.gui_components['apply_tdp_button'] = self.apply_tdp_button
            self.gui_components['pbo_curve_scale'] = self.pbo_curve_scale
            self.gui_components['apply_pbo_button'] = self.apply_pbo_button
            self.gui_components['epb_combobox'] = self.epb_combobox
            self.logger.info("Widgets added to gui_components.")
        except Exception as e:
            self.logger.error(f"Error adding main widgets to gui_components: {e}")

    def setup_gui_components(self):
        # Set up GUI components from the CPU and scale managers
        try:
            self.cpu_manager.setup_gui_components()
            self.scale_manager.setup_gui_components()
            self.settings_applier.setup_gui_components()
        except Exception as e:
            self.logger.error(f"Error setting up gui_components: {e}")

    def update_scales(self):
        # Update the scales from the scale manager
        try:
            self.scale_manager.load_scale_config_settings()
            self.scale_manager.on_disable_scale_limits_change(None)
        except Exception as e:
            self.logger.error(f"Error updating scales: {e}")

    def update_cpu_widgets(self):
        # Update the CPU widgets from the CPU manager
        try:
            self.cpu_manager.update_clock_speeds()
            self.cpu_manager.read_package_temperature()
            self.cpu_manager.get_current_governor()
            self.cpu_manager.update_governor_combobox()
            self.cpu_manager.update_boost_checkbutton()
        except Exception as e:
            self.logger.error(f"Error updating CPU widgets: {e}")

    def debounced_update_check_all_state(self, delay=10):
        if self.debounce_timeout_id is not None:
            GLib.source_remove(self.debounce_timeout_id)
        
        self.debounce_timeout_id = GLib.timeout_add(delay, self.update_check_all_state, None)

    def on_check_all_toggled(self, button):
        # Toggle all thread checkbuttons based on the state of Check All checkbutton
        try:
            # Set flag to indicate update is from Check All checkbutton
            self.updating_from_check_all = True

            active = button.get_active()
            for checkbutton in self.cpu_max_min_checkbuttons.values():
                checkbutton.set_active(active)

            # Reset flag after updating
            self.updating_from_check_all = False
        except Exception as e:
            self.logger.error(f"Error updating thread checkbuttons: {e}")

    def update_check_all_state(self, button):
        # Update the state of Check All checkbutton based on the individual checkbuttons
        try:
            if not self.initialization_complete:
                return False  # Return False to not reschedule the timeout
            all_active = all(cb.get_active() for cb in self.cpu_max_min_checkbuttons.values())
            self.check_all_checkbutton.handler_block_by_func(self.on_check_all_toggled)
            self.check_all_checkbutton.set_active(all_active)
            self.check_all_checkbutton.handler_unblock_by_func(self.on_check_all_toggled)
            return False
        except Exception as e:
            self.logger.error(f"Error updating the Check All checkbutton: {e}")
            return False

    def is_tdp_installed(self):
        # Checks if the CPU's TDP can be set
        try:
            self.tdp_installed = False
            if self.cpu_file_search.cpu_type == "Intel":
                self.tdp_installed = True
            elif self.cpu_file_search.cpu_type == "Other" and self.global_state.is_ryzen_smu_installed():
                self.tdp_installed = True
        except Exception as e:
            self.logger.error(f"Error checking if TDP can be set: {e}")

    def set_tdp_widgets(self):
        # Sets the visibility of the TDP widgets based on tdp_installed
        try:
            if self.tdp_installed:
                self.tdp_label.set_visible(True)
                self.tdp_scale.set_visible(True)
                self.apply_tdp_button.set_visible(True)
            else:
                self.tdp_label.set_visible(False)
                self.tdp_scale.set_visible(False)
                self.apply_tdp_button.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error setting TDP widgets visibility: {e}")

    def set_pbo_widgets(self):
        # Sets the visibility of the TDP widgets based on tdp_installed
        try:
            if self.cpu_file_search.cpu_type == "Other" and self.global_state.is_ryzen_smu_installed():
                self.pbo_curve_label.set_visible(True)
                self.pbo_curve_scale.set_visible(True)
                self.apply_pbo_button.set_visible(True)
            else:
                self.pbo_curve_label.set_visible(False)
                self.pbo_curve_scale.set_visible(False)
                self.apply_pbo_button.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error setting AMD Ryzen PBO widgets visibility: {e}")

    def set_epb_widget(self):
        # Sets the visibility of the TDP widgets based on tdp_installed
        try:
            if self.cpu_file_search.cpu_type == "Intel":
                self.epb_combobox.set_visible(True)
            else:
                self.epb_combobox.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error setting Intel EPB widgets visibility: {e}")

def main():
    # Main function to start the application
    try:
        app = ClockSpeedsApp()
        app.run()
    except Exception as e:
        app.logger.error(f"Error launching the main application: {e}")

if __name__ == "__main__":
    main()
