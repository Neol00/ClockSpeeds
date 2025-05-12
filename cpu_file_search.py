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
        self.cpu_files['epb_files'] = {}

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
        self.cpu_directory = cached_directories.get("cpu_directory")
        self.intel_boost_path = cached_directories.get("intel_boost_path")
        self.package_temp_file = cached_directories.get("package_temp_file")
        self.proc_files = cached_directories.get("proc_files", {})
        self.intel_tdp_files = cached_directories.get("intel_tdp_files", {})
        self.cache_files = cached_directories.get("cache_files", {})
        
        # Handle potential missing keys in the cached data
        cpu_files = cached_directories.get("cpu_files", {})
        self.cpu_files = {}
        for key in ['scaling_max_files', 'scaling_min_files', 'speed_files', 'governor_files', 
                    'cpuinfo_max_files', 'cpuinfo_min_files', 'available_governors_files', 
                    'boost_files', 'package_throttle_time_files', 'epb_files']:
            if key in cpu_files:
                self.cpu_files[key] = {int(k): v for k, v in cpu_files[key].items()}
            else:
                self.cpu_files[key] = {}
        
        self.cpu_type = "Intel" if self.intel_boost_path else "Other"

        # Validate the loaded paths
        self.validate_loaded_paths()

    def validate_loaded_paths(self):
        # Validate that the necessary paths are loaded correctly
        errors = []
        should_reinitialize = False

        if not self.cpu_directory:
            errors.append("CPU directory is not set.")
            should_reinitialize = True
        if not any(self.cpu_files['scaling_max_files'].values()):
            errors.append("Min or max frequency files are not set for any thread.")
            should_reinitialize = True
        if not self.proc_files['stat']:
            errors.append("/proc/stat file is not set.")
            should_reinitialize = True
        
        # Package temperature file is optional, don't raise error for it
        if not self.package_temp_file:
            self.logger.info("Package temperature file is not set. This is common on some systems.")
        
        # If we encountered critical errors that would prevent proper functioning
        if should_reinitialize:
            for error in errors:
                self.logger.error(error)
            self.logger.warning("Some essential CPU paths are missing, reinitializing...")
            # Clear the cache file to force reinitialization
            if os.path.exists(self.directory_cache.cache_file_path):
                try:
                    os.remove(self.directory_cache.cache_file_path)
                    self.logger.info("Removed invalid cache file to reinitialize paths")
                except Exception as e:
                    self.logger.error(f"Failed to remove cache file: {e}")
            # Reinitialize files
            self.initialize_cpu_files()
            # Validate again to make sure critical paths are now available
            if not self.cpu_directory or not any(self.cpu_files['scaling_max_files'].values()) or not self.proc_files['stat']:
                for error in errors:
                    self.logger.error(error)
                raise RuntimeError("Failed to initialize necessary CPU paths and files.")

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
                        # Only log boost file as warning in debug mode, it's normal for it to be missing on ARM
                        if file_name == "boost":
                            self.logger.debug(f'File {file_name} for thread {thread_index} does not exist at {thread_cpufreq_directory}.')
                        else:
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
        potential_paths = [
            '/sys/class/thermal/',  # Most common location for thermal zones
            '/sys/class/',          # Fallback to broader search
            '/sys/devices/',        # Your ARM device structure
        ]
        
        # Priority list for temperature files/sensors
        # Higher priority items are checked first
        cpu_sensor_priorities = [
            # Intel/AMD patterns
            ('package', 'temp'),
            ('coretemp', 'temp'),
            ('cpu', 'package'),
            ('tctl', ''),  # AMD Ryzen thermal control
            ('tccd', ''),  # AMD Ryzen CCD thermal
            ('die', 'temp'),
            
            # ARM patterns
            ('cpu', 'thermal'),
            ('cpu', 'temp'),
            ('soc', 'thermal'),
            ('cluster', 'thermal'),
            ('thermal', 'cpu'),
            ('cpu_thermal', ''),
            ('tsens', 'cpu'),
            
            # Generic patterns (lower priority)
            ('cpu', ''),
            ('thermal', ''),
            ('temp', ''),
        ]
        
        try:
            # First, try thermal zones (most reliable method)
            thermal_zone_file = self._find_thermal_zone_file()
            if thermal_zone_file:
                self.package_temp_file = thermal_zone_file
                self.logger.info(f"Found thermal zone file: {thermal_zone_file}")
                return
            
            # If thermal zones don't work, search through device tree
            for base_path in potential_paths:
                if not os.path.exists(base_path):
                    continue
                    
                # Search for temperature files
                temp_files = self._search_temperature_files(base_path)
                
                if temp_files:
                    # Sort by priority and select the best match
                    best_file = self._select_best_thermal_file(temp_files, cpu_sensor_priorities)
                    if best_file:
                        self.package_temp_file = best_file
                        self.logger.info(f"Found thermal file: {best_file}")
                        return
        
        except Exception as e:
            self.logger.error(f"Error finding thermal files: {e}")
        
        self.logger.warning('No thermal files found for CPU temperature monitoring.')

    def _find_thermal_zone_file(self):
        """Find thermal zone file - most reliable method for most systems"""
        thermal_zone_base = '/sys/class/thermal/'
        
        if not os.path.exists(thermal_zone_base):
            return None
        
        try:
            # Look for thermal zones
            for item in os.listdir(thermal_zone_base):
                if item.startswith('thermal_zone'):
                    zone_path = os.path.join(thermal_zone_base, item)
                    temp_file = os.path.join(zone_path, 'temp')
                    type_file = os.path.join(zone_path, 'type')
                    
                    if os.path.exists(temp_file) and os.path.exists(type_file):
                        try:
                            with open(type_file, 'r') as f:
                                zone_type = f.read().strip().lower()
                                
                            # Check if this thermal zone is CPU-related
                            if self._is_cpu_related_thermal(zone_type):
                                # Verify the temperature file is readable
                                with open(temp_file, 'r') as f:
                                    temp_value = f.read().strip()
                                    if temp_value.isdigit():
                                        return temp_file
                        except (IOError, OSError):
                            continue
        
        except Exception as e:
            self.logger.debug(f"Error searching thermal zones: {e}")
        
        return None

    def _search_temperature_files(self, base_path):
        """Search for temperature files in the given path"""
        temp_files = []
        
        try:
            for root, dirs, files in self.directory_cache.cached_directory_walk(base_path):
                # Look for various temperature file patterns
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Common temperature file patterns
                    if any(pattern in file.lower() for pattern in ['temp', 'thermal']):
                        if any(suffix in file for suffix in ['_input', '_temp', '_temperature']):
                            # Check if file contains CPU-related info
                            parent_dir = os.path.basename(root).lower()
                            if self._is_cpu_related_path(root, file):
                                try:
                                    # Verify file is readable and contains valid temperature
                                    with open(file_path, 'r') as f:
                                        content = f.read().strip()
                                        if content.isdigit() and int(content) > 0:
                                            temp_files.append({
                                                'path': file_path,
                                                'root': root,
                                                'file': file,
                                                'parent_dir': parent_dir
                                            })
                                except (IOError, OSError, ValueError):
                                    continue
        
        except Exception as e:
            self.logger.debug(f"Error searching temperature files in {base_path}: {e}")
        
        return temp_files

    def _is_cpu_related_thermal(self, zone_type):
        """Check if a thermal zone type is CPU-related"""
        zone_type = zone_type.lower()
        
        # Intel/AMD patterns
        if self.cpu_type == "Intel":
            return any(pattern in zone_type for pattern in ['package', 'cpu', 'coretemp', 'x86_pkg_temp'])
        
        # AMD patterns
        if 'amd' in zone_type or any(pattern in zone_type for pattern in ['tctl', 'tccd', 'k10temp']):
            return True
        
        # ARM patterns
        if any(pattern in zone_type for pattern in ['cpu', 'cluster', 'soc']):
            return True
        
        # Generic patterns
        return any(pattern in zone_type for pattern in ['cpu', 'processor', 'core'])

    def _is_cpu_related_path(self, root, file):
        """Check if a file path is CPU-related"""
        full_path = os.path.join(root, file).lower()
        parent_dir = os.path.basename(root).lower()
        
        # Check for CPU-related patterns in the path
        cpu_patterns = [
            'cpu', 'coretemp', 'package', 'tctl', 'tccd', 'k10temp',
            'thermal/cpu', 'cpu_thermal', 'cluster', 'soc', 'tsens'
        ]
        
        # Check file content description if available
        try:
            # Look for label or name files in the same directory
            for label_file in ['label', 'name', 'type']:
                label_path = os.path.join(root, file.replace('_input', f'_{label_file}'))
                if os.path.exists(label_path):
                    with open(label_path, 'r') as f:
                        label_content = f.read().strip().lower()
                        if self._is_cpu_related_thermal(label_content):
                            return True
            
            # Check hwmon device name
            if 'hwmon' in root:
                name_file = os.path.join(root, 'name')
                if os.path.exists(name_file):
                    with open(name_file, 'r') as f:
                        name_content = f.read().strip().lower()
                        if self._is_cpu_related_thermal(name_content):
                            return True
        
        except (IOError, OSError):
            pass
        
        # Check path components
        return any(pattern in full_path for pattern in cpu_patterns)

    def _select_best_thermal_file(self, temp_files, priorities):
        """Select the best thermal file based on priority list"""
        if not temp_files:
            return None
        
        # Score each file based on priority patterns
        scored_files = []
        
        for file_info in temp_files:
            score = 0
            path = file_info['path'].lower()
            parent_dir = file_info['parent_dir'].lower()
            
            # Check against priority list
            for i, (pattern1, pattern2) in enumerate(priorities):
                priority_score = len(priorities) - i  # Higher score for higher priority
                
                if pattern1 in path and (not pattern2 or pattern2 in path):
                    score += priority_score * 2  # Bonus for exact match
                elif pattern1 in parent_dir:
                    score += priority_score
            
            # Bonus for commonly reliable patterns
            if 'thermal_zone' in path:
                score += 100  # Thermal zones are usually reliable
            if 'hwmon' in path:
                score += 50  # hwmon devices are usually stable
            
            # Intel/AMD specific bonuses
            if self.cpu_type == "Intel":
                if 'package' in path or 'coretemp' in path:
                    score += 30
            else:  # AMD or Other
                if 'tctl' in path or 'k10temp' in path:
                    score += 30
            
            scored_files.append((score, file_info))
        
        # Sort by score (descending) and return the best match
        scored_files.sort(key=lambda x: x[0], reverse=True)
        
        if scored_files:
            best_score, best_file = scored_files[0]
            self.logger.info(f"Selected thermal file with score {best_score}: {best_file['path']}")
            return best_file['path']
        
        return None

    def is_relevant_temp_file(self, label):
        # Enhanced version of the existing method
        label = label.lower()
        
        # Intel patterns
        if self.cpu_type == 'Intel':
            return any(pattern in label for pattern in ['package', 'cpu', 'coretemp', 'core'])
        
        # AMD patterns
        if any(pattern in label for pattern in ['tctl', 'tccd', 'k10temp', 'amdgpu']):
            return True
        
        # ARM and other patterns
        return any(pattern in label for pattern in ['cpu', 'cluster', 'soc', 'thermal', 'core'])

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
                        self.cpu_files['epb_files'][i] = file_path
                        found_files += 1
                        break
                if found_files == 0:
                    self.logger.warning(f'Intel energy_perf_bias file for thread {i} does not exist at {thread_power_directory}.')

        except Exception as e:
            self.logger.error(f"Error finding Intel energy_perf_bias files for threads: {e}")
