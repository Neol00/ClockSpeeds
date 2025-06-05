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
import subprocess
from gi.repository import Gtk, GLib

class SettingsApplier:
    APPLY_SCRIPT_PATH = "/usr/local/bin/apply_clockspeeds_settings.sh"
    SERVICE_PATH = "/etc/systemd/system/clockspeeds.service"

    def __init__(self, logger, global_state, gui_components, widget_factory, cpu_file_search, privileged_actions, config_manager):
        # References to instances
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.cpu_file_search = cpu_file_search
        self.privileged_actions = privileged_actions
        self.config_manager = config_manager

        self.applied_settings = {}
        self.settings_applied = False  # Track if any settings have been applied
        self.settings_applied_on_boot = False  # Track if any settings have been applied across startups
        self.systemd_compatible = False  # Track systemd compatibility

    def is_systemd_available(self):
        """Check if systemd is available and active as the init system"""
        try:
            # Check if running in WSL (Windows Subsystem for Linux)
            if self.is_wsl_environment():
                self.logger.info("WSL environment detected - Apply On Boot not supported")
                return False
            
            # Check if systemd is installed
            result = subprocess.run(['which', 'systemctl'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    text=True)
            if result.returncode != 0:
                self.logger.info("systemctl command not found - systemd not installed")
                return False

            # Check if systemd is running as PID 1 (the init system)
            try:
                with open('/proc/1/comm', 'r') as f:
                    init_name = f.read().strip()
                if init_name != 'systemd':
                    self.logger.info(f"System is using {init_name} as init, not systemd")
                    return False
            except (OSError, IOError) as e:
                self.logger.warning(f"Could not determine init system: {e}")
                # Continue with other checks

            # Check if systemd is actually functional
            result = subprocess.run(['systemctl', 'is-system-running'], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    text=True, 
                                    timeout=5)
            # systemctl is-system-running returns various states, but if it runs without error,
            # systemd is functional (even if the state is "degraded" or "maintenance")
            if result.returncode in [0, 1]:  # 0 = running, 1 = degraded (still functional)
                self.logger.info("Systemd is available and functional")
                return True
            else:
                self.logger.info(f"Systemd not functional: {result.stdout.strip()}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning("Timeout while checking systemd status")
            return False
        except Exception as e:
            self.logger.error(f"Error checking systemd availability: {e}")
            return False

    def is_wsl_environment(self):
        """Check if running in Windows Subsystem for Linux (WSL)"""
        try:
            # Check for WSL version file
            if os.path.exists('/proc/version'):
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    if 'microsoft' in version_info or 'wsl' in version_info:
                        return True
            
            # Check for WSL environment variable
            if os.environ.get('WSL_DISTRO_NAME') or os.environ.get('WSLENV'):
                return True
                
            # Check for Windows filesystem mounted at /mnt/c
            if os.path.exists('/mnt/c/Windows'):
                return True
                
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking WSL environment: {e}")
            return False

    def initialize_settings_file(self):
        try:
            # Check systemd compatibility first
            self.systemd_compatible = self.is_systemd_available()
            
            if self.systemd_compatible:
                # Check if the apply script or systemd service exists
                if os.path.exists(self.APPLY_SCRIPT_PATH) or os.path.exists(self.SERVICE_PATH):
                    self.logger.info("Apply script or systemd service found, enabling Apply On Boot checkbutton.")
                    self.settings_applied_on_boot = True
                    # Only set active if we have a valid checkbutton
                    if hasattr(self, 'apply_on_boot_checkbutton') and self.apply_on_boot_checkbutton is not None:
                        self.global_state.ignore_boot_checkbutton_toggle = True
                        self.apply_on_boot_checkbutton.set_active(True)
                        self.global_state.ignore_boot_checkbutton_toggle = False
                else:
                    self.logger.info("No apply script or systemd service found.")
            else:
                self.logger.info("Systemd not compatible - Apply On Boot will be disabled")

            # Always call update_checkbutton_sensitivity after checking compatibility
            self.update_checkbutton_sensitivity()

            self.logger.info("Settings applier initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize settings applier: {e}")

    def setup_gui_components(self):
        try:
            self.checked_threads = self.gui_components['cpu_max_min_checkbuttons']
            self.min_scales = self.gui_components['cpu_min_scales']
            self.max_scales = self.gui_components['cpu_max_scales']
            self.governor_combobox = self.gui_components['governor_dropdown']
            self.boost_checkbutton = self.gui_components['boost_checkbutton']
            self.tdp_scale = self.gui_components['tdp_scale']
            self.pbo_curve_scale = self.gui_components['pbo_curve_scale']
            self.epb_combobox = self.gui_components['epb_dropdown']
            self.settings_window = self.gui_components['settings_window']
            self.apply_on_boot_checkbutton = self.gui_components['apply_on_boot_checkbutton']
        except KeyError as e:
            self.logger.error(f"Error setting up apply_settings gui_components: Component {e} not found")

    def load_applied_settings(self):
        """Load applied settings from the existing config file"""
        try:
            # Load each setting type from the config file
            self.applied_settings = {}
            
            # Load min speeds
            min_speeds = {}
            for i in range(self.cpu_file_search.thread_count):
                setting_key = f"min_speed_thread_{i}"
                value = self.config_manager.get_setting('AppliedSettings', setting_key)
                if value:
                    min_speeds[str(i)] = float(value)
            if min_speeds:
                self.applied_settings["min_speeds"] = min_speeds
            
            # Load max speeds
            max_speeds = {}
            for i in range(self.cpu_file_search.thread_count):
                setting_key = f"max_speed_thread_{i}"
                value = self.config_manager.get_setting('AppliedSettings', setting_key)
                if value:
                    max_speeds[str(i)] = float(value)
            if max_speeds:
                self.applied_settings["max_speeds"] = max_speeds
            
            # Load other settings
            governor = self.config_manager.get_setting('AppliedSettings', 'governor')
            if governor:
                self.applied_settings["governor"] = governor
            
            boost = self.config_manager.get_setting('AppliedSettings', 'boost')
            if boost:
                self.applied_settings["boost"] = boost.lower() == 'true'
            
            tdp = self.config_manager.get_setting('AppliedSettings', 'tdp')
            if tdp:
                self.applied_settings["tdp"] = int(tdp)
            
            pbo_offset = self.config_manager.get_setting('AppliedSettings', 'pbo_offset')
            if pbo_offset:
                self.applied_settings["pbo_offset"] = int(pbo_offset)
            
            epb = self.config_manager.get_setting('AppliedSettings', 'epb')
            if epb:
                self.applied_settings["epb"] = epb
            
            self.logger.info("Applied settings loaded from config.")
        except Exception as e:
            self.logger.error(f"Failed to load applied settings: {e}")
            self.applied_settings = {}

    def save_settings(self):
        """Save applied settings to the existing config file"""
        try:
            # Save min speeds
            min_speeds = self.applied_settings.get("min_speeds", {})
            for thread_id, speed in min_speeds.items():
                setting_key = f"min_speed_thread_{thread_id}"
                self.config_manager.set_setting('AppliedSettings', setting_key, str(speed))
            
            # Save max speeds
            max_speeds = self.applied_settings.get("max_speeds", {})
            for thread_id, speed in max_speeds.items():
                setting_key = f"max_speed_thread_{thread_id}"
                self.config_manager.set_setting('AppliedSettings', setting_key, str(speed))
            
            # Save other settings
            if "governor" in self.applied_settings:
                self.config_manager.set_setting('AppliedSettings', 'governor', self.applied_settings["governor"])
            
            if "boost" in self.applied_settings:
                self.config_manager.set_setting('AppliedSettings', 'boost', str(self.applied_settings["boost"]))
            
            if "tdp" in self.applied_settings:
                self.config_manager.set_setting('AppliedSettings', 'tdp', str(self.applied_settings["tdp"]))
            
            if "pbo_offset" in self.applied_settings:
                self.config_manager.set_setting('AppliedSettings', 'pbo_offset', str(self.applied_settings["pbo_offset"]))
            
            if "epb" in self.applied_settings:
                self.config_manager.set_setting('AppliedSettings', 'epb', self.applied_settings["epb"])
            
            self.settings_applied = True
            self.update_checkbutton_sensitivity()
            self.logger.info("Applied settings saved to config successfully.")
        except Exception as e:
            self.logger.error(f"Failed to save applied settings: {e}")

    def update_checkbutton_sensitivity(self):
        try:
            # Only enable if systemd is compatible AND settings have been applied
            if self.apply_on_boot_checkbutton is not None:
                # If systemd is not compatible, permanently disable the checkbutton
                if not self.systemd_compatible:
                    self.apply_on_boot_checkbutton.set_sensitive(False)
                    self.global_state.ignore_boot_checkbutton_toggle = True
                    self.apply_on_boot_checkbutton.set_active(False)
                    self.global_state.ignore_boot_checkbutton_toggle = False
                    self.logger.info("Apply On Boot checkbutton disabled due to systemd incompatibility")
                elif self.settings_applied or self.settings_applied_on_boot:
                    # Only enable if systemd is compatible and settings have been applied
                    self.apply_on_boot_checkbutton.set_sensitive(True)
                else:
                    # Systemd compatible but no settings applied yet
                    self.apply_on_boot_checkbutton.set_sensitive(False)
        except Exception as e:
            self.logger.error(f"Failed to update the Apply On Boot checkbutton sensitivity: {e}")

    def revert_checkbutton_state(self):
        # Only revert if the checkbutton exists
        if self.apply_on_boot_checkbutton is not None:
            self.global_state.ignore_boot_checkbutton_toggle = True
            self.apply_on_boot_checkbutton.set_active(self.global_state.previous_boot_checkbutton_state)
            self.global_state.ignore_boot_checkbutton_toggle = False

    def create_apply_script(self):
        try:
            # Check systemd compatibility before creating script
            if not self.systemd_compatible:
                self.logger.error("Cannot create apply script: systemd not compatible")
                raise ValueError("Systemd not compatible")

            # Load settings from config instead of JSON file
            self.load_applied_settings()

            commands = []

            self.logger.info(f"Loaded applied settings: {self.applied_settings}")

            min_speeds = self.applied_settings.get("min_speeds", {})
            max_speeds = self.applied_settings.get("max_speeds", {})

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

            governor = self.applied_settings.get("governor")
            if governor and governor != "Select Governor":
                for i in range(self.cpu_file_search.thread_count):
                    governor_file = self.cpu_file_search.cpu_files["governor_files"].get(i)
                    if governor_file:
                        commands.append(f'echo {governor} | tee {governor_file} > /dev/null')
                    else:
                        self.logger.error(f"Governor file not found for thread {i}")

            boost = self.applied_settings.get("boost")
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

            tdp = self.applied_settings.get("tdp")
            if tdp is not None:
                tdp_file = self.cpu_file_search.intel_tdp_files.get("tdp")
                if tdp_file:
                    commands.append(f'echo {int(tdp)} | tee {tdp_file} > /dev/null')
                else:
                    self.logger.error("TDP file not found")

            pbo_offset = self.applied_settings.get("pbo_offset")
            if pbo_offset is not None:
                commands.append(self.create_pbo_command(pbo_offset))

            epb = self.applied_settings.get("epb")
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
            # Check systemd compatibility before proceeding
            if not self.systemd_compatible:
                self.logger.error("Cannot create systemd service: systemd not compatible")
                self.show_systemd_incompatible_dialog()
                self.revert_checkbutton_state()
                self.update_checkbutton_sensitivity()
                return

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
                    self.revert_checkbutton_state()
                    self.update_checkbutton_sensitivity()

            # Run the combined command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error creating systemd service: {e}")
            self.revert_checkbutton_state()
            self.update_checkbutton_sensitivity()

    def remove_systemd_service(self):
        try:
            # Check systemd compatibility before proceeding
            if not self.systemd_compatible:
                self.logger.error("Cannot remove systemd service: systemd not compatible")
                self.revert_checkbutton_state()
                self.update_checkbutton_sensitivity()
                return

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
                    self.revert_checkbutton_state()
                    self.update_checkbutton_sensitivity()

            # Run the command with elevated privileges
            self.privileged_actions.run_pkexec_command(command, success_callback=success_callback, failure_callback=failure_callback)

        except Exception as e:
            self.logger.error(f"Error removing systemd service: {e}")
            self.revert_checkbutton_state()
            self.update_checkbutton_sensitivity()

    def show_systemd_incompatible_dialog(self):
        """Show a dialog explaining why Apply On Boot is not available"""
        try:
            info_window = self.widget_factory.create_window("System Incompatible", self.settings_window, 400, 100)
            info_box = self.widget_factory.create_box(info_window)
            info_label = self.widget_factory.create_label(
                info_box,
                "Apply On Boot is not available on this system.\n\n"
                "This feature requires systemd, but your system is using\n"
                "a different init system (such as OpenRC, SysV init, etc.).\n\n"
                "You will need to manually apply your settings after each reboot.",
                margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)

            def on_destroy(widget):
                info_window.close()

            info_button = self.widget_factory.create_button(
                info_box, "OK", margin_start=175, margin_end=175, margin_bottom=10)
            info_button.connect("clicked", on_destroy)
            info_window.connect("close-request", on_destroy)

            info_window.present()
        except Exception as e:
            self.logger.error(f"Error showing systemd incompatible dialog: {e}")

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

    def parse_cpu_info(self, cpuinfo_file):
        """Parse CPU info to get physical cores count - needed for PBO"""
        try:
            physical_cores = 1  # Default fallback
            with open(cpuinfo_file, 'r') as file:
                for line in file:
                    if line.startswith('cpu cores'):
                        physical_cores = int(line.split(':')[1].strip())
                        break
            return None, None, physical_cores
        except Exception as e:
            self.logger.error(f"Error parsing CPU info: {e}")
            return None, None, 1