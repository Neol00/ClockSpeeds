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
import json

class DirectoryCache:
    def __init__(self, logger):
        # Initialize the logger
        self.logger = logger

        # Dictionary for the cache
        self.cache = {}

        # Cache directory and file name
        self.cache_dir_path = os.path.join(os.path.expanduser("~"), ".cache", "ClockSpeeds")
        self.cache_file_path = os.path.join(self.cache_dir_path, "directory_cache.json")

        # Ensure the cache directory exists
        self.ensure_cache_directory()

    def ensure_cache_directory(self):
        # Create the cache directory if it doesn't exist
        try:
            os.makedirs(self.cache_dir_path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {e}")

    def save_directories_to_file(self, directories):
        # Save the discovered directories and file paths to the cache file
        try:
            with open(self.cache_file_path, 'w') as cache_file:
                json.dump(directories, cache_file)
        except Exception as e:
            self.logger.error(f"Failed to save directories and file paths: {e}")

    def load_directories_from_file(self):
        # Load the discovered directories and file paths from the cache file
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r') as cache_file:
                    directories = json.load(cache_file)
                    return directories
        except Exception as e:
            self.logger.error(f"Failed to load directories and file paths: {e}")
        return None

    def add(self, path, subdirs, files):
        # Add a directory and its contents to the cache
        self.cache[path] = {'subdirs': subdirs, 'files': files}

    def get(self, path):
        # Retrieve cached directory information
        return self.cache.get(path)

    def clear(self):
        # Clear the cache
        self.cache = {}

    def cached_directory_walk(self, base_path):
        # Generator function that walks through directories using caching
        stack = [base_path]
        seen_paths = set()  # To track paths and avoid loops

        while stack:
            path = stack.pop()
            if path in seen_paths:
                continue
            seen_paths.add(path)

            cached = self.get(path)
            if cached:
                yield path, cached['subdirs'], cached['files']
                continue

            try:
                subdirs, files = [], []
                with os.scandir(path) as scanner:
                    for entry in scanner:
                        if entry.is_dir(follow_symlinks=False):
                            full_path = entry.path
                            if os.path.realpath(full_path) not in seen_paths:
                                subdirs.append(entry.name)
                                stack.append(full_path)
                        else:
                            files.append(entry.name)
                self.add(path, subdirs, files)
                yield path, subdirs, files
            except PermissionError:
                continue
            except OSError as e:
                self.logger.error(f"Access error on {path}: {e}")

class CPUFileSearch:
    def __init__(self, logger):
        # Initialize the logger
        self.logger = logger

        # Create an instance of DirectoryCache
        self.directory_cache = DirectoryCache(logger)

        # Get the total number of CPU threads
        self.thread_count = os.cpu_count()

        # Determine CPU type: 'Intel' or 'Other'
        self.cpu_type = None

        # CPU directory path
        self.cpu_directory = None

        # File paths for various CPU files
        self.cpufreq_file_paths = {
            'governor_files': "scaling_governor",
            'speed_files': "scaling_cur_freq",
            'scaling_max_files': "scaling_max_freq",
            'scaling_min_files': "scaling_min_freq",
            'cpuinfo_max_files': "cpuinfo_max_freq",
            'cpuinfo_min_files': "cpuinfo_min_freq",
            'available_governors_files': "scaling_available_governors",
            'boost_files': "boost"
        }

        # Path for package throttle time files
        self.package_throttle_time_file = "package_throttle_total_time_ms"

        # Dictionary to hold found CPU files
        self.cpu_files = {key: {} for key in self.cpufreq_file_paths.keys()}
        self.cpu_files['package_throttle_time_files'] = {}
        self.cpu_files['energy_perf_bias_files'] = {}

        # Path to the Intel boost file
        self.intel_boost_path = None

        # Path to the package temperature file
        self.package_temp_file = None

        # Dictionary to hold paths to /proc files
        self.proc_files = {'stat': None, 'cpuinfo': None, 'meminfo': None}

        # Dictionary to hold paths to Intel TDP files
        self.intel_tdp_files = {'tdp': None, 'max_tdp': None}

        # Dictionary to hold cache size files
        self.cache_files = {}

        # Load paths from cache
        cached_directories = self.directory_cache.load_directories_from_file()
        if cached_directories:
            self.load_paths_from_cache(cached_directories)
        else:
            self.initialize_cpu_files()

    def load_paths_from_cache(self, cached_directories):
        # Load cached paths for various CPU files
        self.cpu_directory = cached_directories["cpu_directory"]
        self.intel_boost_path = cached_directories["intel_boost_path"]
        self.package_temp_file = cached_directories["package_temp_file"]
        self.proc_files = cached_directories["proc_files"]
        self.intel_tdp_files = cached_directories["intel_tdp_files"]
        self.cache_files = cached_directories["cache_files"]
        self.cpu_files = {key: {int(k): v for k, v in value.items()} for key, value in cached_directories["cpu_files"].items()}
        self.cpu_type = "Intel" if self.intel_boost_path else "Other"

        # Validate the loaded paths
        self.validate_loaded_paths()

    def validate_loaded_paths(self):
        # Validate that the necessary paths are loaded correctly
        errors = []

        if not self.cpu_directory:
            errors.append("CPU directory is not set.")
        if not any(self.cpu_files['scaling_max_files'].values()):
            errors.append("Min or max frequency files are not set for any thread.")
        if not self.proc_files['stat']:
            errors.append("/proc/stat file is not set.")
        if not self.package_temp_file:
            errors.append("Package temperature file is not set.")
        
        if errors:
            for error in errors:
                self.logger.error(error)
            raise RuntimeError("Failed to load necessary CPU paths and files.")

    def initialize_cpu_files(self):
        # Initialize CPU files by discovering paths
        try:
            # Find the CPU directory first
            self.cpu_directory = self.find_cpu_directory()
            if self.cpu_directory is None:
                self.logger.warning('CPU directory is not set.')
                return

            # Initialize the search for all necessary CPU files
            for i in range(self.thread_count):
                self.find_cpufreq_files(i)
                self.find_thermal_throttle_files(i)
            self.find_no_turbo_file()
            self.find_proc_files()
            self.find_thermal_file()
            self.find_intel_tdp_files()
            self.find_cache_files()
            self.find_energy_perf_bias_files()

            # Save the paths to the cache
            directories_to_save = {
                "cpu_directory": self.cpu_directory,
                "cpu_files": self.cpu_files,
                "intel_boost_path": self.intel_boost_path,
                "package_temp_file": self.package_temp_file,
                "proc_files": self.proc_files,
                "intel_tdp_files": self.intel_tdp_files,
                "cache_files": self.cache_files,
            }
            self.directory_cache.save_directories_to_file(directories_to_save)
        except Exception as e:
            self.logger.error(f"Error initializing CPU files: {e}")

    def find_cpu_directory(self, base_path='/sys/'):
        # Find the CPU directory by scanning the base path
        try:
            for root, dirs, files in self.directory_cache.cached_directory_walk(base_path):
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

    def find_no_turbo_file(self):
        # Find the Intel no_turbo file if applicable
        try:
            if self.cpu_type == "Intel" and self.intel_boost_path is None:
                intel_pstate_path = os.path.join(self.cpu_directory, 'intel_pstate')
                for root, dirs, files in self.directory_cache.cached_directory_walk(intel_pstate_path):
                    if 'no_turbo' in files:
                        potential_path = os.path.join(root, 'no_turbo')
                        self.intel_boost_path = potential_path
                        self.cpu_files['boost_files'][0] = self.intel_boost_path
                        return
                self.logger.warning('Intel no_turbo file does not exist.')
        except Exception as e:
            self.logger.error(f"Error finding no_turbo file: {e}")

    def find_cpufreq_files(self, thread_index):
        # Find cpufreq files for each CPU thread
        try:
            thread_cpufreq_directory = os.path.join(self.cpu_directory, f"cpu{thread_index}", "cpufreq")
            found_files = 0
            for root, dirs, files in self.directory_cache.cached_directory_walk(thread_cpufreq_directory):
                for file_key, file_name in self.cpufreq_file_paths.items():
                    if file_name in files:
                        file_path = os.path.join(root, file_name)
                        self.cpu_files[file_key][thread_index] = file_path
                        found_files += 1
                if found_files == len(self.cpufreq_file_paths):
                    return

            if found_files < len(self.cpufreq_file_paths):
                for file_key, file_name in self.cpufreq_file_paths.items():
                    if not self.cpu_files[file_key].get(thread_index):
                        if not (self.cpu_type == "Intel" and file_name == "boost"):
                            self.logger.warning(f'File {file_name} for thread {thread_index} does not exist at {thread_cpufreq_directory}.')

        except Exception as e:
            self.logger.error(f"Error finding cpufreq files for thread {thread_index}: {e}")

    def find_thermal_throttle_files(self, thread_index):
        # Find thermal throttle files for Intel CPUs
        try:
            if self.cpu_type == "Intel":
                thread_thermal_throttle_directory = os.path.join(self.cpu_directory, f"cpu{thread_index}", "thermal_throttle")
                file_found = False
                for root, dirs, files in self.directory_cache.cached_directory_walk(thread_thermal_throttle_directory):
                    if self.package_throttle_time_file in files:
                        throttle_file_path = os.path.join(root, self.package_throttle_time_file)
                        self.cpu_files['package_throttle_time_files'][thread_index] = throttle_file_path
                        file_found = True
                        break
                if not file_found:
                    self.logger.warning(f'Throttle file {self.package_throttle_time_file} for thread {thread_index} does not exist at {thread_thermal_throttle_directory}.')
                    
        except Exception as e:
            self.logger.error(f"Error finding thermal throttle files for thread {thread_index}: {e}")

    def find_proc_files(self, base_path='/proc/'):
        # Find necessary /proc files
        proc_file_names = ['stat', 'cpuinfo', 'meminfo']
        need_to_find = set(proc_file_names)
        try:
            found_files = 0
            for root, dirs, files in self.directory_cache.cached_directory_walk(base_path):
                for file_name in list(need_to_find):
                    if file_name in files:
                        self.proc_files[file_name] = os.path.join(root, file_name)
                        need_to_find.remove(file_name)
                        found_files += 1
                if found_files == len(proc_file_names):
                    return

            if found_files < len(proc_file_names):
                for file_name in need_to_find:
                    self.logger.warning(f'{file_name} file not found in /proc/')

        except Exception as e:
            self.logger.error(f"Error searching for proc files: {e}")

    def find_thermal_file(self):
        # Find CPU thermal files
        potential_paths = ['/sys/class/', '/sys/devices/']
        try:
            for base_path in potential_paths:
                for root, dirs, files in self.directory_cache.cached_directory_walk(base_path):
                    for file in files:
                        if file.startswith('temp') and file.endswith('_input'):
                            full_path = os.path.join(root, file)
                            label_path = file.replace('_input', '_label')
                            full_label_path = os.path.join(root, label_path)
                            if os.path.exists(full_label_path):
                                with open(full_label_path, 'r') as label_file:
                                    label = label_file.read().strip().lower()
                                    if self.is_relevant_temp_file(label):
                                        self.package_temp_file = full_path
                                        return
        except IOError as e:
            self.logger.error(f"IOError while finding other thermal files: {e}")
        except Exception as e:
            self.logger.error(f"Error finding other thermal files: {e}")
        self.logger.warning('No thermal files found for CPU temperature monitoring.')

    def is_relevant_temp_file(self, label):
        # Determine if a temperature file is relevant
        return (self.cpu_type == 'Intel' and ('package' in label or 'cpu' in label)) or \
               (self.cpu_type != 'Intel' and 'tctl' in label)

    def find_intel_tdp_files(self):
        # Find Intel TDP files if applicable
        if self.cpu_type != "Intel":
            return

        tdp_file_names = {
            'tdp': 'constraint_0_power_limit_uw',
            'max_tdp': 'constraint_0_max_power_uw'
        }
        try:
            for root, dirs, files in os.walk('/sys/'):
                if 'intel-rapl:0' in root:
                    cached = self.directory_cache.get(root)
                    if not cached:
                        self.directory_cache.add(root, dirs, files)
                    else:
                        files = cached['files']

                    found_files = 0
                    for key, file_name in tdp_file_names.items():
                        if file_name in files:
                            self.intel_tdp_files[key] = os.path.join(root, file_name)
                            found_files += 1
                    if found_files == len(tdp_file_names):
                        return
        except Exception as e:
            self.logger.error(f"Error finding Intel TDP control file: {e}")

        for key, path in self.intel_tdp_files.items():
            if not path:
                self.logger.warning(f'Intel {key} file not found.')

    def find_cache_files(self):
        # Find cache size files in the CPU directory
        if self.cpu_directory:
            base_path = os.path.join(self.cpu_directory, 'cpu0')  # Starting with cpu0 for simplicity
            cache_path = os.path.join(base_path, 'cache')
            try:
                for root, dirs, files in self.directory_cache.cached_directory_walk(cache_path):
                    for dir_name in dirs:
                        cache_index_path = os.path.join(root, dir_name)
                        size_file = os.path.join(cache_index_path, 'size')
                        level_file = os.path.join(cache_index_path, 'level')
                        type_file = os.path.join(cache_index_path, 'type')
                        if os.path.exists(size_file) and os.path.exists(level_file) and os.path.exists(type_file):
                            with open(level_file, 'r') as lf, open(type_file, 'r') as tf, open(size_file, 'r') as sf:
                                level = lf.read().strip()
                                type_ = tf.read().strip()
                                size = sf.read().strip()
                                self.cache_files[f"{level}_{type_}"] = size
            except Exception as e:
                self.logger.error(f"Error searching cache directory: {e}")

    def find_energy_perf_bias_files(self):
        # Find energy_perf_bias files for each CPU thread
        if self.cpu_type != "Intel":
            return
        
        try:
            for i in range(self.thread_count):
                thread_power_directory = os.path.join(self.cpu_directory, f"cpu{i}", "power")
                found_files = 0
                for root, dirs, files in self.directory_cache.cached_directory_walk(thread_power_directory):
                    if 'energy_perf_bias' in files:
                        file_path = os.path.join(root, 'energy_perf_bias')
                        self.cpu_files['energy_perf_bias_files'][i] = file_path
                        found_files += 1
                        break
                if found_files == 0:
                    self.logger.warning(f'energy_perf_bias file for thread {i} does not exist at {thread_power_directory}.')

        except Exception as e:
            self.logger.error(f"Error finding energy_perf_bias files for threads: {e}")
