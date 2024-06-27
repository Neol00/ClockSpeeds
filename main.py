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
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio
import logging
from log_setup import get_logger
from shared import global_state, gui_components
from create_widgets import widget_factory
from cpu_management import cpu_manager
from settings_window_setup import settings_window
from cpu_file_search import cpu_file_search
from scale_management import scale_manager

class ClockSpeedsApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        # Initialize the logger
        self.logger = get_logger()
        super().__init__(*args, application_id="org.ClockSpeeds", flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)

        # Set up the directory and icon paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(self.script_dir, "icon", "ClockSpeeds-Icon.png")

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
                settings_window.init_display_ghz_setting()
                global_state.save_settings()
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

    def setup_main_box(self):
        # Set up the main box layout
        try:
            self.main_box = widget_factory.create_box(self.window)
        except Exception as e:
            self.logger.error(f"Error setting up main box: {e}")

    def create_main_notebook(self):
        # Create the main notebook widget with tabs
        try:
            self.notebook = widget_factory.create_notebook(
                self.main_box)
            self.monitor_tab = widget_factory.create_tab(
                self.notebook, 'Monitor')
            self.control_tab = widget_factory.create_tab(
                self.notebook, 'Control')
            
            # Connect the switch-page signal
            self.notebook.connect("switch-page", self.on_tab_switch)
        except Exception as e:
            self.logger.error(f"Error creating notebook: {e}")

    def on_tab_switch(self, notebook, page, page_num):
        # Stop or start the periodic tasks on tab switch
        if page_num == 0:  # Monitor tab
            cpu_manager.schedule_monitor_tasks()
            cpu_manager.stop_control_tasks()
        elif page_num == 1:  # Control tab
            cpu_manager.schedule_control_tasks()
            cpu_manager.stop_monitor_tasks()
        else:
            cpu_manager.stop_monitor_tasks()
            cpu_manager.stop_control_tasks()

    def create_grids(self):
        # Create grids for the monitor and control tabs
        try:
            self.monitor_grid = widget_factory.create_grid()
            self.control_grid = widget_factory.create_grid()

            self.monitor_tab.append(self.monitor_grid)
            self.control_tab.append(self.control_grid)
        except Exception as e:
            self.logger.error(f"Error creating grids: {e}")

    def create_more_button(self):
        # Create the "more" button to show additional options
        try:
            self.more_button = widget_factory.create_button(
                self.main_box, None, self.show_more_options, margin_start=10, margin_end=10, margin_top=5, margin_bottom=5)
            self.more_button.set_icon_name("open-menu-symbolic")
        except Exception as e:
            self.logger.error(f"Error creating more ... button: {e}")

    def show_more_options(self, widget):
        # Show the more options popover
        try:
            more_popover = Gtk.Popover()
            more_box = widget_factory.create_box(more_popover)

            settings_button = widget_factory.create_button(
                more_box, "Settings", settings_window.open_settings_window, margin_start=5, margin_end=5, margin_bottom=5)
            system_button = widget_factory.create_button(
                more_box, "System", self.open_system_window, margin_start=5, margin_end=5, margin_bottom=5)
            about_button = widget_factory.create_button(
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
            cpu_info = cpu_manager.get_cpu_info()
            if not cpu_info:
                self.logger.warning("Failed to retrieve CPU info.")
                return

            # Create a new Gtk.Window for the system information
            system_window = widget_factory.create_window("System", self.window, 330, 300)

            def on_destroy(widget):
                system_window.close()

            system_window.connect("close-request", on_destroy)

            # Create a vertical box to hold the content
            system_box = widget_factory.create_box(system_window)

            # Create a grid to layout the system information
            system_grid = widget_factory.create_grid()
            system_fixed = Gtk.Fixed()
            system_box.append(system_grid)
            system_grid.attach(system_fixed, 0, 0, 1, 1)

            # Add a label for the system information title
            widget_factory.create_label(
                system_fixed, markup="<b>System Information</b>", x=105, y=10)

            y_offset = 40
            for key, value in cpu_info.items():
                # Skip certain keys to avoid displaying them
                if key not in ["Min (MHz)", "Max (MHz)", "Physical Cores", "Virtual Cores (Threads)", "Total RAM (MB)", "Cache Sizes"]:
                    widget_factory.create_label(
                        system_fixed, text=f"{key}: {value}", x=10, y=y_offset)
                    y_offset += 30

            # Display cache sizes if available
            if "Cache Sizes" in cpu_info:
                cache_sizes = cpu_info["Cache Sizes"]
                widget_factory.create_label(
                    system_fixed, text="Cache Sizes:", x=10, y=y_offset)
                y_offset += 30
                for cache_type, size in cache_sizes.items():
                    widget_factory.create_label(
                        system_fixed, text=f"{cache_type}: {size}", x=10, y=y_offset)
                    y_offset += 30

            # Display physical and virtual cores
            widget_factory.create_label(
                system_fixed, text=f"Cores: {cpu_info['Physical Cores']}  Virtual Cores (Threads): {cpu_info['Virtual Cores (Threads)']}", x=10, y=y_offset)
            y_offset += 30

            # Display total RAM
            widget_factory.create_label(
                system_fixed, text=f"Total RAM (MB): {cpu_info['Total RAM (MB)']}", x=10, y=y_offset)
            y_offset += 30

            min_frequencies = cpu_info.get("Min (MHz)", [])
            max_frequencies = cpu_info.get("Max (MHz)", [])

            # Display allowed CPU frequencies if available
            if min_frequencies and max_frequencies:
                widget_factory.create_label(
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

                    widget_factory.create_label(
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
            about_window = widget_factory.create_window("About", self.window, 350, 205)

            def on_destroy(widget):
                about_window.close()

            about_window.connect("close-request", on_destroy)

            # Create a vertical box to hold the content
            about_box = widget_factory.create_box(about_window)

            # Create a notebook to hold the tabs
            about_notebook = widget_factory.create_notebook(
                about_box)

            # About Tab
            about_tab = widget_factory.create_about_tab(
                about_notebook, "About")
            about_grid = widget_factory.create_grid()
            about_fixed = Gtk.Fixed()
            about_tab.append(about_grid)
            about_grid.attach(about_fixed, 0, 0, 1, 1)

            # Load, scale, and add the icon to the about box
            icon = Gtk.Image.new_from_file(self.icon_path)
            icon.set_size_request(128, 128)
            about_fixed.put(icon, 0, 10)

            # Add a label with information about the application
            widget_factory.create_label(
                about_fixed,
                markup="<b>ClockSpeeds</b>\n\n"
                       "CPU Monitoring and Control Application for Linux\n\n"
                       "Version 0.11",
                x=120, y=30)

            # Credits Tab
            credits_tab = widget_factory.create_about_tab(
                about_notebook, "Credits")
            credits_grid = widget_factory.create_grid()
            credits_fixed = Gtk.Fixed()
            credits_tab.append(credits_grid)
            credits_grid.attach(credits_fixed, 0, 0, 1, 1)

            # Add a label with credits information
            widget_factory.create_label(
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

            for i in range(cpu_file_search.thread_count):
                row = i // 2
                col = i % 2
                x_offset = col * 250  # Adjust horizontal spacing
                y_offset = row * 50   # Adjust vertical spacing

                description_label = widget_factory.create_label(
                    monitor_fixed, f"Thread {i}:", x=x_offset + 10, y=y_offset + 15)
                clock_label = widget_factory.create_entry(
                    monitor_fixed, "N/A MHz", False, width_chars=10, x=x_offset + 80, y=y_offset + 10)
                progress_bar, percentage_label = widget_factory.create_progressbar(
                    monitor_fixed, x=x_offset + 175, y=y_offset)

                self.clock_labels[i] = clock_label
                self.progress_bars[i] = (progress_bar, percentage_label)

            y_offset += 60

            average_description_label = widget_factory.create_label(
                monitor_fixed, "Average:", x=16, y=y_offset + 5)
            self.average_clock_entry = widget_factory.create_entry(
                monitor_fixed, "N/A MHz", False, width_chars=10, x=80, y=y_offset)
            self.average_progress_bar = widget_factory.create_progressbar(
                monitor_fixed, x=175, y=y_offset - 10)

            package_temp_label = widget_factory.create_label(
                monitor_fixed, "Package Temp:", x=280, y=y_offset + 4)
            self.package_temp_entry = widget_factory.create_entry(
                monitor_fixed, "N/A °C", False, width_chars=10, x=380, y=y_offset)

            self.thermal_throttle_label = widget_factory.create_label(
                monitor_fixed, "Throttling", x=392, y=y_offset + 32)
            self.thermal_throttle_label.set_visible(False)

            self.current_governor_label = widget_factory.create_label(
                monitor_fixed, "", x=170, y=y_offset + 50, margin_bottom=10)

            self.logger.info("Monitor widgets created.")
        except Exception as e:
            self.logger.error(f"Error creating monitor widgets: {e}")

    def create_control_widgets(self):
        # Create the widgets for the control tab
        try:
            control_fixed = Gtk.Fixed()
            self.control_grid.attach(control_fixed, 0, 0, 1, 1)

            self.cpu_min_max_checkbuttons = {}
            self.cpu_min_scales = {}
            self.cpu_max_scales = {}

            for i in range(cpu_file_search.thread_count):
                y_offset = i * 100  # Adjust vertical spacing

                cpu_min_max_checkbutton = widget_factory.create_checkbutton(
                    control_fixed, f"Thread {i}", None, self.update_check_all_state, x=10, y=y_offset + 27)
                cpu_min_max_checkbutton.set_active(True)
                cpu_min_max_checkbutton.set_tooltip_text("Toggle whether minimum and maximum frequency should be applied")

                cpu_max_scale = widget_factory.create_scale(
                    control_fixed, scale_manager.update_min_max_labels, global_state.SCALE_MIN, global_state.SCALE_MAX, x=100, y=y_offset + 10, Frequency=True)
                cpu_max_scale.set_name(f'cpu_max_scale_{i}')
                cpu_max_scale.set_tooltip_text("Maximum frequency")
                cpu_max_desc = widget_factory.create_label(
                    control_fixed, f"Maximum", x=440, y=y_offset + 10)

                cpu_min_scale = widget_factory.create_scale(
                    control_fixed, scale_manager.update_min_max_labels, global_state.SCALE_MIN, global_state.SCALE_MAX, x=100, y=y_offset + 50, Frequency=True)
                cpu_min_scale.set_name(f'cpu_min_scale_{i}')
                cpu_min_scale.set_tooltip_text("Minimum frequency")
                cpu_min_desc = widget_factory.create_label(
                    control_fixed, f"Minimum", x=440, y=y_offset + 50)

                self.cpu_min_max_checkbuttons[i] = cpu_min_max_checkbutton
                self.cpu_min_scales[i] = cpu_min_scale
                self.cpu_max_scales[i] = cpu_max_scale

            # Add Check All checkbutton
            self.check_all_checkbutton = widget_factory.create_checkbutton(
                control_fixed, "Check All", None, self.on_check_all_toggled, x=10, y=y_offset + 98)
            self.check_all_checkbutton.set_tooltip_text("Toggle all thread checkbuttons")

            apply_button = widget_factory.create_button(
                control_fixed, "Apply Speed Limits", cpu_manager.apply_cpu_clock_speed_limits, x=194, y=y_offset + 95)
            apply_button.set_tooltip_text("Apply minimum and maximum speed limits")

            self.governor_combobox = widget_factory.create_combobox(
                control_fixed, global_state.unique_governors, cpu_manager.set_cpu_governor, x=100, y=y_offset + 128)

            self.boost_checkbutton = widget_factory.create_checkbutton(
                control_fixed, "Enable CPU Boost Clock", global_state.boost_enabled, cpu_manager.toggle_boost, x=265, y=y_offset + 130)

            self.tdp_label = widget_factory.create_label(
                control_fixed, "TDP:", x=60, y=y_offset + 160)
            self.tdp_scale = widget_factory.create_scale(
                control_fixed, None, global_state.TDP_SCALE_MIN, global_state.TDP_SCALE_MAX, x=100, y=y_offset + 160)
            self.tdp_scale.set_tooltip_text("Adjust the TDP in watts")
            self.apply_tdp_button = widget_factory.create_button(
                control_fixed, "Apply TDP", cpu_manager.set_intel_tdp, x=220, y=y_offset + 205, margin_bottom=10)

            # Add PBO Curve Offset Scale
            self.pbo_curve_label = widget_factory.create_label(
                control_fixed, "PBO Offset:", x=23, y=y_offset + 235)
            self.pbo_curve_scale = widget_factory.create_scale(
                control_fixed, None, global_state.PBO_SCALE_MIN, global_state.PBO_SCALE_MAX, x=100, y=y_offset + 235, Negative=True)
            self.pbo_curve_scale.set_tooltip_text("Adjust the negative PBO curve offset")
            self.apply_pbo_button = widget_factory.create_button(
                control_fixed, "Apply PBO Offset", cpu_manager.set_pbo_curve_offset, x=190, y=y_offset + 280, margin_bottom=10)

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
            gui_components['clock_labels'] = self.clock_labels
            gui_components['progress_bars'] = self.progress_bars
            gui_components['average_clock_entry'] = self.average_clock_entry
            gui_components['average_progress_bar'] = self.average_progress_bar
            gui_components['package_temp_entry'] = self.package_temp_entry
            gui_components['current_governor_label'] = self.current_governor_label
            gui_components['thermal_throttle_label'] = self.thermal_throttle_label
            gui_components['cpu_min_max_checkbuttons'] = self.cpu_min_max_checkbuttons
            gui_components['cpu_min_scales'] = self.cpu_min_scales
            gui_components['cpu_max_scales'] = self.cpu_max_scales
            gui_components['governor_combobox'] = self.governor_combobox
            gui_components['boost_checkbutton'] = self.boost_checkbutton
            gui_components['tdp_scale'] = self.tdp_scale
            gui_components['pbo_curve_scale'] = self.pbo_curve_scale
            self.logger.info("Widgets added to gui_components.")
        except Exception as e:
            self.logger.error(f"Error adding widget to gui_components: {e}")

    def setup_gui_components(self):
        # Set up GUI components from the CPU and scale managers
        try:
            cpu_manager.setup_gui_components()
            scale_manager.setup_gui_components()
        except Exception as e:
            self.logger.error(f"Error setting up GUI components: {e}")

    def update_scales(self):
        # Update the scales from the scale manager
        try:
            scale_manager.load_scale_config_settings()
            scale_manager.on_disable_scale_limits_change(None)
        except Exception as e:
            self.logger.error(f"Error updating scales: {e}")

    def update_cpu_widgets(self):
        # Update the CPU widgets from the CPU manager
        try:
            cpu_manager.update_clock_speeds()
            cpu_manager.read_package_temperature()
            cpu_manager.get_current_governor()
            cpu_manager.update_governor_combobox()
            cpu_manager.update_boost_checkbutton()
        except Exception as e:
            self.logger.error(f"Error updating CPU widgets: {e}")

    def on_check_all_toggled(self, button):
        # Toggle all thread checkbuttons based on the state of Check All checkbutton
        try:
            # Set flag to indicate update is from Check All checkbutton
            self.updating_from_check_all = True

            active = button.get_active()
            for checkbutton in self.cpu_min_max_checkbuttons.values():
                checkbutton.set_active(active)

            # Reset flag after updating
            self.updating_from_check_all = False
        except Exception as e:
            self.logger.error(f"Error updating thread checkbuttons: {e}")

    def update_check_all_state(self, button):
        # Update the state of Check All checkbutton based on the individual checkbuttons
        try:
            all_active = all(cb.get_active() for cb in self.cpu_min_max_checkbuttons.values())
            self.check_all_checkbutton.handler_block_by_func(self.on_check_all_toggled)
            self.check_all_checkbutton.set_active(all_active)
            self.check_all_checkbutton.handler_unblock_by_func(self.on_check_all_toggled)
        except Exception as e:
            self.logger.error(f"Error updating the Check All checkbutton: {e}")

    def is_tdp_installed(self):
        # Checks if the CPU's TDP can be set
        try:
            self.tdp_installed = False
            if cpu_file_search.cpu_type == "Intel":
                self.tdp_installed = True
            elif cpu_file_search.cpu_type == "Other" and global_state.is_ryzen_smu_installed():
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
            if cpu_file_search.cpu_type == "Other" and global_state.is_ryzen_smu_installed():
                self.pbo_curve_label.set_visible(True)
                self.pbo_curve_scale.set_visible(True)
                self.apply_pbo_button.set_visible(True)
            else:
                self.pbo_curve_label.set_visible(False)
                self.pbo_curve_scale.set_visible(False)
                self.apply_pbo_button.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error setting PBO widgets visibility: {e}")

def main():
    # Main function to start the application
    try:
        app = ClockSpeedsApp()
        app.run()
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error launching the main application: {e}")

if __name__ == "__main__":
    main()
