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
import tempfile
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GdkPixbuf, AppIndicator3
import logging
from log_setup import get_logger
from shared import global_state, gui_components
from create_widgets import widget_factory
from cpu_management import cpu_manager
from settings_window_setup import settings_window
from cpu_file_search import cpu_file_search
from scale_management import scale_manager
from ryzen_smu_installer import ryzen_smu_installer

class ClockSpeedsApp:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.window = Gtk.Window(title="ClockSpeeds")
        self.window.set_default_size(535, 350)
        self.window.set_resizable(False)
        self.window.connect("destroy", Gtk.main_quit)
        self.window.connect("window-state-event", self.on_window_state_event)

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(self.script_dir, "icon", "ClockSpeeds-Icon.png")
        self.pixbuf128 = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.icon_path, 128, 128, True)
        self.pixbuf64 = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.icon_path, 64, 64, True)

        self.setup_main_box()
        self.create_main_notebook()
        self.create_more_button()
        self.create_grids()
        self.create_cpu_widgets()
        self.add_widgets_to_gui_components()
        self.setup_gui_components()
        self.update_scales()
        self.update_cpu_widgets()
        self.set_window_icon()
        self.setup_tray_icon()

    def setup_main_box(self):
        try:
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.window.add(self.main_box)
        except Exception as e:
            self.logger.error(f"Error setting up main window: {e}")

    def create_main_notebook(self):
        try:
            self.notebook = widget_factory.create_notebook(
                self.main_box)
            self.monitor_tab = widget_factory.create_tab(
                self.notebook, 'Monitor')
            self.control_tab = widget_factory.create_tab(
                self.notebook, 'Control')
        except Exception as e:
            self.logger.error(f"Error creating notebook: {e}")

    def create_more_button(self):
        try:
            more_button = widget_factory.create_button(
                self.main_box, "...", self.show_more_options, margin_start=10, margin_end=10)
        except Exception as e:
            self.logger.error(f"Error creating more ... button: {e}")

    def create_grids(self):
        try:
            self.monitor_grid = widget_factory.create_grid()
            self.control_grid = widget_factory.create_grid()

            self.monitor_tab.add(self.monitor_grid)
            self.control_tab.add(self.control_grid)

            self.control_fixed = Gtk.Fixed()
            self.monitor_fixed = Gtk.Fixed()

            self.monitor_grid.add(self.monitor_fixed)
            self.control_grid.add(self.control_fixed)
        except Exception as e:
            self.logger.error(f"Error creating grids: {e}")

    def show_more_options(self, widget):
        try:
            more_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            more_popover = Gtk.Popover()
            more_popover.add(more_box)

            settings_button = widget_factory.create_button(
                more_box, "Settings", settings_window.open_settings_window, margin_start=15, margin_end=15)
            system_button = widget_factory.create_button(
                more_box, "System", self.open_system_window, margin_start=15, margin_end=15)
            about_button = widget_factory.create_button(
                more_box, "About", self.open_about_dialog, margin_start=15, margin_end=15)

            more_box.show_all()
            more_popover.set_position(Gtk.PositionType.BOTTOM)
            more_popover.set_relative_to(widget)
            more_popover.show_all()
        except Exception as e:
            self.logger.error(f"Error showing more options: {e}")

    def open_system_window(self, widget=None):
        try:
            cpu_info = cpu_manager.get_cpu_info()
            if not cpu_info:
                self.logger.error("Failed to retrieve CPU info.")
                return

            system_dialog = Gtk.Dialog(title="System", transient_for=self.window, flags=0)
            system_dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
            system_dialog.connect("response", lambda d, r: d.destroy())

            system_box = system_dialog.get_content_area()
            system_grid = widget_factory.create_grid()
            system_fixed = Gtk.Fixed()
            system_grid.add(system_fixed)
            system_box.add(system_grid)

            widget_factory.create_label(
                system_fixed, markup="<b>System Information</b>", x=10, y=10)

            y_offset = 40
            for key, value in cpu_info.items():
                if key not in ["Min (MHz)", "Max (MHz)", "Physical Cores", "Virtual Cores (Threads)", "Total RAM (MB)"]:
                    widget_factory.create_label(
                        system_fixed, text=f"{key}: {value}", x=10, y=y_offset)
                    y_offset += 30

            widget_factory.create_label(
                system_fixed, text=f"Cores: {cpu_info['Physical Cores']}  Virtual Cores (Threads): {cpu_info['Virtual Cores (Threads)']}", x=10, y=y_offset)
            y_offset += 30

            widget_factory.create_label(
                system_fixed, text=f"Total RAM (MB): {cpu_info['Total RAM (MB)']}", x=10, y=y_offset)
            y_offset += 30

            min_frequencies = cpu_info.get("Min (MHz)", [])
            max_frequencies = cpu_info.get("Max (MHz)", [])

            if min_frequencies and max_frequencies:
                widget_factory.create_label(
                    system_fixed, markup="<b>Allowed CPU Frequencies</b>", x=10, y=y_offset)
                y_offset += 30

                # Group threads by their min and max frequencies
                thread_groups = {}
                for i, (min_freq, max_freq) in enumerate(zip(min_frequencies, max_frequencies)):
                    key = (min_freq, max_freq)
                    if key not in thread_groups:
                        thread_groups[key] = []
                    thread_groups[key].append(i)

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
                        system_fixed, text=f"{', '.join(thread_ranges)}: {min_freq:.2f} MHz - {max_freq:.2f} MHz", x=10, y=y_offset)
                    y_offset += 30

            system_dialog.show_all()

        except Exception as e:
            self.logger.error(f"Error opening system window: {e}")

    def open_about_dialog(self, widget=None):
        try:
            about_dialog = Gtk.Dialog(title="About", transient_for=self.window, modal=True)
            about_dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
            about_dialog.set_default_size(350, 250)
            about_dialog.connect("response", lambda d, r: d.destroy())

            # Create notebook
            about_notebook = widget_factory.create_notebook(about_dialog.get_content_area())

            # About Tab
            about_tab = widget_factory.create_about_tab(
                about_notebook, "About")
            about_grid = widget_factory.create_grid()
            about_tab.add(about_grid)
            
            about_fixed = Gtk.Fixed()
            about_grid.add(about_fixed)

            # Load, scale, and add the icon to the about box
            icon = Gtk.Image.new_from_pixbuf(self.pixbuf128)
            about_fixed.put(icon, 0, 10)

            about_label = widget_factory.create_label(
                about_fixed,
                markup="<b>ClockSpeeds</b>\n\n"
                       "CPU Monitoring and Control Application for Linux\n\n"
                       "Version 0.1",
                x=120, y=30)

            # Credits Tab
            credits_tab = widget_factory.create_about_tab(
                about_notebook, "Credits")
            credits_grid = widget_factory.create_grid()
            credits_tab.add(credits_grid)

            credits_fixed = Gtk.Fixed()
            credits_grid.add(credits_fixed)
            
            credits_label = widget_factory.create_label(
                credits_fixed,
                markup="Main developer: Noel Ejemyr\n\n"
                       "This application is licensed under the <a href='https://www.gnu.org/licenses/gpl-3.0.html'>GNU General Public License v3</a>.\n\n"
                       "This application uses <a href='https://www.gtk.org/'>GTK</a> for its graphical interface.\n\n"
                       "This application uses <a href='https://github.com/leogx9r/ryzen_smu'>ryzen_smu</a> for controlling Ryzen CPUs.",
                x=10, y=10)

            about_dialog.get_content_area().add(about_notebook)
            about_dialog.show_all()

        except Exception as e:
            self.logger.error(f"Error opening about dialog: {e}")

    def create_monitor_widgets(self):
        try:
            self.monitor_grid.show()
            self.clock_labels = {}
            self.progress_bars = {}

            for i in range(cpu_file_search.thread_count):
                row = i // 2
                col = i % 2
                x_offset = col * 250  # Adjust horizontal spacing
                y_offset = row * 50   # Adjust vertical spacing

                description_label = widget_factory.create_label(
                    self.monitor_fixed, f"Thread {i}:", x=x_offset + 5, y=y_offset + 10)

                clock_label = widget_factory.create_entry(
                    self.monitor_fixed, "N/A MHz", False, width_chars=10, x=x_offset + 80, y=y_offset + 5)

                progress_bar = widget_factory.create_cellrendererprogress(
                    self.monitor_fixed, x=x_offset + 175, y=y_offset - 5)

                self.clock_labels[i] = clock_label
                self.progress_bars[i] = progress_bar

            y_offset += 60

            average_description_label = widget_factory.create_label(
                self.monitor_fixed, "Average:", x=16, y=y_offset + 4)

            self.average_clock_entry = widget_factory.create_entry(
                self.monitor_fixed, "N/A MHz", False, width_chars=10, x=80, y=y_offset)

            self.average_progress_bar = widget_factory.create_cellrendererprogress(
                self.monitor_fixed, x=175, y=y_offset - 15)

            package_temp_label = widget_factory.create_label(
                self.monitor_fixed, "Package Temp:", x=300, y=y_offset + 4)

            self.package_temp_entry = widget_factory.create_entry(
                self.monitor_fixed, "N/A °C", False, width_chars=10, x=400, y=y_offset)

            self.current_governor_label = widget_factory.create_label(
                self.monitor_fixed, "", x=170, y=y_offset + 50)

            self.logger.info("Monitor widgets created.")
        except Exception as e:
            self.logger.error(f"Error creating monitor widgets: {e}")

    def create_control_widgets(self):
        try:
            self.control_grid.show()
            self.cpu_min_max_checkbuttons = {}
            self.cpu_min_scales = {}
            self.cpu_max_scales = {}

            for i in range(cpu_file_search.thread_count):
                y_offset = i * 100  # Adjust vertical spacing

                cpu_min_max_checkbutton = widget_factory.create_checkbutton(
                    self.control_fixed, f"Thread {i}", None, None, x=10, y=y_offset + 27)
                cpu_min_max_checkbutton.set_active(True)
                cpu_min_max_checkbutton.set_tooltip_text("Toggle Whether Min/Max Should Be Applied")

                cpu_max_scale = widget_factory.create_scale(
                    self.control_fixed, scale_manager.update_min_max_labels, global_state.SCALE_MIN, global_state.SCALE_MAX, x=100, y=y_offset)
                cpu_max_scale.set_name(f'cpu_max_scale_{i}')
                cpu_max_scale.set_tooltip_text("Maximum Frequency Set in MHz")

                cpu_max_desc = widget_factory.create_label(
                    self.control_fixed, f"Maximum", x=430, y=y_offset)

                cpu_min_scale = widget_factory.create_scale(
                    self.control_fixed, scale_manager.update_min_max_labels, global_state.SCALE_MIN, global_state.SCALE_MAX, x=100, y=y_offset + 40)
                cpu_min_scale.set_name(f'cpu_min_scale_{i}')
                cpu_min_scale.set_tooltip_text("Minimum Frequency Set in MHz")

                cpu_min_desc = widget_factory.create_label(
                    self.control_fixed, f"Minimum", x=430, y=y_offset + 40)

                self.cpu_min_max_checkbuttons[i] = cpu_min_max_checkbutton
                self.cpu_min_scales[i] = cpu_min_scale
                self.cpu_max_scales[i] = cpu_max_scale

            apply_button = widget_factory.create_button(
                self.control_fixed, "Apply Speed Limits", cpu_manager.apply_cpu_clock_speed_limits, x=185, y=y_offset + 80)
            apply_button.set_tooltip_text("Apply Minimum And Maximum Speed Limits")

            self.governor_combobox = widget_factory.create_combobox(
                self.control_fixed, global_state.unique_governors, cpu_manager.on_governor_change, x=90, y=y_offset + 115)

            self.boost_checkbutton = widget_factory.create_checkbutton(
                self.control_fixed, "Enable CPU Boost Clock", global_state.boost_enabled, cpu_manager.toggle_boost, x=265, y=y_offset + 120)

            tdp_label = widget_factory.create_label(
                self.control_fixed, "TDP:", x=50, y=y_offset + 160)
            self.tdp_scale = widget_factory.create_scale(
                self.control_fixed, None, global_state.TDP_SCALE_MIN, global_state.TDP_SCALE_MAX, x=100, y=y_offset + 150)
            self.tdp_scale.set_value(0)
            self.tdp_scale.set_tooltip_text("Adjust the TDP in Watts")

            tdp_installed = False
            if cpu_file_search.cpu_type == "Intel":
                apply_tdp_button = widget_factory.create_button(
                    self.control_fixed, "Apply TDP", cpu_manager.set_intel_tdp, x=210, y=y_offset + 180)
                tdp_installed = True
            elif cpu_file_search.cpu_type == "Other" and ryzen_smu_installer.is_ryzen_smu_installed():
                apply_tdp_button = widget_factory.create_button(
                    self.control_fixed, "Apply TDP", cpu_manager.set_ryzen_tdp, x=210, y=y_offset + 180)
                tdp_installed = True

            if tdp_installed:
                tdp_label.show()
                self.tdp_scale.show()
                apply_tdp_button.show()
            else:
                tdp_label.hide()
                self.tdp_scale.hide()
                apply_tdp_button.hide()

                self.governor_combobox.set_y(y_offset + 160)
                self.boost_checkbutton.set_y(y_offset + 180)

            self.logger.info("Control widgets created.")
        except Exception as e:
            self.logger.error(f"Error creating control widgets: {e}")

    def create_cpu_widgets(self):
        try:
            self.create_monitor_widgets()
            self.create_control_widgets()
        except Exception as e:
            self.logger.error(f"Error creating CPU widgets: {e}")

    def add_widgets_to_gui_components(self):
        try:
            gui_components['clock_labels'] = self.clock_labels
            gui_components['progress_bars'] = self.progress_bars
            gui_components['average_clock_entry'] = self.average_clock_entry
            gui_components['average_progress_bar'] = self.average_progress_bar
            gui_components['package_temp_entry'] = self.package_temp_entry
            gui_components['current_governor_label'] = self.current_governor_label
            gui_components['cpu_min_max_checkbuttons'] = self.cpu_min_max_checkbuttons
            gui_components['cpu_min_scales'] = self.cpu_min_scales
            gui_components['cpu_max_scales'] = self.cpu_max_scales
            gui_components['governor_combobox'] = self.governor_combobox
            gui_components['boost_checkbutton'] = self.boost_checkbutton
            gui_components['tdp_scale'] = self.tdp_scale
            self.logger.info("Widgets added to gui_components.")
        except Exception as e:
            self.logger.error(f"Error adding widget to gui_components: {e}")

    def setup_gui_components(self):
        try:
            cpu_manager.setup_gui_components()
            scale_manager.setup_gui_components()
        except Exception as e:
            self.logger.error(f"Error setting up GUI components: {e}")

    def update_scales(self):
        try:
            scale_manager.load_scale_config_settings()
            scale_manager.on_disable_scale_limits_change(None)
        except Exception as e:
            self.logger.error(f"Error updating scales: {e}")

    def update_cpu_widgets(self):
        try:
            cpu_manager.update_clock_speeds()
            cpu_manager.read_package_temperature()
            cpu_manager.get_current_governor()
            cpu_manager.update_governor_combobox()
            cpu_manager.update_boost_checkbutton()
        except Exception as e:
            self.logger.error(f"Error updating CPU widgets: {e}")

    def on_window_state_event(self, window, event):
        if event.new_window_state & Gdk.WindowState.ICONIFIED:
            self.window.set_skip_taskbar_hint(True)
        else:
            self.window.set_skip_taskbar_hint(False)

    def set_window_icon(self):
        try:
            self.window.set_icon(self.pixbuf64)
        except Exception as e:
            self.logger.error(f"Error setting window icon: {e}")

    def setup_tray_icon(self):
        # Save Pixbuf to a temporary file
        temp_icon_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        self.pixbuf64.savev(temp_icon_file.name, "png", [], [])
        icon_path = temp_icon_file.name

        self.indicator = AppIndicator3.Indicator.new(
            "ClockSpeedsAppIndicator",
            icon_path,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.create_tray_menu())

        # Set the title and tooltip
        self.indicator.set_title("ClockSpeeds")

    def create_tray_menu(self):
        menu = Gtk.Menu()

        # Open main window item
        item_open = Gtk.MenuItem(label='Open ClockSpeeds')
        item_open.connect('activate', self.show_main_window)
        menu.append(item_open)

        # Hide main window item
        item_hide = Gtk.MenuItem(label='Hide')
        item_hide.connect('activate', self.hide_main_window)
        menu.append(item_hide)

        # Quit item
        item_quit = Gtk.MenuItem(label='Quit')
        item_quit.connect('activate', Gtk.main_quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def show_main_window(self, widget):
        self.window.set_skip_taskbar_hint(False)
        self.window.show_all()
        self.window.present()

    def hide_main_window(self, widget):
        self.window.set_skip_taskbar_hint(True)
        self.window.hide()

def main():
    try:
        app = ClockSpeedsApp()
        app.window.show_all()
        Gtk.main()
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error launching the main application: {e}")

if __name__ == "__main__":
    main()
