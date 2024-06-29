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

import json
import os
import atexit
from gi.repository import Gtk, GLib

class SettingsApplier:
    SETTINGS_FILE = "/tmp/clockspeeds_settings.json"

    def __init__(self, logger, global_state, gui_components, cpu_file_search, privileged_actions):
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.cpu_file_search = cpu_file_search
        self.privileged_actions = privileged_actions

        self.applied_settings = {}
        self.settings_applied = False  # Track if any settings have been applied

        self.initialize_settings_file()

        atexit.register(self.cleanup)

    def initialize_settings_file(self):
        try:
            if os.path.exists(self.SETTINGS_FILE):
                os.remove(self.SETTINGS_FILE)
                self.logger.info("Old settings file deleted.")
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump({}, f)
            self.logger.info("New settings file created.")
        except Exception as e:
            self.logger.error(f"Failed to initialize settings file: {e}")

    def cleanup(self):
        try:
            if os.path.exists(self.SETTINGS_FILE):
                os.remove(self.SETTINGS_FILE)
                self.logger.info("Settings file deleted.")
        except Exception as e:
            self.logger.error(f"Failed to delete settings file: {e}")

    def setup_gui_components(self):
        try:
            self.checked_threads = self.gui_components['cpu_max_min_checkbuttons']
            self.min_scales = self.gui_components['cpu_min_scales']
            self.max_scales = self.gui_components['cpu_max_scales']
            self.governor_combobox = self.gui_components['governor_combobox']
            self.boost_checkbutton = self.gui_components['boost_checkbutton']
            self.tdp_scale = self.gui_components['tdp_scale']
            self.pbo_curve_scale = self.gui_components['pbo_curve_scale']
            self.energy_perf_bias_combobox = self.gui_components['energy_perf_bias_combobox']
            self.apply_on_boot_checkbutton = self.gui_components['apply_on_boot_checkbutton']
        except KeyError as e:
            self.logger.error(f"Error setting up GUI components: Component {e} not found")

    def load_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)
            self.logger.info("Settings loaded.")
        except FileNotFoundError:
            self.logger.info("Settings file not found.")
            self.settings = {}
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            self.settings = {}

    def save_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.applied_settings, f)
                self.settings_applied = True
                self.update_checkbutton_sensitivity()
            self.logger.info("Settings saved successfully.")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")

    def update_checkbutton_sensitivity(self):
        try:
            if self.settings_applied:
                self.apply_on_boot_checkbutton.set_sensitive(True)
            else:
                self.apply_on_boot_checkbutton.set_sensitive(False)
        except Exception as e:
            self.logger.error(f"Failed to update the Apply On Boot checkbutton sensitivity: {e}")

    def revert_checkbutton_state(self):
        self.global_state.ignore_boot_checkbutton_toggle = True
        self.apply_on_boot_checkbutton.set_active(self.global_state.previous_boot_checkbutton_state)
        self.global_state.ignore_boot_checkbutton_toggle = False

    def apply_ui_settings(self):
        for i, value in self.settings.get("min_speeds", {}).items():
            self.min_scales[int(i)].set_value(value)
        for i, value in self.settings.get("max_speeds", {}).items():
            self.max_scales[int(i)].set_value(value)
        for i, value in self.settings.get("checked_threads", {}).items():
            self.checked_threads[int(i)].set_active(value)

        governor = self.settings.get("governor")
        if governor:
            model = self.governor_combobox.get_model()
            for i, row in enumerate(model):
                if row[0] == governor:
                    self.governor_combobox.set_active(i)
                    break

        self.boost_checkbutton.set_active(self.settings.get("boost", False))
        self.tdp_scale.set_value(self.settings.get("tdp", 0))
        self.pbo_curve_scale.set_value(self.settings.get("pbo_offset", 0))

        energy_perf_bias = self.settings.get("energy_perf_bias")
        if energy_perf_bias:
            model = self.energy_perf_bias_combobox.get_model()
            for i, row in enumerate(model):
                if row[0] == energy_perf_bias:
                    self.energy_perf_bias_combobox.set_active(i)
                    break
        self.logger.info("Settings loaded into UI.")

    def create_apply_script(self):
        try:
            self.load_settings()  # Load settings before creating the script

            commands = []

            self.logger.info(f"Loaded settings: {self.settings}")

            min_speeds = self.settings.get("min_speeds", {})
            max_speeds = self.settings.get("max_speeds", {})

            for i in range(self.cpu_file_search.thread_count):
                min_speed = min_speeds.get(str(i))
                max_speed = max_speeds.get(str(i))
                self.logger.info(f"Thread {i}: min_speed={min_speed}, max_speed={max_speed}")

                if min_speed is not None and max_speed is not None:
                    max_file = self.cpu_file_search.cpu_files['scaling_max_files'].get(i)
                    min_file = self.cpu_file_search.cpu_files['scaling_min_files'].get(i)
                    if max_file and min_file:
                        commands.append(f'echo {int(max_speed * 1000)} | tee {max_file} > /dev/null')
                        commands.append(f'echo {int(min_speed * 1000)} | tee {min_file} > /dev/null')
                    else:
                        self.logger.error(f"Scaling min or max file not found for thread {i}")

            governor = self.settings.get("governor")
            if governor and governor != "Select Governor":
                for i in range(self.cpu_file_search.thread_count):
                    governor_file = self.cpu_file_search.cpu_files["governor_files"].get(i)
                    if governor_file:
                        commands.append(f'echo {governor} | tee {governor_file} > /dev/null')
                    else:
                        self.logger.error(f"Governor file not found for thread {i}")

            boost = self.settings.get("boost")
            if boost is not None:
                if self.cpu_file_search.cpu_type == "Other":
                    boost_value = '1' if boost else '0'
                    for i in range(self.cpu_file_search.thread_count):
                        boost_file = self.cpu_file_search.cpu_files["boost_files"].get(i)
                        if boost_file:
                            commands.append(f'echo {boost_value} | tee {boost_file} > /dev/null')
                        else:
                            self.logger.error(f"Boost file not found for thread {i}")
                else:
                    boost_value = '0' if boost else '1'
                    boost_file = self.cpu_file_search.intel_boost_path
                    if boost_file:
                        commands.append(f'echo {boost_value} | tee {boost_file} > /dev/null')
                    else:
                        self.logger.error(f"Intel boost file not found")

            tdp = self.settings.get("tdp")
            if tdp is not None:
                tdp_file = self.cpu_file_search.intel_tdp_files.get("tdp")
                if tdp_file:
                    commands.append(f'echo {int(tdp)} | tee {tdp_file} > /dev/null')
                else:
                    self.logger.error("TDP file not found")

            pbo_offset = self.settings.get("pbo_offset")
            if pbo_offset is not None:
                commands.append(self.create_pbo_command(pbo_offset))

            energy_perf_bias = self.settings.get("energy_perf_bias")
            if energy_perf_bias and energy_perf_bias != "Select Energy Perf Bias":
                bias_value = int(energy_perf_bias.split()[0])
                for i in range(self.cpu_file_search.thread_count):
                    bias_file = self.cpu_file_search.cpu_files["energy_perf_bias_files"].get(i)
                    if bias_file:
                        commands.append(f'echo {bias_value} | tee {bias_file} > /dev/null')
                    else:
                        self.logger.error(f"Energy performance bias file not found for thread {i}")

            if not commands:
                self.logger.error("No commands generated to execute.")
                raise ValueError("No commands to execute.")

            script_content = "#!/bin/bash\n" + "\n".join(commands)

            # Write the script content to a temporary file
            tmp_script_path = "/tmp/apply_clockspeeds_settings.sh"
            with open(tmp_script_path, 'w') as f:
                f.write(script_content)

            self.logger.info("Apply script created successfully in /tmp/")

            return tmp_script_path

        except Exception as e:
            self.logger.error(f"Error creating apply script: {e}")
            return None

    def create_pbo_command(self, offset_value):
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

    def create_systemd_service(self):
        try:
            apply_script_path = self.create_apply_script()
            if not apply_script_path:
                raise Exception("Failed to create apply script")

            service_content = f"""[Unit]
Description=Apply ClockSpeeds settings

[Service]
Type=oneshot
ExecStart=/usr/local/bin/apply_clockspeeds_settings.sh
TimeoutSec=0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

            service_path = "/etc/systemd/system/clockspeeds.service"

            # Write the service content to a temporary file
            tmp_service_path = "/tmp/clockspeeds.service"
            with open(tmp_service_path, 'w') as f:
                f.write(service_content)

            # Combine the commands for moving the files and setting up the systemd service
            command = (
                f'mv {tmp_service_path} {service_path} && '
                f'mv {apply_script_path} /usr/local/bin/apply_clockspeeds_settings.sh && '
                f'chmod +x /usr/local/bin/apply_clockspeeds_settings.sh && '
                'systemctl daemon-reload && '
                'systemctl enable clockspeeds.service && '
                'systemctl start clockspeeds.service'
            )

            # Define success and failure callbacks
            def success_callback():
                self.logger.info("Systemd service created and started.")
                self.global_state.previous_boot_checkbutton_state = True
                self.apply_on_boot_checkbutton.set_sensitive(True)

            def failure_callback(error):
                self.logger.error(f"Failed to create systemd service: {error}")
                self.revert_checkbutton_state()
                self.apply_on_boot_checkbutton.set_sensitive(True)

            # Run the combined command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error creating systemd service: {e}")
            self.revert_checkbutton_state()
            self.apply_on_boot_checkbutton.set_sensitive(True)

    def remove_systemd_service(self):
        try:
            command = (
                "rm /usr/local/bin/apply_clockspeeds_settings.sh && "
                "systemctl stop clockspeeds.service && "
                "systemctl disable clockspeeds.service && "
                "rm /etc/systemd/system/clockspeeds.service && "
                "systemctl daemon-reload")

            # Define success and failure callbacks
            def success_callback():
                self.logger.info("Systemd service removed.")
                self.global_state.previous_boot_checkbutton_state = False
                self.apply_on_boot_checkbutton.set_sensitive(True)

            def failure_callback(error):
                self.logger.error(f"Failed to remove systemd service: {error}")
                self.revert_checkbutton_state()
                self.apply_on_boot_checkbutton.set_sensitive(True)

            # Run the command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error removing systemd service: {e}")
            self.revert_checkbutton_state()
            self.apply_on_boot_checkbutton.set_sensitive(True)

if __name__ == "__main__":
    applier = SettingsApplier(logger, gui_components, cpu_file_search, privileged_actions)
    applier.apply_all_settings()
