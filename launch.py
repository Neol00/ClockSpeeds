#!/usr/bin/env python3

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
import platform
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
        
        # Detect system architecture
        self.architecture = platform.machine().lower()
        self.logger.info(f"Detected architecture: {self.architecture}")

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
                        
                        # Extract source file path from .pyc file
                        if '__pycache__' in pyc_path:
                            # Handle __pycache__ format: __pycache__/file.cpython-39.pyc
                            cache_dir = os.path.dirname(pyc_path)
                            parent_dir = os.path.dirname(cache_dir)
                            filename = os.path.basename(pyc_path)
                            # Extract the base filename without version info
                            base_name = filename.split('.')[0]
                            src_path = os.path.join(parent_dir, f"{base_name}.py")
                        else:
                            # Handle direct .pyc files
                            src_path = pyc_path[:-1]  # Remove 'c' from '.pyc' to get the source path

                        # Check if source file exists and compare timestamps
                        if os.path.exists(src_path):
                            src_mtime = os.stat(src_path).st_mtime
                            pyc_mtime = os.stat(pyc_path).st_mtime
                            if src_mtime > pyc_mtime:
                                return True  # Source file is newer than the bytecode

                        # Check Python version used to compile the bytecode
                        try:
                            with open(pyc_path, 'rb') as f:
                                header = f.read(16)  # Read more bytes to handle different Python versions
                                current_magic = importlib.util.MAGIC_NUMBER
                                # Compare first 4 bytes which contain the magic number
                                if len(header) >= 4 and header[:4] != current_magic:
                                    return True  # Bytecode was compiled with a different Python version
                        except Exception as e:
                            self.logger.warning(f"Error checking bytecode version for {pyc_path}: {e}")
                            return True  # If we can't read it, consider it outdated

            return False

        except Exception as e:
            self.logger.error(f"Failed to check whether __pycache__ is outdated: {e}")
            return True  # Consider outdated if we can't check

    def clear_pycache(self, pycache_path='./__pycache__'):
        # Clears the cache if the application is run on a different version
        if os.path.exists(pycache_path) and self.is_cache_outdated(pycache_path):
            try:
                shutil.rmtree(pycache_path)
                self.logger.info("__pycache__ directory cleared because it was outdated.")
            except Exception as e:
                self.logger.error(f"Failed to clear outdated __pycache__: {e}")

    def get_python_executable(self):
        # Get the appropriate Python executable
        # Try to use the same interpreter that's running this script
        python_exe = sys.executable
        
        # Fallback to common Python command names
        if not python_exe or not os.path.isfile(python_exe):
            for cmd in ['python3', 'python']:
                try:
                    result = Popen([cmd, '--version'], stdout=PIPE, stderr=PIPE)
                    result.communicate()
                    if result.returncode == 0:
                        python_exe = cmd
                        break
                except FileNotFoundError:
                    continue
        
        if not python_exe:
            self.logger.error("Could not find Python executable")
            return None
            
        self.logger.info(f"Using Python executable: {python_exe}")
        return python_exe

    def launch_main_application(self):
        # Launches the main application script securely
        main_script_path = os.path.join(self.script_dir, 'main.py')  # Path to the main application script
        
        if not os.path.exists(main_script_path):
            self.logger.error(f"Main script not found at: {main_script_path}")
            return False

        try:
            python_exe = self.get_python_executable()
            if not python_exe:
                return False
                
            # Use the same Python executable that's running this script
            process = Popen([python_exe, main_script_path], 
                          stdout=PIPE, stderr=PIPE,
                          cwd=self.script_dir)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.logger.error("Error launching the main application:")
                self.logger.error(f"Return code: {process.returncode}")
                if stderr:
                    self.logger.error(f"STDERR: {stderr.decode()}")
                if stdout:
                    self.logger.info(f"STDOUT: {stdout.decode()}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch the main application: {e}")
            return False

    def run(self):
        # Main function to perform checks and launch the application
        if not self.is_safe_environment() or not self.validate_python_version():
            self.logger.error("Environment checks failed")
            sys.exit(1)  # Exit if the environment is not safe or the Python version is incompatible

        self.clear_pycache()  # Clear __pycache__ if it's outdated
        
        if not self.launch_main_application():
            self.logger.error("Failed to launch main application")
            sys.exit(1)

if __name__ == '__main__':
    launcher = Launcher()
    launcher.run()