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
import logging
from log_setup import get_logger

class CPUFileSearch:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.thread_count = os.cpu_count()
        self.cpu_type = None  # 'Intel' or 'Other'
        self.intel_boost_path = None
        self.package_temp_file = None
        self.proc_files = {'stat': None, 'cpuinfo': None, 'meminfo': None}
        self.intel_tdp_files = {'tdp': None, 'max_tdp': None}
        
        self.file_paths = {
            'governor_files': "scaling_governor",
            'speed_files': "scaling_cur_freq",
            'scaling_max_files': "scaling_max_freq",
            'scaling_min_files': "scaling_min_freq",
            'cpuinfo_max_files': "cpuinfo_max_freq",
            'cpuinfo_min_files': "cpuinfo_min_freq",
            'available_governors_files': "scaling_available_governors",
            'boost_files': "boost"
        }
        
        self.cpu_files = {key: {} for key in self.file_paths.keys()}
        
        self.initialize_cpu_files()

    def find_cpu_directory(self, base_path='/sys/'):
        try:
            for root, dirs, files in os.walk(base_path):
                if 'intel_pstate' in dirs and 'cpu' in root:
                    self.cpu_type = "Intel"
                    return root
                if 'cpufreq' in dirs and 'cpu' in root:
                    self.cpu_type = "Other"
                    return root
        except Exception as e:
            self.logger.error(f"Error searching CPU directory: {e}")

        self.logger.warning('CPU directory not found.')
        return None

    def search_for_no_turbo(self, intel_base_path):
        potential_path = os.path.join(intel_base_path, 'intel_pstate', 'no_turbo')
        if os.path.exists(potential_path):
            self.intel_boost_path = potential_path
            self.cpu_files['boost_files'][0] = self.intel_boost_path
        else:
            self.logger.warning('Intel no_turbo file does not exist.')

    def find_cpu_files(self, thread_index):
        cpu_files_directory = self.find_cpu_directory()
        if cpu_files_directory is None:
            self.logger.warning('Failed to find the CPU files directory.')
            return

        if self.cpu_type == "Intel" and self.intel_boost_path is None:
            self.search_for_no_turbo(cpu_files_directory)

        thread_files_directory = os.path.join(cpu_files_directory, f"cpu{thread_index}", "cpufreq")

        for file_key, file_name in self.file_paths.items():
            file_path = os.path.join(thread_files_directory, file_name)
            if os.path.exists(file_path):
                self.cpu_files[file_key][thread_index] = file_path
            else:
                self.logger.warning(f'File {file_name} for thread {thread_index} does not exist.')

    def find_proc_files(self, base_path='/proc/'):
        proc_file_names = ['stat', 'cpuinfo', 'meminfo']
        
        try:
            for root, dirs, files in os.walk(base_path):
                for file_name in proc_file_names:
                    if file_name in files:
                        self.proc_files[file_name] = os.path.join(root, file_name)
                        self.logger.info(f'Found {file_name} file: {self.proc_files[file_name]}')
                if all(self.proc_files.values()):
                    break
        except Exception as e:
            self.logger.error(f"Error searching for proc files: {e}")

        for key, path in self.proc_files.items():
            if not path:
                self.logger.warning(f'{key} file not found in /proc/')

    def find_thermal_file(self):
        potential_paths = [
            '/sys/class/',
            '/sys/devices/',
        ]
        try:
            for path in potential_paths:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.startswith('temp') and file.endswith('_input'):
                            label_path = file.replace('_input', '_label')
                            full_label_path = os.path.join(root, label_path)
                            if os.path.exists(full_label_path):
                                with open(full_label_path, 'r') as label_file:
                                    label = label_file.read().strip().lower()
                                    if 'package' in label or 'cpu' in label:
                                        full_path = os.path.join(root, file)
                                        self.package_temp_file = full_path
                                        self.logger.info(f'Found thermal file: {full_path}')
                                        return
                            else:
                                full_path = os.path.join(root, file)
                                self.package_temp_file = full_path
                                self.logger.info(f'Found thermal file without label: {full_path}')
                                return
        except IOError as e:
            self.logger.error(f"IOError while finding other thermal files: {e}")
        except Exception as e:
            self.logger.error(f"Error finding other thermal files: {e}")

        if not self.package_temp_file:
            self.logger.warning('No thermal files found for non-Intel CPU.')

    def find_intel_tdp_files(self):
        if self.cpu_type != "Intel":
            return

        tdp_file_names = {
            'tdp': 'constraint_0_power_limit_uw',
            'max_tdp': 'constraint_0_max_power_uw'
        }
        try:
            for root, dirs, files in os.walk('/sys/'):
                if 'intel-rapl:0' in root:
                    for key, file_name in tdp_file_names.items():
                        if file_name in files:
                            self.intel_tdp_files[key] = os.path.join(root, file_name)
                            self.logger.info(f'Found Intel {key} file: {self.intel_tdp_files[key]}')
                    if all(self.intel_tdp_files.values()):
                        return
        except Exception as e:
            self.logger.error(f"Error finding Intel TDP control file: {e}")

        for key, path in self.intel_tdp_files.items():
            if not path:
                self.logger.warning(f'Intel {key} file not found.')

    def initialize_cpu_files(self):
        for i in range(self.thread_count):
            self.find_cpu_files(i)
        self.find_thermal_file()
        self.find_proc_files()
        self.find_intel_tdp_files()

cpu_file_search = CPUFileSearch()
