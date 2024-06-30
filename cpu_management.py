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
from gi.repository import GLib

class CPUManager:
    def __init__(self, config_manager, logger, global_state, gui_components, widget_factory, cpu_file_search, privileged_actions, settings_applier):
        # References to instances
        self.config_manager = config_manager
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.cpu_file_search = cpu_file_search
        self.privileged_actions = privileged_actions
        self.settings_applier = settings_applier

        self.monitor_task_id = None
        self.control_task_id = None

        # Load update interval from config or use default
        self.update_interval = float(config_manager.get_setting("Settings", "update_interval", "1.0"))

        # Read initial CPU statistics
        self.prev_stat = self.read_stat_file()

        # Schedule monitor tasks on startup
        self.schedule_monitor_tasks()

        # Initialize dictionaries for GUI components
        self.clock_labels = {}
        self.progress_bars = {}
        self.min_scales = {}
        self.max_scales = {}
        self.cpu_max_min_checkbuttons = {}

        # GUI components
        self.average_clock_entry = None
        self.average_progress_bar = None
        self.package_temp_entry = None
        self.current_governor_label = None
        self.governor_combobox = None
        self.boost_checkbutton = None
        self.tdp_scale = None
        self.pbo_curve_scale = None

        # Set of valid CPU governors
        self.valid_governors = frozenset([
            'conservative', 
            'ondemand', 
            'performance', 
            'powersave', 
            'schedutil',
            'userspace'
        ])

        # Keep track if CPU is currently throttling
        self.prev_package_throttle_time = [None] * self.cpu_file_search.thread_count
        self.is_throttling = False  # Flag to indicate if throttling is occurring

    def schedule_monitor_tasks(self):
        # Schedule the periodic tasks for the monitor tab with the specified update interval
        if self.monitor_task_id:
            GLib.source_remove(self.monitor_task_id)
        self.monitor_task_id = GLib.timeout_add(int(self.update_interval * 1000), self.run_monitor_tasks)

    def stop_monitor_tasks(self):
        # Stop the periodic tasks for the monitor tab if they are running
        if self.monitor_task_id:
            GLib.source_remove(self.monitor_task_id)
            self.monitor_task_id = None

    def schedule_control_tasks(self):
        # Schedule the periodic tasks for the control tab with the specified update interval
        if self.control_task_id:
            GLib.source_remove(self.control_task_id)
        self.control_task_id = GLib.timeout_add(int(self.update_interval * 1000), self.run_control_tasks)

    def stop_control_tasks(self):
        # Stop the periodic tasks for the control tab if they are running
        if self.control_task_id:
            GLib.source_remove(self.control_task_id)
            self.control_task_id = None

    def run_monitor_tasks(self):
        # Execute the monitor tasks periodically
        try:
            self.update_clock_speeds()
            self.update_load()
            self.read_package_temperature()
            self.get_current_governor()
            self.update_throttle()
        except Exception as e:
            self.logger.error("Failed to run monitor tasks: %s", e)

        # Only reschedule if the task ID is still valid (i.e., periodic tasks haven't been stopped)
        if self.monitor_task_id:
            self.schedule_monitor_tasks()
        return False  # Prevent automatic re-scheduling by GLib

    def run_control_tasks(self):
        # Execute the control tasks periodically
        try:
            self.update_boost_checkbutton()
        except Exception as e:
            self.logger.error("Failed to run control tasks: %s", e)
        if self.control_task_id:
            self.schedule_control_tasks()
        return False  # Prevent automatic re-scheduling by GLib

    def set_update_interval(self, interval):
        # Set the update interval for periodic tasks and save it in the config
        self.update_interval = round(max(0.1, min(20.0, interval)), 1)
        self.logger.info(f"Update interval set to {self.update_interval} seconds")
        self.config_manager.set_setting("Settings", "update_interval", f"{self.update_interval:.1f}")
        self.schedule_monitor_tasks()
        self.schedule_control_tasks()

    def setup_gui_components(self):
        # Set up references to GUI components from the shared dictionary
        try:
            self.clock_labels = self.gui_components['clock_labels']
            self.progress_bars = self.gui_components['progress_bars']
            self.average_clock_entry = self.gui_components['average_clock_entry']
            self.average_progress_bar = self.gui_components['average_progress_bar']
            self.package_temp_entry = self.gui_components['package_temp_entry']
            self.current_governor_label = self.gui_components['current_governor_label']
            self.thermal_throttle_label = self.gui_components['thermal_throttle_label']
            self.cpu_max_min_checkbuttons = self.gui_components['cpu_max_min_checkbuttons']
            self.max_scales = self.gui_components['cpu_max_scales']
            self.min_scales = self.gui_components['cpu_min_scales']
            self.apply_max_min_button = self.gui_components['apply_max_min_button']
            self.governor_combobox = self.gui_components['governor_combobox']
            self.boost_checkbutton = self.gui_components['boost_checkbutton']
            self.tdp_scale = self.gui_components['tdp_scale']
            self.apply_tdp_button = self.gui_components['apply_tdp_button']
            self.pbo_curve_scale = self.gui_components['pbo_curve_scale']
            self.apply_pbo_button = self.gui_components['apply_pbo_button']
            self.epb_combobox = self.gui_components['epb_combobox']
        except KeyError as e:
            self.logger.error(f"Error setting up cpu_manager gui_components: Component {e} not found")

    def get_cpu_info(self):
        # Retrieve CPU information from system files
        try:
            cpuinfo_file = self.cpu_file_search.proc_files['cpuinfo']
            meminfo_file = self.cpu_file_search.proc_files['meminfo']

            if not cpuinfo_file:
                self.logger.error("cpuinfo file not found.")
                return
            if not meminfo_file:
                self.logger.error("meminfo file not found.")
                return

            # Parse the CPU information
            model_name, cache_sizes, physical_cores, virtual_cores = self.parse_cpu_info(cpuinfo_file)
            
            # Get the allowed CPU frequencies
            min_allowed_freqs, max_allowed_freqs = self.get_allowed_cpu_frequency()
            
            # Read the total RAM from the meminfo file
            total_ram = self.read_total_ram(meminfo_file)

            # Filter out any None cache sizes
            cache_sizes = {k: v for k, v in cache_sizes.items() if v is not None}

            # Create a dictionary with the CPU information
            cpu_info = {
                "Model Name": model_name,
                "Cache Sizes": cache_sizes,
                "Total RAM (MB)": total_ram,
                "Min (MHz)": min_allowed_freqs,
                "Max (MHz)": max_allowed_freqs,
                "Physical Cores": physical_cores,
                "Virtual Cores (Threads)": virtual_cores
            }

            return cpu_info

        except Exception as e:
            self.logger.error(f"Error retrieving CPU info: {e}")
            return None

    def parse_cpu_info(self, cpuinfo_file):
        # Parse the CPU information file to extract model name and core counts
        try:
            model_name = None  # To store the CPU model name
            # Dictionary to store cache sizes
            cache_sizes = {
                "L1 Data": self.cpu_file_search.cache_files.get("1_Data", None),
                "L1 Instruction": self.cpu_file_search.cache_files.get("1_Instruction", None),
                "L2 Unified": self.cpu_file_search.cache_files.get("2_Unified", None),
                "L3 Unified": self.cpu_file_search.cache_files.get("3_Unified", None)
            }
            physical_cores = 0  # To store the number of physical cores
            virtual_cores = self.cpu_file_search.thread_count  # Number of virtual cores (threads)

            # Open the cpuinfo file and read line by line
            with open(cpuinfo_file, 'r') as file:
                for line in file:
                    # Extract the model name
                    if line.startswith('model name') and not model_name:
                        model_name = line.split(':')[1].strip()
                    # Extract the number of physical cores
                    elif line.startswith('cpu cores') and not physical_cores:
                        physical_cores = int(line.split(':')[1].strip())

            return model_name, cache_sizes, physical_cores, virtual_cores

        except Exception as e:
            self.logger.error(f"Error parsing CPU info: {e}")
            return None

    def read_total_ram(self, meminfo_file):
        # Read the total RAM from the meminfo file
        total_ram = None
        try:
            with open(meminfo_file, 'r') as file:
                for line in file:
                    if line.startswith('MemTotal'):
                        total_ram = int(line.split()[1]) // 1024  # Convert to MB
                        break
        except Exception as e:
            self.logger.error(f"Error reading meminfo file: {e}")
        return total_ram

    def get_allowed_cpu_frequency(self):
        # Get the allowed CPU frequencies from the system files
        try:
            min_allowed_freqs = []
            max_allowed_freqs = []

            for i in range(self.cpu_file_search.thread_count):
                min_freq_file = self.cpu_file_search.cpu_files['cpuinfo_min_files'].get(i)
                max_freq_file = self.cpu_file_search.cpu_files['cpuinfo_max_files'].get(i)

                if not min_freq_file or not max_freq_file:
                    self.logger.error(f"Min or max frequency file not found for thread {i}")
                    continue

                with open(min_freq_file) as min_file:
                    min_freq_mhz = int(min_file.read()) / 1000  # Convert from kHz to MHz
                    min_allowed_freqs.append(min_freq_mhz)

                with open(max_freq_file) as max_file:
                    max_freq_mhz = int(max_file.read()) / 1000  # Convert from kHz to MHz
                    max_allowed_freqs.append(max_freq_mhz)

            return min_allowed_freqs, max_allowed_freqs

        except Exception as e:
            self.logger.error(f"Error getting CPU frequencies: {e}")
            return None, None

    def get_allowed_tdp_values(self):
        # First, check the CPU type
        cpu_type = self.cpu_file_search.cpu_type

        # If CPU type is "Other", do not proceed with TDP check and log no error
        if cpu_type == "Other":
            return None

        # Get the allowed TDP values for Intel CPUs
        max_tdp_file = self.cpu_file_search.intel_tdp_files['max_tdp']
        if not max_tdp_file or not os.path.exists(max_tdp_file):
            self.logger.error("Intel Max TDP file not found.")
            return None

        try:
            with open(max_tdp_file, 'r') as f:
                max_tdp_value_uw = int(f.read().strip())
                max_tdp_value_w = max_tdp_value_uw / 1_000_000  # Convert from microwatts to watts
                return max_tdp_value_w
        except ValueError as e:
            self.logger.error(f"Error reading TDP values: {e}")
            return None

    def read_cpu_speeds(self):
        # Read the current CPU speeds from the appropriate system files
        speeds = []  # List to store the CPU speeds
        for i in range(self.cpu_file_search.thread_count):
            speed_file = self.cpu_file_search.cpu_files['speed_files'].get(i)
            if speed_file and os.path.exists(speed_file):
                with open(speed_file, 'r') as file:
                    speed_str = file.read().strip()
                    if speed_str:
                        speed = int(speed_str) / 1000  # Convert to MHz
                        speeds.append((i, speed))
        return speeds

    def update_clock_labels(self, speeds):
        # Update the clock speed labels in the GUI
        for i, speed in speeds:
            if i in self.clock_labels:
                if self.global_state.display_ghz:
                    display_speed = speed / 1000
                    unit = "GHz"
                    self.clock_labels[i].set_text(f"{display_speed:.2f} {unit}")
                else:
                    display_speed = speed
                    unit = "MHz"
                    self.clock_labels[i].set_text(f"{display_speed:.0f} {unit}")
            else:
                self.logger.error(f"No label found for thread {i}")

    def update_average_speed(self, speeds):
        # Update the average clock speed label in the GUI
        if speeds:
            average_speed = sum(speed for _, speed in speeds) / len(speeds)
            if self.global_state.display_ghz:
                display_speed = average_speed / 1000
                unit = "GHz"
                self.average_clock_entry.set_text(f"{display_speed:.2f} {unit}")
            else:
                display_speed = average_speed
                unit = "MHz"
                self.average_clock_entry.set_text(f"{display_speed:.0f} {unit}")
        else:
            self.logger.error("No valid CPU clock speeds found")

    def update_clock_speeds(self):
        # Update the clock speeds of all CPU threads
        try:
            speeds = self.read_cpu_speeds()
            self.update_clock_labels(speeds)
            self.update_average_speed(speeds)
        except Exception as e:
            self.logger.error(f"Error updating CPU clock speeds: {e}")

    def read_stat_file(self):
        # Read the CPU statistics from the stat file
        stat_file_path = self.cpu_file_search.proc_files['stat']
        if not stat_file_path:
            self.logger.error("Stat file not found.")
            return None

        # Open the stat file and read its lines
        with open(stat_file_path, 'r') as file:
            lines = file.readlines()

        cpu_stats = []  # List to store the CPU statistics
        for line in lines:
            if line.startswith('cpu'):
                fields = line.split()
                if len(fields) >= 5:
                    cpu_id = fields[0]  # Extract CPU ID
                    user = int(fields[1])  # Extract user time
                    nice = int(fields[2])  # Extract nice time
                    system = int(fields[3])  # Extract system time
                    idle = int(fields[4])  # Extract idle time
                    cpu_stats.append((cpu_id, user, nice, system, idle))

        return cpu_stats

    def calculate_load(self, prev_stat, curr_stat):
        # Calculate the CPU load based on previous and current statistics
        loads = {}  # Dictionary to store the load percentages for each CPU

        for (cpu_id, prev_user, prev_nice, prev_system, prev_idle), \
            (_, curr_user, curr_nice, curr_system, curr_idle) in zip(prev_stat, curr_stat):

            # Calculate the previous and current total times
            prev_total = prev_user + prev_nice + prev_system + prev_idle
            curr_total = curr_user + curr_nice + curr_system + curr_idle

            # Calculate the differences in total and idle times
            total_diff = curr_total - prev_total
            idle_diff = curr_idle - prev_idle

            if total_diff != 0:
                # Calculate the load percentage
                load_percentage = 100 * (total_diff - idle_diff) / total_diff
                loads[cpu_id] = load_percentage

        return loads

    def update_average_load(self, loads):
        try:
            # Calculate and update the average CPU load
            average_load = sum(loads.values()) / len(loads)  # Calculate the average load
            load_percentage = min(100, average_load)  # Ensure the load percentage does not exceed 100%

            # Update the progress bar and the label if the load percentage has changed
            progress_bar, percentage_label = self.average_progress_bar
            if int(progress_bar.get_fraction() * 100) != int(load_percentage):
                progress_bar.set_fraction(load_percentage / 100.0)
                percentage_label.set_text(f"{int(load_percentage)}%")
        except Exception as e:
            self.logger.error(f"Error updating average load: {e}")

    def update_thread_loads(self, loads):
        try:
            # Update the load for each CPU thread
            for cpu_id, load in loads.items():
                if cpu_id.startswith('cpu') and cpu_id != 'cpu':  # Skip the aggregated 'cpu' line
                    thread_index = int(cpu_id.replace('cpu', ''))
                    if thread_index in self.progress_bars:
                        # Update the progress bar and the label if the load has changed
                        progress_bar, percentage_label = self.progress_bars[thread_index]
                        if int(progress_bar.get_fraction() * 100) != int(load):
                            progress_bar.set_fraction(load / 100.0)
                            percentage_label.set_text(f"{int(load)}%")
        except Exception as e:
            self.logger.error(f"Error updating thread loads: {e}")

    def update_load(self):
        # Update the CPU load for all threads
        try:
            curr_stat = self.read_stat_file()  # Read the current CPU statistics
            if not curr_stat:
                return

            # Calculate the load based on the previous and current statistics
            loads = self.calculate_load(self.prev_stat, curr_stat)
            if loads:
                self.update_average_load(loads)  # Update the average load
                self.update_thread_loads(loads)  # Update the load for each thread
            # Update the previous statistics
            self.prev_stat = curr_stat
        except Exception as e:
            self.logger.error(f"Error updating average load: {e}")

    def read_and_parse_temperature(self):
        # Read and parse the CPU package temperature
        try:
            if self.cpu_file_search.package_temp_file:
                if os.path.exists(self.cpu_file_search.package_temp_file):
                    with open(self.cpu_file_search.package_temp_file, 'r') as file:
                        temp_str = file.read().strip()
                        if temp_str.isdigit():
                            temp_celsius = int(temp_str) / 1000  # Convert from millidegrees to degrees Celsius
                            return temp_str, temp_celsius
                        else:
                            self.logger.error("Temperature reading is not a valid number.")
            self.logger.error("No package temperature file found.")
        except Exception as e:
            self.logger.error(f"Error parsing temperature file: {e}")
        return None, None

    def read_package_temperature(self):
        # Read the CPU package temperature and update the GUI
        try:
            temp_str, temp_celsius = self.read_and_parse_temperature()
            if temp_celsius is not None:
                self.package_temp_entry.set_text(f"{int(temp_celsius)} °C")
                return temp_celsius
        except Exception as e:
            self.logger.error(f"Error reading package temperature: {e}")
        return None

    def update_throttle(self):
        # Update the thermal throttle status in the GUI
        try:
            self.is_throttling = False  # Reset the throttling flag initially

            if self.cpu_file_search.cpu_type == "Intel":
                # Intel specific throttle file check
                for i in range(self.cpu_file_search.thread_count):
                    package_throttle_time_file = self.cpu_file_search.cpu_files.get('package_throttle_time_files', {}).get(i)

                    if package_throttle_time_file and os.path.exists(package_throttle_time_file):
                        with open(package_throttle_time_file, 'r') as file:
                            current_throttle_time = int(file.read().strip())

                        if self.prev_package_throttle_time[i] is not None:
                            if current_throttle_time > self.prev_package_throttle_time[i]:
                                self.is_throttling = True  # Set throttling flag if throttle time has increased

                        self.prev_package_throttle_time[i] = current_throttle_time  # Update previous throttle time

            if self.is_throttling:
                # Update the label to indicate throttling
                self.thermal_throttle_label.set_markup('<span foreground="red">Throttling</span>')
                self.thermal_throttle_label.set_visible(True)
            else:
                self.thermal_throttle_label.set_visible(False)

        except Exception as e:
            self.logger.error(f"Error updating throttle widget: {e}")

    def read_and_get_governor(self):
        # Read the current CPU governor from the system file
        governor_file_path = self.cpu_file_search.cpu_files['governor_files'].get(0)
        if governor_file_path and os.path.exists(governor_file_path):
            with open(governor_file_path, 'r') as governor_file:
                return governor_file.read().strip()
        return None

    def get_current_governor(self):
        # Get the current CPU governor and update the GUI
        try:
            current_governor = self.read_and_get_governor()
            if current_governor:
                self.current_governor_label.set_label(f"Current Governor: {current_governor}")
            else:
                self.logger.error("Governor file path not found or could not read the governor for thread 0")
        except Exception as e:
            self.logger.error(f"Error updating CPU governor: {e}")

    def update_governor_combobox(self):
        # Update the governor combobox with available governors
        model = self.governor_combobox.get_model()
        model.clear()

        # Add the first entry as a placeholder
        model.append(["Select Governor"])

        # Gather all unique governors from available governor files
        self.global_state.unique_governors = set()
        for i in range(self.cpu_file_search.thread_count):
            available_governors_file = self.cpu_file_search.cpu_files['available_governors_files'].get(i)
            if available_governors_file and os.path.exists(available_governors_file):
                try:
                    with open(available_governors_file, 'r') as file:
                        governors = file.read().strip().split()
                        self.global_state.unique_governors.update(governors)
                except Exception as e:
                    self.logger.error(f"Error reading available governors from {available_governors_file}: {e}")

        # Populate the combobox with the available governors, sorted alphabetically
        for governor in sorted(self.global_state.unique_governors):
            model.append([governor])

        # Set the active index to 0, which is the "Select Governor" placeholder
        self.governor_combobox.set_active(0)

    def find_boost_type(self):
        # Determine which boost files are correct for your CPU type
        if self.cpu_file_search.cpu_type == "Intel" and self.cpu_file_search.intel_boost_path and os.path.exists(self.cpu_file_search.intel_boost_path):
            return self.read_boost_file(self.cpu_file_search.intel_boost_path, intel=True)
        else:
            for boost_file in self.cpu_file_search.cpu_files['boost_files'].values():
                if os.path.exists(boost_file):
                    return self.read_boost_file(boost_file)
            self.logger.info("No valid boost control files found.")
            self.boost_checkbutton.hide()
            return None

    def read_boost_file(self, file_path, intel=False):
        # Read the boost file to determine the current boost status
        try:
            with open(file_path, 'r') as file:
                content = file.read().strip()
                if content in ['0', '1']:
                    return content == ('0' if intel else '1')
                else:
                    self.logger.error(f"Unexpected content in boost file at {file_path}: {content}")
                    return False
        except IOError as e:
            self.logger.info(f"Boost file not accessible at {file_path}: {e}")
            return False

    def update_boost_checkbutton(self):
        # Update the boost checkbutton status in the GUI
        try:
            current_status = self.find_boost_type()
            if current_status is None:
                self.boost_checkbutton.set_visible(False)
            else:
                self.boost_checkbutton.set_visible(True)
                if self.boost_checkbutton.get_active() != current_status:
                    self.boost_checkbutton.handler_block_by_func(self.toggle_boost)
                    self.boost_checkbutton.set_active(current_status)
                    self.boost_checkbutton.handler_unblock_by_func(self.toggle_boost)
        except Exception as e:
            self.logger.error(f"Error updating boost checkbutton status: {e}")

    def apply_cpu_clock_speed_limits(self, widget=None):
        try:
            command_list = []  # List to store commands

            def set_apply_min_max_sensitivity():
                self.apply_max_min_button.set_sensitive(False)

            def retrieve_widgets_for_thread(i):
                try:
                    min_scale = self.min_scales[i]
                    max_scale = self.max_scales[i]
                    checkbutton = self.cpu_max_min_checkbuttons[i]
                    return min_scale, max_scale, checkbutton
                except KeyError:
                    self.logger.error(f"Scale or checkbutton widget for thread {i} not found.")
                    return None, None, None

            def validate_and_get_speeds(min_scale, max_scale, i):
                try:
                    min_speed = int(min_scale.get_value())
                    max_speed = int(max_scale.get_value())
                    if not (0 <= min_speed <= max_speed <= 6000):
                        self.logger.error(f"Invalid input: Please enter valid CPU speed limits for thread {i}.")
                        return None, None
                    return min_speed, max_speed
                except ValueError:
                    self.logger.error(f"Invalid input: CPU speeds must be a number for thread {i}.")
                    return None, None

            def get_frequency_commands(min_speed, max_speed, i):
                min_frequency_in_khz = min_speed * 1000
                max_frequency_in_khz = max_speed * 1000

                max_file = self.cpu_file_search.cpu_files['scaling_max_files'].get(i)
                min_file = self.cpu_file_search.cpu_files['scaling_min_files'].get(i)

                if max_file and min_file:
                    max_command = f'echo {max_frequency_in_khz} | tee {max_file} > /dev/null'
                    min_command = f'echo {min_frequency_in_khz} | tee {min_file} > /dev/null'
                    return max_command, min_command
                return None, None

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info("Successfully applied CPU clock speed limits.")
                self.apply_max_min_button.set_sensitive(True)
                try:
                    self.settings_applier.applied_settings["min_speeds"] = {i: self.min_scales[i].get_value() for i in self.min_scales if self.min_scales[i].get_value() > 0}
                    self.settings_applier.applied_settings["max_speeds"] = {i: self.max_scales[i].get_value() for i in self.max_scales if self.max_scales[i].get_value() > 0}
                    self.settings_applier.applied_settings["checked_threads"] = {i: self.cpu_max_min_checkbuttons[i].get_active() for i in self.cpu_max_min_checkbuttons}
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied min/max speeds and checked threads: {e}")

            def failure_callback(error_message):
                self.apply_max_min_button.set_sensitive(True)
                if error_message == 'canceled':
                    self.logger.info("User canceled the min / max frequency pkexec prompt.")
                else:
                    self.logger.error(f"Failed to apply CPU clock speed limits: {error_message}")

            any_active_checkbutton = False

            set_apply_min_max_sensitivity()

            for i in range(self.cpu_file_search.thread_count):
                min_scale, max_scale, checkbutton = retrieve_widgets_for_thread(i)
                if min_scale is None or max_scale is None or checkbutton is None:
                    continue  # Skip to the next thread if widgets are not found

                if checkbutton.get_active():
                    any_active_checkbutton = True
                    min_speed, max_speed = validate_and_get_speeds(min_scale, max_scale, i)
                    if min_speed is None or max_speed is None:
                        continue  # Skip to the next thread if speeds are invalid

                    self.logger.info(f"Applying clock speed for thread {i}")
                    max_command, min_command = get_frequency_commands(min_speed, max_speed, i)
                    if max_command is None or min_command is None:
                        self.logger.error(f"Failed to get frequency commands for thread {i}")
                        continue  # Skip to the next thread if commands are invalid

                    command_list.extend([max_command, min_command])
                else:
                    self.logger.info(f"Skipping clock speed for thread {i} as checkbutton is not active")

            if command_list:
                full_command = ' && '.join(command_list)
                self.privileged_actions.run_pkexec_command(full_command, success_callback=success_callback, failure_callback=failure_callback)
            else:
                if not any_active_checkbutton:
                    self.apply_max_min_button.set_sensitive(True)
                    self.show_speed_limits_info_window("You need at least one thread enabled to apply the speed limits.")
                else:
                    self.logger.info("No valid commands generated to apply clock speed limits.")
                    self.apply_max_min_button.set_sensitive(True)

        except Exception as e:
            self.logger.error(f"Error applying CPU clock speed limits: {e}")
            self.apply_max_min_button.set_sensitive(True)

    def show_speed_limits_info_window(self, message):
        # Show the information dialog for the speed limits info
        try:
            speed_limits_info_window = self.widget_factory.create_window("Information", None, 300, 50)

            speed_limits_info_box = self.widget_factory.create_box(speed_limits_info_window)

            speed_limits_info_label = self.widget_factory.create_label(
                speed_limits_info_box,
                message,
                margin_start=10, margin_end=10, margin_top=10)

            def on_destroy(widget):
                speed_limits_info_window.close()

            speed_limits_info_button = self.widget_factory.create_button(
                speed_limits_info_box, "OK", margin_start=131, margin_end=131, margin_bottom=10)
            speed_limits_info_button.connect("clicked", on_destroy)

            speed_limits_info_window.connect("close-request", on_destroy)

            speed_limits_info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing speed limits info dialog: {e}")

    def set_cpu_governor(self, combobox):
        # Handle the change of CPU governor from the combobox and set it
        try:
            def set_governor_combobox_sensitivity():
                self.governor_combobox.set_sensitive(False)

            def get_selected_governor():
                # Retrieve the selected governor from the combobox
                model = combobox.get_model()
                active_iter = combobox.get_active_iter()
                if active_iter is not None:
                    return model[active_iter][0]
                return None

            def get_command_list(governor):
                # Generate the command list to set the governor
                command_list = []
                for i in range(self.cpu_file_search.thread_count):
                    governor_file = self.cpu_file_search.cpu_files['governor_files'].get(i)
                    if governor_file:
                        command_list.append(f'echo "{governor}" | sudo tee {governor_file} > /dev/null')
                return command_list

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info(f"Successfully set governor to {selected_governor}")
                self.governor_combobox.set_sensitive(True)
                try:
                    self.settings_applier.applied_settings["governor"] = selected_governor
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied governor setting: {e}")

            def failure_callback(error):
                # Handle failures from pkexec command
                if error == 'canceled':
                    self.logger.info("User canceled the governor change pkexec prompt.")
                    GLib.idle_add(lambda: combobox.set_active(0))
                else:
                    self.logger.error(f"Failed to set CPU governor: {error}")
                self.governor_combobox.set_sensitive(True)

            selected_governor = get_selected_governor()
            if selected_governor == "Select Governor" or selected_governor is None:
                return  # Do nothing if placeholder or no selection is made

            set_governor_combobox_sensitivity()

            if selected_governor in self.valid_governors:
                self.logger.info(f"Setting CPU governor to: {selected_governor}")
                command_list = get_command_list(selected_governor)

                if command_list:
                    # If there are commands to execute, run them with pkexec
                    full_command = ' && '.join(command_list)
                    self.privileged_actions.run_pkexec_command(full_command, success_callback=success_callback, failure_callback=failure_callback)
                else:
                    self.logger.error("No CPU governor files found to apply clock speed limits.")
                    self.governor_combobox.set_sensitive(True)
            else:
                self.logger.error(f"Invalid CPU governor selected: {selected_governor}")
                self.governor_combobox.set_sensitive(True)
                GLib.idle_add(lambda: combobox.set_active(0))

        except Exception as e:
            self.logger.error(f"An error occurred while handling CPU governor change: {e}")
            self.governor_combobox.set_sensitive(True)

    def toggle_boost(self, widget=None):
        # Toggle the CPU boost clock on or off
        try:
            self.stop_control_tasks()  # Stop the control tasks while the method is running
            current_status = self.find_boost_type()  # Get the current boost status
            is_enabled = not current_status  # Determine the new boost status

            def set_toggle_boost_sensitivity():
                self.boost_checkbutton.set_sensitive(False)

            def get_command_list():
                # Generate the command list to toggle boost
                command_list = []
                if self.cpu_file_search.cpu_type == "Intel" and self.cpu_file_search.intel_boost_path:
                    # For Intel CPUs, set the boost value based on the new status
                    value = '0' if is_enabled else '1'
                    command_list.append(f'echo {value} | sudo tee {self.cpu_file_search.intel_boost_path} > /dev/null')
                else:
                    # For non-Intel CPUs, toggle the boost for each thread
                    for i in range(self.cpu_file_search.thread_count):
                        boost_file = self.cpu_file_search.cpu_files['boost_files'].get(i)
                        if boost_file:
                            value = '1' if is_enabled else '0'
                            command_list.append(f'echo {value} | sudo tee {boost_file} > /dev/null')
                return command_list

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info("CPU boost toggled successfully.")
                self.global_state.boost_enabled = is_enabled  # Update the global state
                self.schedule_control_tasks()  # Restart the control tasks
                self.boost_checkbutton.set_sensitive(True)
                self.update_boost_checkbutton()  # Update the checkbutton state
                try:
                    # Update applied settings
                    self.settings_applier.applied_settings["boost"] = is_enabled
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied boost setting: {e}")

            def failure_callback(error_message):
                # Handle failures from pkexec command
                if error_message == 'canceled':
                    self.logger.info("User canceled the CPU boost pkexec prompt.")
                else:
                    self.logger.error("Failed to toggle CPU boost: " + error_message)
                self.schedule_control_tasks()
                self.boost_checkbutton.set_sensitive(True)
                self.update_boost_checkbutton()

            set_toggle_boost_sensitivity()

            command_list = get_command_list()

            if command_list:
                # If there are commands to execute, run them with pkexec
                full_command = ' && '.join(command_list)
                self.privileged_actions.run_pkexec_command(full_command, success_callback=success_callback, failure_callback=failure_callback)
            else:
                self.logger.error("No commands generated to toggle CPU boost.")
                self.schedule_control_tasks()
                self.boost_checkbutton.set_sensitive(True)
                self.update_boost_checkbutton()
        except Exception as e:
            self.logger.error(f"Error toggling CPU boost: {e}")
            self.schedule_control_tasks()
            self.boost_checkbutton.set_sensitive(True)
            self.update_boost_checkbutton()

    def set_intel_tdp(self, widget=None):
        # Set the TDP (Thermal Design Power) for Intel CPUs
        try:
            def set_tdp_sensitivity():
                self.apply_tdp_button.set_sensitive(False)

            def validate_cpu_type():
                # Validate the CPU type
                if self.cpu_file_search.cpu_type != "Intel":
                    self.logger.error("TDP control is only supported for Intel CPUs.")
                    return False
                return True

            def get_tdp_file():
                # Retrieve the TDP control file path
                tdp_file = self.cpu_file_search.intel_tdp_files['tdp']
                if not tdp_file or not os.path.exists(tdp_file):
                    self.logger.error("Intel TDP control file not found.")
                    return None
                return tdp_file

            def create_tdp_command(tdp_file):
                # Create the command to set the TDP value
                tdp_value_watts = self.tdp_scale.get_value()
                tdp_value_microwatts = int(tdp_value_watts * 1_000_000)  # Convert watts to microwatts
                command = f'echo {tdp_value_microwatts} | sudo tee {tdp_file} > /dev/null'
                return command, tdp_value_microwatts

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info(f"Successfully set TDP.")
                self.apply_tdp_button.set_sensitive(True)
                try:
                    self.settings_applier.applied_settings["tdp"] = tdp_value_microwatts
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied Intel TDP setting: {e}")

            def failure_callback(error_message):
                # Handle failures from pkexec command
                if error_message == 'canceled':
                    self.logger.info("User canceled the TDP pkexec prompt.")
                else:
                    self.logger.error(f"Failed to set TDP for Intel CPU: {error_message}")
                self.apply_tdp_button.set_sensitive(True)

            if not validate_cpu_type():
                return False

            tdp_file = get_tdp_file()
            if not tdp_file:
                return False

            set_tdp_sensitivity()

            command, tdp_value_microwatts = create_tdp_command(tdp_file)
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)
            return True

        except Exception as e:
            self.logger.error(f"Error setting Intel TDP: {e}")
            self.apply_tdp_button.set_sensitive(True)
            return False

    def set_ryzen_tdp(self, widget=None):
        # Set the TDP (Thermal Design Power) for AMD Ryzen CPUs
        try:
            def set_tdp_sensitivity():
                self.apply_tdp_button.set_sensitive(False)

            def validate_cpu_type():
                # Validate the CPU type
                if self.cpu_file_search.cpu_type != "Other":
                    self.logger.error("TDP control with ryzen_smu is only supported for AMD Ryzen CPUs.")
                    return False
                return True

            def create_tdp_command():
                # Create the command to set the TDP value
                tdp_value_watts = self.tdp_scale.get_value()
                tdp_value_milliwatts = int(tdp_value_watts * 1000)  # Convert watts to milliwatts
                command = f"printf '%0*x' 48 {tdp_value_milliwatts} | fold -w 2 | tac | tr -d '\\n' | xxd -r -p | sudo tee /sys/kernel/ryzen_smu_drv/smu_args && printf '\\x53' | sudo tee /sys/kernel/ryzen_smu_drv/rsmu_cmd"
                return command, tdp_value_milliwatts

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info(f"Successfully set TDP")
                self.apply_tdp_button.set_sensitive(True)
                try:
                    self.settings_applier.applied_settings["tdp"] = tdp_value_milliwatts
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied AMD Ryzen TDP setting: {e}")

            def failure_callback(error_message):
                # Handle failures from pkexec command
                if error_message == 'canceled':
                    self.logger.info("User canceled the TDP pkexec prompt.")
                else:
                    self.logger.error(f"Failed to set TDP for Ryzen CPU: {error_message}")
                self.apply_tdp_button.set_sensitive(True)

            if not validate_cpu_type():
                return False

            if not self.global_state.is_ryzen_smu_installed():
                self.logger.error("ryzen_smu is not installed.")
                return False

            set_tdp_sensitivity()

            command, tdp_value_milliwatts = create_tdp_command()
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)
            return True

        except Exception as e:
            self.logger.error(f"Error setting Ryzen TDP: {e}")
            self.apply_tdp_button.set_sensitive(True)
            return False

    def set_pbo_curve_offset(self, widget=None):
        try:
            def set_pbo_sensitivity():
                self.apply_pbo_button.set_sensitive(False)

            def validate_cpu_type():
                # Validate the CPU type
                if self.cpu_file_search.cpu_type != "Other":
                    self.logger.error("PBO curve setting is only supported for AMD Ryzen CPUs.")
                    return False
                return True

            def create_pbo_command(offset_value):
                # Create the command to set the PBO curve offset value for all cores
                commands = []
                physical_cores = self.parse_cpu_info(self.cpu_file_search.proc_files['cpuinfo'])[2]

                # Convert the positive offset_value to a negative offset
                offset_value = -offset_value

                # Convert offset_value to a 16-bit two's complement representation
                if offset_value < 0:
                    offset_value = (1 << 16) + offset_value

                for core_id in range(physical_cores):
                    # Calculate smu_args_value for each core
                    smu_args_value = ((core_id & 8) << 5 | core_id & 7) << 20 | (offset_value & 0xFFFF)
                    commands.append(f"echo {smu_args_value} | sudo tee /sys/kernel/ryzen_smu_drv/smu_args > /dev/null")
                    commands.append(f"echo '0x35' | sudo tee /sys/kernel/ryzen_smu_drv/mp1_smu_cmd > /dev/null")
                return " && ".join(commands)

            def success_callback():
                self.logger.info(f"Successfully set PBO curve offset using scale value.")
                self.apply_pbo_button.set_sensitive(True)
                try:
                    # Update applied_settings with the PBO offset value
                    self.settings_applier.applied_settings["pbo_offset"] = offset_value
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied PBO offset setting: {e}")

            def failure_callback(error_message):
                # Handle failures from pkexec command
                if error_message == 'canceled':
                    self.logger.info("User canceled the PBO curve setting pkexec prompt.")
                else:
                    self.logger.error(f"Failed to set PBO curve offset: {error_message}")
                self.apply_pbo_button.set_sensitive(True)

            if not validate_cpu_type():
                return False

            if not self.global_state.is_ryzen_smu_installed():
                self.logger.error("ryzen_smu is not installed.")
                return False

            set_pbo_sensitivity()

            offset_value = int(self.pbo_curve_scale.get_value())
            command = create_pbo_command(offset_value)
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)
            return True

        except Exception as e:
            self.logger.error(f"Error setting PBO curve offset: {e}")
            self.apply_pbo_button.set_sensitive(True)
            return False

    def set_energy_perf_bias(self, combobox):
        try:
            def set_epb_sensitivity():
                self.epb_combobox.set_sensitive(False)

            def get_selected_bias():
                # Retrieve the selected EPB from the combobox
                model = combobox.get_model()
                active_iter = combobox.get_active_iter()
                if active_iter is not None:
                    return model[active_iter][0]
                return None

            def get_command_list(bias_value):
                # Generate the command list to set the EPB
                command_list = []
                epb_files = self.cpu_file_search.cpu_files['epb_files']
                for i in range(self.cpu_file_search.thread_count):
                    bias_file = epb_files.get(i)
                    if bias_file:
                        command_list.append(f'echo "{bias_value}" | sudo tee {bias_file} > /dev/null')
                return command_list

            def success_callback():
                # Handle successful execution of pkexec command
                self.logger.info(f"Successfully set Intel EPB to {selected_bias}")
                self.epb_combobox.set_sensitive(True)
                try:
                    self.settings_applier.applied_settings["epb"] = selected_bias
                    self.settings_applier.save_settings()
                except Exception as e:
                    self.logger.error(f"Error saving the applied Intel EPB setting: {e}")

            def failure_callback(error):
                # Handle failures from pkexec command
                if error == 'canceled':
                    self.logger.info("User canceled the Intel EPB change pkexec prompt.")
                    GLib.idle_add(lambda: combobox.set_active(0))
                else:
                    self.logger.error(f"Failed to set Intel EPB: {error}")
                self.epb_combobox.set_sensitive(True)

            selected_bias = get_selected_bias()
            if selected_bias == "Select Energy Performance Bias" or selected_bias is None:
                return  # Do nothing if placeholder or no selection is made

            set_epb_sensitivity()

            bias_value = int(selected_bias.split()[0])
            valid_bias_values = frozenset([0, 4, 6, 8, 15])

            if bias_value in valid_bias_values:
                self.logger.info(f"Setting Intel EPB to: {selected_bias}")
                command_list = get_command_list(bias_value)

                if command_list:
                    # If there are commands to execute, run them with pkexec
                    full_command = ' && '.join(command_list)
                    self.privileged_actions.run_pkexec_command(full_command, success_callback=success_callback, failure_callback=failure_callback)
                else:
                    self.logger.error("No Intel EPB files found to apply the bias value.")
                    self.epb_combobox.set_sensitive(True)
            else:
                self.logger.error(f"Invalid Intel EPB value selected: {selected_bias}")
                GLib.idle_add(lambda: combobox.set_active(0))
                self.epb_combobox.set_sensitive(True)

        except Exception as e:
            self.epb_combobox.set_sensitive(True)
            self.logger.error(f"An error occurred while handling Intel EPB change: {e}")
