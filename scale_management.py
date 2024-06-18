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
from log_setup import get_logger
from config_setup import config_manager
from shared import global_state, gui_components
from cpu_file_search import cpu_file_search
from cpu_management import cpu_manager

class ScaleManager:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        # Initialize dictionaries for GUI components
        self.min_scales = {}
        self.max_scales = {}

        # GUI components
        self.disable_scale_limits_checkbutton = None
        self.sync_scales_checkbutton = None
        self.tdp_scale = None

    def setup_gui_components(self):
        # Set up references to GUI components from the shared dictionary
        try:
            self.disable_scale_limits_checkbutton = gui_components['disable_scale_limits_checkbutton']
            self.sync_scales_checkbutton = gui_components['sync_scales_checkbutton']
            self.tdp_scale = gui_components['tdp_scale']

            # Loop through the min scales in the GUI components and set up references
            for thread_num in range(cpu_file_search.thread_count):
                try:
                    self.min_scales[thread_num] = gui_components['cpu_min_scales'][thread_num]
                    self.max_scales[thread_num] = gui_components['cpu_max_scales'][thread_num]
                except KeyError as e:
                    self.logger.error(f"Error setting up scale for thread {thread_num}: Component {e} not found")
        except KeyError as e:
            self.logger.error(f"Error setting up scale_manager's GUI components: Component {e} not found")

    def get_scale_pair(self, thread_num):
        # Get the min and max scale widgets for a given thread number
        try:
            min_scale = self.min_scales[thread_num]
            max_scale = self.max_scales[thread_num]
            return min_scale, max_scale
        except KeyError:
            self.logger.error(f"Scale widget for thread {thread_num} not found.")
            return None, None

    def extract_thread_num(self, scale_name):
        # Extract the thread number from the scale widget name
        try:
            return int(scale_name.split('_')[-1])
        except ValueError:
            self.logger.error(f"Invalid scale name format: {scale_name}")
            return None

    def update_min_max_labels(self, event):
        # Update the min and max scale labels based on user interaction
        if not event:
            return
        try:
            scale_name = event.get_name()  # Get the name of the scale that triggered the event
            source_value = event.get_value()  # Get the current value of the scale
            thread_num = self.extract_thread_num(scale_name)  # Extract the thread number from the scale name
            if thread_num is None:
                return
            
            # Get the pair of min and max scales for the current thread
            min_scale, max_scale = self.get_scale_pair(thread_num)
            if not (min_scale and max_scale):
                return
            
            # Update the max scale value if the min scale value exceeds it
            if 'min' in scale_name and source_value > max_scale.get_value():
                max_scale.set_value(source_value)
            # Update the min scale value if the max scale value is less than it
            elif source_value < min_scale.get_value():
                min_scale.set_value(source_value)
            
            # Synchronize scales across threads if the sync option is enabled
            if global_state.sync_scales:
                self.sync_scales(event)
            else:
                # Set the scale range for the current thread
                self.set_scale_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error updating min-max labels: {e}")

    def set_scale_range(self, min_scale=None, max_scale=None, thread_num=None, tdp_scale=None):
        # Set the range for the min and max scales based on current settings
        try:
            if global_state.disable_scale_limits:
                self.set_unlimited_range(min_scale, max_scale)
            else:
                self.set_limited_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error setting scale range: {e}")

    def set_unlimited_range(self, min_scale, max_scale):
        # Set the scale range to unlimited values
        try:
            if min_scale and max_scale:
                min_scale.set_range(global_state.SCALE_MIN, global_state.SCALE_MAX)
                max_scale.set_range(global_state.SCALE_MIN, global_state.SCALE_MAX)

            if self.tdp_scale:
                self.tdp_scale.set_range(global_state.TDP_SCALE_MIN, global_state.TDP_SCALE_MAX)
        except Exception as e:
            self.logger.error(f"Error setting unlimited range: {e}")

    def set_limited_range(self, min_scale, max_scale, thread_num):
        # Set the scale range to limited values based on allowed CPU frequencies
        try:
            # Get the allowed CPU frequencies
            min_allowed_freqs, max_allowed_freqs = cpu_manager.get_allowed_cpu_frequency()
            if not min_allowed_freqs or not max_allowed_freqs:
                self.logger.error("Failed to retrieve allowed CPU frequencies")
                return

            # Check if the thread number is valid
            if thread_num is not None and thread_num >= len(min_allowed_freqs):
                self.logger.error(f"Allowed frequencies for thread {thread_num} not found")
                return

            # Set the range for min and max scales if they are provided
            if min_scale and max_scale:
                min_scale.set_range(min_allowed_freqs[thread_num], max_allowed_freqs[thread_num])
                max_scale.set_range(min_allowed_freqs[thread_num], max_allowed_freqs[thread_num])

            # Set the range for the TDP scale only if the CPU type is not "Other"
            if self.tdp_scale and cpu_file_search.cpu_type != "Other":
                max_tdp_value_w = cpu_manager.get_allowed_tdp_values()
                if max_tdp_value_w is not None:
                    self.tdp_scale.set_range(global_state.TDP_SCALE_MIN, max_tdp_value_w)

        except Exception as e:
            self.logger.error(f"Error setting limited range: {e}")

    def sync_scales(self, source_scale):
        # Synchronize the values of all min and max scales based on the source scale
        try:
            source_value = source_scale.get_value()  # Get the value of the source scale
            is_min_scale = 'min' in source_scale.get_name()  # Determine if the source scale is a min scale

            for thread_num in self.min_scales.keys():
                # Get the pair of min and max scales for the current thread
                min_scale, max_scale = self.get_scale_pair(thread_num)
                if not min_scale or not max_scale:
                    self.logger.error(f"Scale pair for thread {thread_num} not found")
                    continue

                # Temporarily block signals to prevent recursive updates
                min_scale.handler_block_by_func(self.update_min_max_labels)
                max_scale.handler_block_by_func(self.update_min_max_labels)

                # Set new values for min and max scales based on the source scale
                if is_min_scale:
                    new_min_value = source_value
                    new_max_value = max(source_value, max_scale.get_value())
                else:
                    new_min_value = min(source_value, min_scale.get_value())
                    new_max_value = source_value

                min_scale.set_value(new_min_value)
                max_scale.set_value(new_max_value)

                # Unblock signals after setting new values
                min_scale.handler_unblock_by_func(self.update_min_max_labels)
                max_scale.handler_unblock_by_func(self.update_min_max_labels)

                # Update the scale range for the current thread
                self.set_scale_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error synchronizing scales: {e}")

    def on_disable_scale_limits_change(self, checkbutton):
        # Handle changes to the disable scale limits setting
        global_state.disable_scale_limits = self.disable_scale_limits_checkbutton.get_active()  # Update the global state based on the checkbutton's status
        try:
            # Iterate over all threads to update their scale ranges
            for thread_num in self.min_scales.keys():
                min_scale, max_scale = self.get_scale_pair(thread_num)
                if min_scale and max_scale:
                    self.set_scale_range(min_scale=min_scale, max_scale=max_scale, thread_num=thread_num)
            
            # Update the TDP scale range if it exists
            if self.tdp_scale:
                self.set_scale_range(tdp_scale=self.tdp_scale)
            
            # Save the new setting to the configuration
            config_manager.set_setting('Settings', 'disable_scale_limits', str(global_state.disable_scale_limits))
        except Exception as e:
            self.logger.error(f"Error changing scale limits: {e}")

    def on_sync_scales_change(self, checkbutton):
        # Handle changes to the sync scales setting
        try:
            global_state.sync_scales = self.sync_scales_checkbutton.get_active()
            config_manager.set_setting('Settings', 'sync_scales', str(global_state.sync_scales))
        except Exception as e:
            self.logger.error(f"Error changing sync scales setting: {e}")

    def load_scale_config_settings(self):
        # Load the scale configuration settings from the config manager
        try:
            scale_limit_setting = config_manager.get_setting('Settings', 'disable_scale_limits', 'False')
            sync_scales_setting = config_manager.get_setting('Settings', 'sync_scales', 'False')
            global_state.disable_scale_limits = scale_limit_setting == 'True'
            global_state.sync_scales = sync_scales_setting == 'True'
            self.disable_scale_limits_checkbutton.set_active(global_state.disable_scale_limits)
            self.sync_scales_checkbutton.set_active(global_state.sync_scales)
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")

# Create an instance of ScaleManager
scale_manager = ScaleManager()
