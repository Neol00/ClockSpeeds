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
    APPLY_SCRIPT_PATH = "/usr/local/bin/apply_clockspeeds_settings.sh"
    SERVICE_PATH = "/etc/systemd/system/clockspeeds.service"

    def __init__(self, logger, global_state, gui_components, widget_factory, cpu_file_search, privileged_actions):
        # References to instances
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.cpu_file_search = cpu_file_search
        self.privileged_actions = privileged_actions

        self.applied_settings = {}
        self.settings_applied = False  # Track if any settings have been applied
        self.settings_applied_on_boot = False  # Track if any settings have been applied across startups

        atexit.register(self.cleanup)

    def initialize_settings_file(self):
        try:
            # Check if the apply script or systemd service exists
            if os.path.exists(self.APPLY_SCRIPT_PATH) or os.path.exists(self.SERVICE_PATH):
                self.logger.info("Apply script or systemd service found, enabling Apply On Boot checkbutton.")
                self.settings_applied_on_boot = True
                self.global_state.ignore_boot_checkbutton_toggle = True
                self.apply_on_boot_checkbutton.set_active(True)
                self.global_state.ignore_boot_checkbutton_toggle = False
            else:
                self.logger.info("No apply script or systemd service found.")

            # Check if the tmp command settings file still exists, if so delete it and create a new one
            if os.path.exists(self.SETTINGS_FILE):
                os.remove(self.SETTINGS_FILE)
                self.logger.info("Old command settings file deleted.")
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump({}, f)
            self.logger.info("New command settings file created.")
        except Exception as e:
            self.logger.error(f"Failed to initialize command settings file: {e}")

    def cleanup(self):
        # Delete the tmp command settings file on exit
        try:
            if os.path.exists(self.SETTINGS_FILE):
                os.remove(self.SETTINGS_FILE)
                self.logger.info("Command settings file deleted.")
        except Exception as e:
            self.logger.error(f"Failed to delete command settings file: {e}")

    def setup_gui_components(self):
        try:
            self.checked_threads = self.gui_components['cpu_max_min_checkbuttons']
            self.min_scales = self.gui_components['cpu_min_scales']
            self.max_scales = self.gui_components['cpu_max_scales']
            self.governor_combobox = self.gui_components['governor_combobox']
            self.boost_checkbutton = self.gui_components['boost_checkbutton']
            self.tdp_scale = self.gui_components['tdp_scale']
            self.pbo_curve_scale = self.gui_components['pbo_curve_scale']
            self.epb_combobox = self.gui_components['epb_combobox']
            self.settings_window = self.gui_components['settings_window']
            self.apply_on_boot_checkbutton = self.gui_components['apply_on_boot_checkbutton']
        except KeyError as e:
            self.logger.error(f"Error setting up apply_settings gui_components: Component {e} not found")

    def load_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)
            self.logger.info("Command settings loaded.")
        except FileNotFoundError:
            self.logger.info("Command settings file not found.")
            self.settings = {}
        except Exception as e:
            self.logger.error(f"Failed to load command settings: {e}")
            self.settings = {}

    def save_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.applied_settings, f)
                self.settings_applied = True
                self.update_checkbutton_sensitivity()
            self.logger.info("Command settings saved successfully.")
        except Exception as e:
            self.logger.error(f"Failed to save command settings: {e}")

    def update_checkbutton_sensitivity(self):
        try:
            if self.settings_applied or self.settings_applied_on_boot:
                self.apply_on_boot_checkbutton.set_sensitive(True)
            else:
                self.apply_on_boot_checkbutton.set_sensitive(False)
        except Exception as e:
            self.logger.error(f"Failed to update the Apply On Boot checkbutton sensitivity: {e}")

    def revert_checkbutton_state(self):
        self.global_state.ignore_boot_checkbutton_toggle = True
        self.apply_on_boot_checkbutton.set_active(self.global_state.previous_boot_checkbutton_state)
        self.global_state.ignore_boot_checkbutton_toggle = False

    def create_apply_script(self):
        try:
            self.load_settings()  # Load settings before creating the script

            commands = []

            self.logger.info(f"Loaded command settings: {self.settings}")

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

            epb = self.settings.get("epb")
            if epb and epb != "Select Energy Performance Bias":
                bias_value = int(epb.split()[0])
                for i in range(self.cpu_file_search.thread_count):
                    bias_file = self.cpu_file_search.cpu_files["epb_files"].get(i)
                    if bias_file:
                        commands.append(f'echo {bias_value} | tee {bias_file} > /dev/null')
                    else:
                        self.logger.error(f"Intel energy_perf_bias files not found for thread {i}")

            if not commands:
                self.logger.error("No commands generated to execute.")
                raise ValueError("No commands to execute.")

            script_content = "#!/bin/bash\n" + "\n".join(commands)

            # Write the script content to a temporary file
            tmp_script_path = "/tmp/apply_clockspeeds_settings.sh"
            with open(tmp_script_path, 'w') as f:
                f.write(script_content)

            self.logger.info("Command apply script created successfully in /tmp/")

            return tmp_script_path
        except Exception as e:
            self.logger.error(f"Error creating command apply script: {e}")
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
            tmp_script_path = self.create_apply_script()
            if not tmp_script_path:
                raise Exception("Failed to create command apply script")

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

            # Write the service content to a temporary file
            tmp_service_path = "/tmp/clockspeeds.service"
            with open(tmp_service_path, 'w') as f:
                f.write(service_content)

            # Combine the commands for moving the files and setting up the systemd service
            command = (
                f'mv {tmp_service_path} {self.SERVICE_PATH} && '
                f'mv {tmp_script_path} {self.APPLY_SCRIPT_PATH} && '
                f'chmod +x {self.APPLY_SCRIPT_PATH} && '
                'systemctl daemon-reload && '
                'systemctl enable clockspeeds.service && '
                'systemctl start clockspeeds.service')

            # Define success and failure callbacks
            def success_callback():
                self.logger.info("Systemd service created and started.")
                self.global_state.previous_boot_checkbutton_state = True
                self.update_checkbutton_sensitivity()
                self.created_systemd_info_window()

            def failure_callback(error):
                if error == 'canceled':
                    self.logger.info("User canceled to create systemd service.")
                    self.revert_checkbutton_state()
                    self.update_checkbutton_sensitivity()
                else:
                    self.logger.error(f"Failed to create systemd service: {error}")


            # Run the combined command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error creating systemd service: {e}")
            self.revert_checkbutton_state()
            self.update_checkbutton_sensitivity()

    def remove_systemd_service(self):
        try:
            command = (
                'systemctl stop clockspeeds.service && '
                'systemctl disable clockspeeds.service && '
                f'rm {self.APPLY_SCRIPT_PATH} && '
                f'rm {self.SERVICE_PATH} && '
                'systemctl daemon-reload')

            # Define success and failure callbacks
            def success_callback():
                self.logger.info("Systemd service removed.")
                self.global_state.previous_boot_checkbutton_state = False
                self.settings_applied_on_boot = False
                self.update_checkbutton_sensitivity()
                self.removed_systemd_info_window()

            def failure_callback(error):
                if error == 'canceled':
                    self.logger.info("User canceled to remove systemd service.")
                    self.revert_checkbutton_state()
                    self.update_checkbutton_sensitivity()
                else:
                    self.logger.error(f"Failed to remove systemd service: {error}")


            # Run the command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error removing systemd service: {e}")
            self.revert_checkbutton_state()
            self.update_checkbutton_sensitivity()

    def created_systemd_info_window(self):
        # Show the information dialog for successfully creating the systemd service and script
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Successfully created systemd service and script",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=86, margin_end=86, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing created systemd service info window: {e}")

    def removed_systemd_info_window(self):
        # Show the information dialog for successfully removing the systemd service and script
        try:
            info_window = self.widget_factory.create_window("Information", self.settings_window, 300, 50)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Successfully removed systemd service and script",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=89, margin_end=89, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing removed systemd service info window: {e}")
