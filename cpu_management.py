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
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import logging
from log_setup import get_logger
from config_setup import config_manager
from privileged_actions import privileged_actions
from shared import global_state, gui_components
from cpu_file_search import cpu_file_search

class CPUManager:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.valid_governors = frozenset([
            'conservative', 
            'ondemand', 
            'performance', 
            'powersave', 
            'schedutil',
            'userspace'
        ])

        # Flag to track initial logging
        self.initial_log_done = False

        self.clock_labels = {}
        self.progress_bars = {}
        self.min_scales = {}
        self.max_scales = {}
        self.cpu_min_max_checkbuttons = {}
        self.average_clock_entry = None
        self.average_progress_bar = None
        self.package_temp_entry = None
        self.current_governor_label = None
        self.governor_combobox = None
        self.boost_checkbutton = None
        self.tdp_scale = None

        self.periodic_task_id = None

        # Load interval from config or use default
        self.update_interval = float(config_manager.get_setting("Settings", "updateinterval", "1.0"))

        self.prev_stat = self.read_stat_file()

        # Schedule all periodic tasks
        self.schedule_periodic_tasks()

    def schedule_periodic_tasks(self):
        if self.periodic_task_id:
            GLib.source_remove(self.periodic_task_id)
        self.periodic_task_id = GLib.timeout_add(int(self.update_interval * 1000), self.run_periodic_tasks)

    def run_periodic_tasks(self):
        try:
            self.update_clock_speeds()
            self.update_load()
            self.read_package_temperature()
            self.get_current_governor()
            self.update_boost_checkbutton()
        except Exception as e:
            self.logger.error("Failed to run periodic tasks: %s", e)
        self.schedule_periodic_tasks()
        return False  # Do not re-run this method automatically, rescheduling is handled explicitly

    def set_update_interval(self, interval):
        self.update_interval = round(max(0.1, min(20.0, interval)), 1)
        self.logger.info(f"Update interval set to {self.update_interval} seconds")
        config_manager.set_setting("Settings", "updateinterval", f"{self.update_interval:.1f}")
        self.schedule_periodic_tasks()

    # Set up GUI component references
    def setup_gui_components(self):
        try:
            self.clock_labels = gui_components['clock_labels']
            self.progress_bars = gui_components['progress_bars']
            self.average_clock_entry = gui_components['average_clock_entry']
            self.average_progress_bar = gui_components['average_progress_bar']
            self.package_temp_entry = gui_components['package_temp_entry']
            self.current_governor_label = gui_components['current_governor_label']
            self.cpu_min_max_checkbuttons = gui_components['cpu_min_max_checkbuttons']
            self.min_scales = gui_components['cpu_min_scales']
            self.max_scales = gui_components['cpu_max_scales']
            self.governor_combobox = gui_components['governor_combobox']
            self.boost_checkbutton = gui_components['boost_checkbutton']
            self.tdp_scale = gui_components['tdp_scale']
        except KeyError as e:
            self.logger.error(f"Error setting up CPU manager's GUI components: Component {e} not found")

    def get_cpu_info(self):
        try:
            cpuinfo_file = cpu_file_search.proc_files['cpuinfo']
            meminfo_file = cpu_file_search.proc_files['meminfo']
            if not cpuinfo_file:
                self.logger.error("cpuinfo file not found.")
                return
            if not meminfo_file:
                self.logger.error("meminfo file not found.")
                return

            model_name = None
            cache_size = None
            physical_cores = 0
            virtual_cores = cpu_file_search.thread_count

            with open(cpuinfo_file, 'r') as file:
                for line in file:
                    if line.startswith('model name'):
                        if not model_name:
                            model_name = line.split(':')[1].strip()
                    elif line.startswith('cache size'):
                        if not cache_size:
                            cache_size = line.split(':')[1].strip()
                    elif line.startswith('cpu cores'):
                        if not physical_cores:
                            physical_cores = int(line.split(':')[1].strip())

            min_allowed_freqs, max_allowed_freqs = self.get_allowed_cpu_frequency()

            total_ram = None
            try:
                with open(meminfo_file, 'r') as file:
                    for line in file:
                        if line.startswith('MemTotal'):
                            total_ram = int(line.split()[1]) // 1024  # Convert from kB to MB
                            break
            except Exception as e:
                self.logger.error(f"Error reading meminfo file: {e}")

            if not model_name:
                self.logger.warning("CPU model name not found.")
            if not cache_size:
                self.logger.warning("CPU cache size not found.")
            if not physical_cores:
                self.logger.warning("Number of physical cores not found.")
            if not min_allowed_freqs or not max_allowed_freqs:
                self.logger.warning("Allowed CPU frequencies not found.")
            if not total_ram:
                self.logger.warning("Total RAM not found.")

            cpu_info = {
                "Model Name": model_name,
                "Cache Size": cache_size,
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

    # Apply the minimum and maximum CPU clock speed limits to each CPU thread individually
    def apply_cpu_clock_speed_limits(self, widget=None):
        try:
            command_list = []

            for i in range(cpu_file_search.thread_count):
                try:
                    min_scale = self.min_scales[i]
                    max_scale = self.max_scales[i]
                    checkbutton = self.cpu_min_max_checkbuttons[i]
                except KeyError:
                    self.logger.error(f"Scale or checkbutton widget for thread {i} not found.")
                    continue

                if checkbutton.get_active():
                    try:
                        min_speed = int(min_scale.get_value())
                        max_speed = int(max_scale.get_value())
                    except ValueError:
                        self.logger.error(f"Invalid input: CPU speeds must be a number for thread {i}.")
                        continue

                    if not (0 <= min_speed <= max_speed <= 6000):
                        self.logger.error(f"Invalid input: Please enter valid CPU speed limits for thread {i}.")
                        continue

                    self.logger.info(f"Applying clockspeed for thread {i}")

                    min_frequency_in_khz = min_speed * 1000
                    max_frequency_in_khz = max_speed * 1000

                    max_file = cpu_file_search.cpu_files['scaling_max_files'].get(i)
                    min_file = cpu_file_search.cpu_files['scaling_min_files'].get(i)
                    if max_file and min_file:
                        max_command = f'echo {max_frequency_in_khz} | tee {max_file} > /dev/null'
                        min_command = f'echo {min_frequency_in_khz} | tee {min_file} > /dev/null'
                        command_list.extend([max_command, min_command])
                else:
                    self.logger.info(f"Skipping clockspeed for thread {i} as checkbutton is not active")

            if command_list:
                full_command = ' && '.join(command_list)
                success, error_message = privileged_actions.run_pkexec_command(full_command)
                if success:
                    self.update_min_max_labels()
                else:
                    if error_message == 'canceled':
                        self.logger.info("User canceled the min / max CPU clock speed limits operation.")
                    else:
                        self.logger.error(error_message)
            else:
                self.logger.error("No CPU files found to apply clock speed limits.")

        except Exception as e:
            self.logger.error(f"Error applying CPU clock speed limits: {e}")

    # Get and update the current CPU clock speeds
    def update_clock_speeds(self):
        try:
            speeds = []
            for i in range(cpu_file_search.thread_count):
                speed_file = cpu_file_search.cpu_files['speed_files'].get(i)
                if speed_file and os.path.exists(speed_file):
                    with open(speed_file, 'r') as file:
                        speed_str = file.read().strip()
                        if speed_str:
                            speed = int(speed_str) / 1000  # Convert to MHz
                            speeds.append(speed)
                            if i in self.clock_labels:
                                self.clock_labels[i].set_text(f"{speed:.0f} MHz")
                            else:
                                self.logger.error(f"No label found for thread {i}")

            if speeds:
                average_speed = sum(speeds) / len(speeds)
                self.average_clock_entry.set_text(f"{average_speed:.0f} MHz")
            else:
                self.average_clock_entry.set_text("N/A MHz")
                self.logger.warning("No valid CPU clock speeds found")

        except Exception as e:
            self.logger.error(f"Error updating CPU clock speeds: {e}")

    def read_stat_file(self):
        stat_file_path = cpu_file_search.proc_files['stat']
        if not stat_file_path:
            self.logger.error("Stat file not found.")
            return None

        with open(stat_file_path, 'r') as file:
            lines = file.readlines()

        cpu_stats = []
        for line in lines:
            if line.startswith('cpu'):
                fields = line.split()
                if len(fields) >= 5:
                    cpu_id = fields[0]
                    user = int(fields[1])
                    nice = int(fields[2])
                    system = int(fields[3])
                    idle = int(fields[4])
                    cpu_stats.append((cpu_id, user, nice, system, idle))

        return cpu_stats

    def calculate_load(self, prev_stat, curr_stat):
        loads = {}
        for (cpu_id, prev_user, prev_nice, prev_system, prev_idle), (_, curr_user, curr_nice, curr_system, curr_idle) in zip(prev_stat, curr_stat):
            prev_total = prev_user + prev_nice + prev_system + prev_idle
            curr_total = curr_user + curr_nice + curr_system + curr_idle

            total_diff = curr_total - prev_total
            idle_diff = curr_idle - prev_idle

            if total_diff != 0:
                load_percentage = 100 * (total_diff - idle_diff) / total_diff
                loads[cpu_id] = load_percentage

        return loads

    def update_load(self):
        try:
            curr_stat = self.read_stat_file()
            if not curr_stat:
                return

            loads = self.calculate_load(self.prev_stat, curr_stat)
            if loads:
                # Calculate average load
                average_load = sum(loads.values()) / len(loads)
                load_percentage = min(100, average_load)

                # Update the CellRendererProgress for average load
                model = self.average_progress_bar.get_model()
                model[0][0] = int(load_percentage)
                model[0][1] = f"{int(load_percentage)}%"

                # Update each thread's CellRendererProgress
                for cpu_id, load in loads.items():
                    if cpu_id.startswith('cpu') and cpu_id != 'cpu':  # Skip the aggregated 'cpu' line
                        thread_index = int(cpu_id.replace('cpu', ''))
                        if thread_index in self.progress_bars:
                            thread_model = self.progress_bars[thread_index].get_model()
                            thread_model[0][0] = int(load)
                            thread_model[0][1] = f"{int(load)}%"

            self.prev_stat = curr_stat

        except Exception as e:
            self.logger.error(f"Error updating average load: {e}")

    # Read and convert the package temperature from the thermal file
    def read_package_temperature(self):
        try:
            if cpu_file_search.package_temp_file:
                with open(cpu_file_search.package_temp_file, 'r') as file:
                    temp_str = file.read().strip()
                    if not self.initial_log_done:
                        self.logger.info(f"Raw temperature reading: {temp_str}")
                    if temp_str.isdigit():
                        temp_celsius = int(temp_str) / 1000  # Convert from millidegrees to degrees Celsius
                        if not self.initial_log_done:
                            self.logger.info(f"Package Temperature: {temp_celsius}°C")
                        # Update the package temperature entry
                        self.package_temp_entry.set_text(f"{int(temp_celsius)} °C")
                        return temp_celsius
                    else:
                        self.logger.error("Temperature reading is not a valid number.")
            else:
                self.logger.error("No package temperature file found.")
        except Exception as e:
            self.logger.error(f"Error reading package temperature: {e}")
        return None

    # Set CPU governor for all CPU threads
    def set_cpu_governor(self, governor):
        try:
            # Construct the command to set the governor for all CPU threads
            command_list = []
            for i in range(cpu_file_search.thread_count):
                governor_file = cpu_file_search.cpu_files['governor_files'].get(i)
                if governor_file:
                    command_list.append(f'echo "{governor}" | sudo tee {governor_file} > /dev/null')

            if command_list:
                full_command = ' && '.join(command_list)
                success, error_message = privileged_actions.run_pkexec_command(full_command)
                if success:
                    return True
                else:
                    if error_message == 'canceled':
                        self.logger.info("User canceled the toggling of CPU governors operation.")
                    else:
                        self.logger.error(error_message)
                    return False
            else:
                self.logger.error("No CPU governor files found to apply clock speed limits.")
                return False

        except Exception as e:
            self.logger.error(f"Error setting CPU governor: {e}")
            return False

    def on_governor_change(self, combobox):
        try:
            model = combobox.get_model()
            active_iter = combobox.get_active_iter()
            if active_iter is not None:
                selected_governor = model[active_iter][0]
                if selected_governor == "Select Governor":
                    return  # Do nothing if placeholder is selected

                if selected_governor in self.valid_governors:
                    success = self.set_cpu_governor(selected_governor)
                    if not success:
                        GLib.idle_add(lambda: combobox.set_active(0))  # Reset combobox on failure
                else:
                    self.logger.error(f"Invalid CPU governor selected: {selected_governor}")
                    GLib.idle_add(lambda: combobox.set_active(0))
        except Exception as e:
            self.logger.error(f"An error occurred while handling CPU governor change: {e}")

    # Get and update the current CPU governor
    def get_current_governor(self):
        try:
            # Use the governor file from thread 0
            governor_file_path = cpu_file_search.cpu_files['governor_files'].get(0)

            # If the governor file path is found
            if governor_file_path and os.path.exists(governor_file_path):
                # Read the current governor and update the label
                with open(governor_file_path, 'r') as governor_file:
                    current_governor = governor_file.read().strip()
                    self.current_governor_label.set_label(f"Current Governor: {current_governor}")
            else:
                self.logger.error("Governor file path not found for thread 0")

        except Exception as e:
            self.logger.error(f"Error updating CPU governor: {e}")

    # Update the combobox label to the found avalible governors 
    def update_governor_combobox(self):
        model = self.governor_combobox.get_model()
        model.clear()

        # First entry as a placeholder
        model.append(["Select Governor"])

        # Gather all unique governors from available governor files
        global_state.unique_governors = set()
        for i in range(cpu_file_search.thread_count):
            available_governors_file = cpu_file_search.cpu_files['available_governors_files'].get(i)
            if available_governors_file and os.path.exists(available_governors_file):
                try:
                    with open(available_governors_file, 'r') as file:
                        governors = file.read().strip().split()
                        global_state.unique_governors.update(governors)
                except Exception as e:
                    self.logger.error(f"Error reading available governors from {available_governors_file}: {e}")

        # Populate the combobox with the available governors, sorted alphabetically
        for governor in sorted(global_state.unique_governors):
            model.append([governor])

        # Set the active index to 0 which is the "Select Governor" placeholder
        self.governor_combobox.set_active(0)

    # Toggle boost on or off
    def toggle_boost(self, widget=None):
        try:
            # Invert the current status to toggle
            current_status = self.read_boost_status()
            is_enabled = not current_status

            command_list = []
            if cpu_file_search.cpu_type == "Intel" and cpu_file_search.intel_boost_path:
                value = '0' if is_enabled else '1'
                command_list.append(f'echo {value} | sudo tee {cpu_file_search.intel_boost_path} > /dev/null')
            else:
                for i in range(cpu_file_search.thread_count):
                    boost_file = cpu_file_search.cpu_files['boost_files'].get(i)
                    if boost_file:
                        value = '1' if is_enabled else '0'
                        command_list.append(f'echo {value} | sudo tee {boost_file} > /dev/null')

            if command_list:
                full_command = ' && '.join(command_list)
                success, error_message = privileged_actions.run_pkexec_command(full_command)
                if success:
                    global_state.boost_enabled = is_enabled
                    self.logger.info("CPU boost toggled successfully.")
                elif error_message == 'canceled':
                    self.logger.info("User canceled the CPU boost clock toggle operation.")
                else:
                    self.logger.error("Failed to toggle CPU boost: " + error_message)
            elif cpu_file_search.cpu_type != "Intel":  # Log only if expected to have boost control
                self.logger.info("No boost control files found for non-Intel CPUs.")
        except Exception as e:
            self.logger.error(f"Error toggling CPU boost: {e}")

    # Read the boost file to determine the checkbutton status
    def read_boost_status(self):
        if cpu_file_search.cpu_type == "Intel" and cpu_file_search.intel_boost_path and os.path.exists(cpu_file_search.intel_boost_path):
            return self.read_boost_file(cpu_file_search.intel_boost_path, intel=True)
        else:
            # Check for the first valid boost file in non-Intel CPUs
            for boost_file in cpu_file_search.cpu_files['boost_files'].values():
                if os.path.exists(boost_file):
                    return self.read_boost_file(boost_file)
            # If no valid files found, log and hide the checkbutton
            self.logger.info("No valid boost control files found.")
            self.boost_checkbutton.hide()
            return None

    def read_boost_file(self, file_path, intel=False):
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

    # Update the boost checkbutton status
    def update_boost_checkbutton(self):
        try:
            current_status = self.read_boost_status()
            if current_status is None:
                self.boost_checkbutton.hide()
            else:
                self.boost_checkbutton.show()
                if self.boost_checkbutton.get_active() != current_status:
                    self.boost_checkbutton.handler_block_by_func(self.toggle_boost)
                    self.boost_checkbutton.set_active(current_status)
                    self.boost_checkbutton.handler_unblock_by_func(self.toggle_boost)
                if not self.initial_log_done:
                    self.logger.info(f"Boost checkbutton status updated to reflect system status: {'enabled' if current_status else 'disabled'}.")
                    self.initial_log_done = True  # Set the flag after the initial log

        except Exception as e:
            self.logger.error(f"Error updating boost checkbutton status: {e}")
            return None

    def set_intel_tdp(self, widget=None):
        try:
            if cpu_file_search.cpu_type != "Intel":
                self.logger.error("TDP control is only supported for Intel CPUs.")
                return False

            tdp_file = cpu_file_search.intel_tdp_files['tdp']
            if not tdp_file or not os.path.exists(tdp_file):
                self.logger.error("Intel TDP control file not found.")
                return False

            tdp_scale = self.tdp_scale
            tdp_value_watts = tdp_scale.get_value()
            tdp_value_microwatts = int(tdp_value_watts * 1_000_000)  # Convert watts to microwatts

            command = f'echo {tdp_value_microwatts} | sudo tee {tdp_file} > /dev/null'
            success, error_message = privileged_actions.run_pkexec_command(command)
            if success:
                self.logger.info(f"Successfully set TDP to {tdp_value_microwatts} microwatts.")
                return True
            else:
                if error_message == 'canceled':
                    self.logger.info("User canceled the TDP control operation.")
                else:
                    self.logger.error(error_message)
                return False
        except Exception as e:
            self.logger.error(f"Error setting Intel TDP: {e}")
            return False

    def set_ryzen_tdp(self, widget=None):
        try:
            if cpu_file_search.cpu_type != "Other":
                self.logger.error("TDP control with ryzen_smu is only supported for AMD Ryzen CPUs.")
                return False

            tdp_scale = self.tdp_scale
            tdp_value_watts = tdp_scale.get_value()
            tdp_value_milliwatts = int(tdp_value_watts * 1000)  # Convert watts to milliwatts

            # Prepare the command
            command = f"printf '%0*x' 48 {tdp_value_milliwatts} | fold -w 2 | tac | tr -d '\\n' | xxd -r -p | sudo tee /sys/kernel/ryzen_smu_drv/smu_args && printf '\\x53' | sudo tee /sys/kernel/ryzen_smu_drv/rsmu_cmd"

            # Execute the command
            process = privileged_actions.run_pkexec_command(command)
            if process.returncode == 0:
                self.logger.info(f"Successfully set TDP to {tdp_value_milliwatts} milliwatts for Ryzen CPU.")
                return True
            else:
                self.logger.error(f"Failed to set TDP for Ryzen CPU. Error: {process.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error setting Ryzen TDP: {e}")
            return False

    # Use the allowed cpu frequency files in the searched file location
    def get_allowed_cpu_frequency(self):
        try:
            min_allowed_freqs = []
            max_allowed_freqs = []

            for i in range(cpu_file_search.thread_count):
                min_freq_file = cpu_file_search.cpu_files['cpuinfo_min_files'].get(i)
                max_freq_file = cpu_file_search.cpu_files['cpuinfo_max_files'].get(i)

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
        max_tdp_file = cpu_file_search.intel_tdp_files['max_tdp']
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

# Create an instance of CPUManager
cpu_manager = CPUManager()
