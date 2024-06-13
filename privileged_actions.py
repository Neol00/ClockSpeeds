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

import logging
import subprocess
from log_setup import get_logger

class PrivilegedActions:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

    # Run commands with elevated privileges using pkexec
    def run_pkexec_command(self, command, cwd=None):
        # Convert command to string if it's a list
        command_str = ' '.join(command) if isinstance(command, list) else command

        try:
            # Execute the command with elevated privileges using pkexec
            if cwd:
                subprocess.run(['pkexec', 'sh', '-c', f'cd {cwd} && {command_str}'], check=True)
            else:
                subprocess.run(['pkexec', 'sh', '-c', command_str], check=True)
            return True, None  # Indicates success
        except subprocess.CalledProcessError as e:
            # Check if the error is due to user cancellation or other pkexec specific issues
            if e.returncode == 126:  # Command is found but cannot be executed
                self.logger.info("Command canceled")
                return False, 'canceled'
            elif e.returncode == 127:  # Command not found
                self.logger.error("Command not found")
                return False
            else:
                # Log specific subprocess errors for other exit codes
                self.logger.error(f"pkexec command failed with error: {e}")
                return False, f"subprocess_error: {e}"
        except Exception as e:
            # Log unexpected errors
            self.logger.error(f"Unexpected error running pkexec command: {e}")
            return False, f"unexpected_error: {e}"

# Create an instance of PrivilegedActions
privileged_actions = PrivilegedActions()
