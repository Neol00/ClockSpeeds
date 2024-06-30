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
import importlib.util
import shutil
import sys
from subprocess import Popen, PIPE
from config_setup import ConfigManager
from log_setup import LogSetup

class Launcher:
    def __init__(self):
        # Initialize the logger
        self.config_manager = ConfigManager()
        self.log_setup = LogSetup(self.config_manager)
        self.logger = self.log_setup.logger

        self.script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of this script

    def is_safe_environment(self):
        # Check if the current environment is safe for execution
        if os.geteuid() == 0:
            self.logger.warning("Running as root is not allowed.")
            return False
        return True

    def validate_python_version(self):
        # Ensures that the script is running in a compatible Python environment
        min_version = (3, 6)
        if sys.version_info < min_version:
            self.logger.error(f"Python {min_version[0]}.{min_version[1]} or later is required.")
            return False
        return True

    def is_cache_outdated(self, pycache_path):
        # Checks if the cache is from a different python version
        try:
            for root, dirs, files in os.walk(pycache_path):
                for file in files:
                    if file.endswith('.pyc'):
                        pyc_path = os.path.join(root, file)
                        src_path = pyc_path[:-1]  # Remove 'c' from '.pyc' to get the source path

                        # Check if source file exists and compare timestamps
                        if os.path.exists(src_path):
                            src_mtime = os.stat(src_path).st_mtime
                            pyc_mtime = os.stat(pyc_path).st_mtime
                            if src_mtime > pyc_mtime:
                                return True  # Source file is newer than the bytecode

                        # Check Python version used to compile the bytecode
                        with open(pyc_path, 'rb') as f:
                            header = f.read(12)
                            version = importlib.util.MAGIC_NUMBER
                            if header[:4] != version:
                                return True  # Bytecode was compiled with a different Python version

            return False

        except Exception as e:
            self.logger.error(f"Failed to check whether __pycache__ is outdated : {e}")

    def clear_pycache(self, pycache_path='./__pycache__'):
        # Clears the cache if the application is run on a different version
        if os.path.exists(pycache_path) and self.is_cache_outdated(pycache_path):
            try:
                shutil.rmtree(pycache_path)
                self.logger.info("__pycache__ directory cleared because it was outdated.")
            except Exception as e:
                self.logger.error(f"Failed to clear outdated __pycache__: {e}")

    def launch_main_application(self):
        # Launches the main application script securely
        main_script_path = os.path.join(self.script_dir, 'main.py')  # Path to the main application script

        try:
            process = Popen(['python', main_script_path], stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.logger.error("Error launching the main application:")
                self.logger.error(stderr.decode())
        except Exception as e:
            self.logger.error(f"Failed to launch the main application: {e}")

    def run(self):
        # Main function to perform checks and launch the application
        if not self.is_safe_environment() or not self.validate_python_version():
            sys.exit(1)  # Exit if the environment is not safe or the Python version is incompatible

        self.clear_pycache()  # Clear __pycache__ if it's outdated
        self.launch_main_application()

if __name__ == '__main__':
    launcher = Launcher()
    launcher.run()
