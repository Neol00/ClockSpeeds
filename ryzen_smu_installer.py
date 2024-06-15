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
import subprocess
import platform
import logging
from log_setup import get_logger
from privileged_actions import privileged_actions

class RyzenSmuInstaller:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        # List of dependencies required for building and installing the module
        self.dependencies = ["git", "dkms", "base-devel"]

    def detect_package_manager(self):
        # Detect the package manager for the system
        package_managers = {
            "pacman": ["pacman", "-Sy", "--noconfirm"]
        }
        for pm in package_managers.keys():
            if subprocess.run(["which", pm], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                return pm, package_managers[pm]
        return None, None

    def install_dependencies(self, package_manager, install_command):
        # Install the required dependencies using the detected package manager
        commands = []
        for dep in self.dependencies:
            result = subprocess.run(["which", dep], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                self.logger.info(f"Installing {dep} using {package_manager}...")
                commands.append(f"{' '.join([package_manager] + install_command + [dep])}")

        # Check and install kernel headers
        kernel_name = self.get_running_kernel()
        headers_package = self.get_kernel_headers_package(kernel_name)
        self.logger.info(f"Installing {headers_package} using {package_manager}...")
        commands.append(f"{' '.join([package_manager] + install_command + [headers_package])}")

        if commands:
            full_command = " && ".join(commands)
            success, error = privileged_actions.run_pkexec_command(full_command)
            if not success:
                self.logger.error(f"Failed to install dependencies: {error}")
                return False

        self.logger.info("All dependencies are installed.")
        return True

    def get_running_kernel(self):
        # Get the name of the currently running kernel
        kernel_name = subprocess.run(["uname", "-r"], stdout=subprocess.PIPE, text=True).stdout.strip()
        self.logger.info(f"Running kernel: {kernel_name}")
        return kernel_name

    def get_kernel_headers_package(self, kernel_name):
        # Determine the appropriate kernel headers package based on the kernel name
        if 'zen' in kernel_name:
            return 'linux-zen-headers'
        elif 'hardened' in kernel_name:
            return 'linux-hardened-headers'
        elif 'lts' in kernel_name:
            return 'linux-lts-headers'
        else:
            return 'linux-headers'

    def check_and_install_dependencies(self):
        # Check and install the required dependencies
        package_manager, install_command = self.detect_package_manager()
        if package_manager is None:
            self.logger.error("No compatible package manager found.")
            return False

        return self.install_dependencies(package_manager, install_command)

    def clone_repository(self, repo_url, dest_dir):
        # Clone the specified Git repository to the destination directory
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        result = subprocess.run(["git", "clone", repo_url, dest_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            self.logger.error(f"Failed to clone repository: {result.stderr.decode()}")
            return False
        self.logger.info("Repository cloned successfully.")
        return True

    def install_module(self, src_dir):
        # Install the DKMS module from the source directory
        try:
            # Run the make dkms-install command inside the ryzen_smu directory
            success, error = privileged_actions.run_pkexec_command(["make", "dkms-install"], cwd=src_dir)
            if not success:
                self.logger.error(f"Failed to install DKMS module: {error}")
                return False
            
            self.logger.info("ryzen_smu module installed successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Installation failed: {str(e)}")
            return False

    def enable_enhanced_control(self):
        # Enable enhanced control for Ryzen CPUs by installing the ryzen_smu module
        repo_url = "https://github.com/leogx9r/ryzen_smu.git"
        dest_dir = os.path.join(os.path.dirname(__file__), "ryzen_smu")
        
        if not self.check_and_install_dependencies():
            self.logger.error("Failed to install dependencies. Cannot enable enhanced Ryzen control.")
            return False

        if not self.clone_repository(repo_url, dest_dir):
            self.logger.error("Failed to clone ryzen_smu repository.")
            return False

        if not self.install_module(dest_dir):
            self.logger.error("Failed to install ryzen_smu module.")
            return False

        self.logger.info("Enhanced Ryzen control enabled.")
        return True

    def is_ryzen_smu_installed(self):
        # Check if the ryzen_smu module is installed using DKMS
        result = subprocess.run(["dkms", "status", "ryzen_smu"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "installed" in result.stdout.decode()

# Create an instance of the RyzenSmuInstaller
ryzen_smu_installer = RyzenSmuInstaller()
