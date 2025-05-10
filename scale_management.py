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

class ScaleManager:
    def __init__(self, config_manager, logger, global_state, gui_components, widget_factory, cpu_file_search, cpu_manager):
        # References to instances
        self.config_manager = config_manager
        self.logger = logger
        self.global_state = global_state
        self.gui_components = gui_components
        self.widget_factory = widget_factory
        self.cpu_file_search = cpu_file_search
        self.cpu_manager = cpu_manager

        # Initialize dictionaries for GUI components
        self.min_scales = {}
        self.max_scales = {}

        # GUI components
        self.disable_scale_limits_checkbutton = None
        self.sync_scales_checkbutton = None
        self.tdp_scale = None

        # Initialize cache for CPU frequencies and TDP values
        self._cached_freqs = None
        self._cached_tdp_values = None

        # Fetch and cache allowed frequencies and TDP values during initialization
        self._initialize_cache()

    def _initialize_cache(self):
        # Initialize the cache for CPU frequencies and TDP values
        try:
            self._cached_freqs = self.cpu_manager.get_allowed_cpu_frequency()
            if not self._cached_freqs or None in self._cached_freqs:
                self.logger.info("Failed to retrieve allowed CPU frequencies, using defaults")
                min_allowed_freqs = [400] * self.cpu_file_search.thread_count
                max_allowed_freqs = [5000] * self.cpu_file_search.thread_count
                self._cached_freqs = (min_allowed_freqs, max_allowed_freqs)
            
            self._cached_tdp_values = self.cpu_manager.get_allowed_tdp_values()
            if self._cached_tdp_values is None:
                self.logger.info("Failed to retrieve allowed TDP values, this is expected on non-Intel CPUs")
        except Exception as e:
            self.logger.error(f"Error initializing cache: {e}")
            # Set default values as fallback
            min_allowed_freqs = [400] * self.cpu_file_search.thread_count
            max_allowed_freqs = [5000] * self.cpu_file_search.thread_count
            self._cached_freqs = (min_allowed_freqs, max_allowed_freqs)
            self._cached_tdp_values = 105  # Default TDP in watts

    def setup_gui_components(self):
        # Set up references to GUI components from the shared dictionary
        try:
            self.disable_scale_limits_checkbutton = self.gui_components['disable_scale_limits_checkbutton']
            self.sync_scales_checkbutton = self.gui_components['sync_scales_checkbutton']
            self.tdp_scale = self.gui_components['tdp_scale']

            # Loop through the min scales in the GUI components and set up references
            for thread_num in range(self.cpu_file_search.thread_count):
                try:
                    self.min_scales[thread_num] = self.gui_components['cpu_min_scales'][thread_num]
                    self.max_scales[thread_num] = self.gui_components['cpu_max_scales'][thread_num]
                except KeyError as e:
                    self.logger.error(f"Error setting up scale for thread {thread_num}: Component {e} not found")
        except KeyError as e:
            self.logger.error(f"Error setting up scale_manager's GUI components: Component {e} not found")

    def get_scale_pair(self, thread_num):
        # Get the min and max scale widgets for a given thread number
        try:
            min_scale = self.min_scales.get(thread_num)
            max_scale = self.max_scales.get(thread_num)
            if min_scale is None or max_scale is None:
                self.logger.warning(f"Scale widget for thread {thread_num} not found.")
                return None, None
            return min_scale, max_scale
        except Exception as e:
            self.logger.error(f"Error getting scale pair for thread {thread_num}: {e}")
            return None, None

    def extract_thread_num(self, scale_name):
        # Extract the thread number from the scale widget name
        try:
            return int(scale_name.split('_')[-1])
        except ValueError as e:
            self.logger.error(f"Invalid scale name format or unable to extract thread number: {scale_name}, Error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error extracting thread number from scale name: {scale_name}, Error: {e}")
            return None

    def update_min_max_labels(self, event):
        # Update the min and max scale labels based on user interaction
        if not event:
            return

        try:
            scale_name = event.get_name()  # Name of the scale that triggered the event
            source_value = event.get_value()  # Current value of the scale
            thread_num = self.extract_thread_num(scale_name)  # Extract the thread number

            if thread_num is None:
                return

            min_scale, max_scale = self.get_scale_pair(thread_num)
            if not (min_scale and max_scale):
                return

            # Determine the type of scale and apply the logic
            is_min_scale = 'min' in scale_name
            if is_min_scale:
                if source_value > max_scale.get_value():
                    max_scale.set_value(source_value)  # Adjust max if min exceeds it
                min_scale.set_value(min(source_value, max_scale.get_value()))  # Enforce min does not exceed max
            else:
                if source_value < min_scale.get_value():
                    min_scale.set_value(source_value)  # Adjust min if max falls below it
                max_scale.set_value(max(source_value, min_scale.get_value()))  # Enforce max does not fall below min

            # Synchronize scales across threads if the sync option is enabled
            if self.global_state.sync_scales:
                self.sync_scales(event)
            else:
                # Set the scale range for the current thread
                self.set_scale_range(min_scale, max_scale, thread_num)

        except Exception as e:
            self.logger.error(f"Error updating min-max labels: {e}")

    def set_scale_range(self, min_scale=None, max_scale=None, thread_num=None, tdp_scale=None):
        # Set the range for the min and max scales based on current settings
        try:
            if self.global_state.disable_scale_limits:
                self.set_unlimited_range(min_scale, max_scale)
            else:
                self.set_limited_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error setting scale range: {e}")

    def set_unlimited_range(self, min_scale, max_scale):
        # Set the scale range to unlimited values
        try:
            if min_scale and max_scale:
                min_scale.set_range(self.global_state.SCALE_MIN, self.global_state.SCALE_MAX)
                max_scale.set_range(self.global_state.SCALE_MIN, self.global_state.SCALE_MAX)

            if self.tdp_scale:
                self.tdp_scale.set_range(self.global_state.TDP_SCALE_MIN, self.global_state.TDP_SCALE_MAX)
        except Exception as e:
            self.logger.error(f"Error setting unlimited range: {e}")

    def set_limited_range(self, min_scale, max_scale, thread_num):
        # Set the scale range to limited values based on allowed CPU frequencies
        try:
            if self._cached_freqs is None:
                self._initialize_cache()

            # Handle case where cached_freqs is None
            if self._cached_freqs is None:
                # Use default values
                min_allowed_freq = 400 # 400 Mhz
                max_allowed_freq = 5000  # 5 GHz
            else:
                min_allowed_freqs, max_allowed_freqs = self._cached_freqs
                
                # Ensure that the thread number is valid
                if thread_num is None or thread_num >= len(min_allowed_freqs):
                    self.logger.warning(f"Allowed frequencies for thread {thread_num} not found, using defaults")
                    min_allowed_freq = 400 # 400 Mhz
                    max_allowed_freq = 5000  # 5 GHz
                else:
                    min_allowed_freq = min_allowed_freqs[thread_num]
                    max_allowed_freq = max_allowed_freqs[thread_num]

            # Set the range for min and max scales if they are provided and valid
            if min_scale and max_scale:
                min_scale.set_range(min_allowed_freq, max_allowed_freq)
                max_scale.set_range(min_allowed_freq, max_allowed_freq)

            # For TDP scale
            if self._cached_tdp_values is None:
                self._initialize_cache()

            # Set the range for the TDP scale only if the CPU type is not "Other"
            if self.tdp_scale and self.cpu_file_search.cpu_type != "Other":
                max_tdp_value_w = self._cached_tdp_values
                if max_tdp_value_w is not None:
                    self.tdp_scale.set_range(self.global_state.TDP_SCALE_MIN, max_tdp_value_w)
                else:
                    # Use default TDP value
                    self.tdp_scale.set_range(self.global_state.TDP_SCALE_MIN, self.global_state.TDP_SCALE_MAX)
        except Exception as e:
            self.logger.error(f"Error setting limited range: {e}")

    def sync_scales(self, source_scale):
        # Synchronize the values of all min and max scales based on the source scale
        try:
            source_value = source_scale.get_value()
            is_min_scale = 'min' in source_scale.get_name()

            # Gather current values to determine the new synchronized values efficiently
            current_min_values = [self.min_scales[tn].get_value() for tn in self.min_scales.keys()]
            current_max_values = [self.max_scales[tn].get_value() for tn in self.max_scales.keys()]

            if is_min_scale:
                new_min_value = source_value
                new_max_value = max(source_value, max(current_max_values))
            else:
                new_min_value = min(source_value, min(current_min_values))
                new_max_value = source_value

            # Temporarily block all signals to prevent triggering events for every change
            for min_scale, max_scale in zip(self.min_scales.values(), self.max_scales.values()):
                min_scale.handler_block_by_func(self.update_min_max_labels)
                max_scale.handler_block_by_func(self.update_min_max_labels)

            # Set new values for all min and max scales
            for min_scale, max_scale in zip(self.min_scales.values(), self.max_scales.values()):
                if is_min_scale:
                    if new_min_value > max_scale.get_value():
                        max_scale.set_value(new_min_value)
                    min_scale.set_value(new_min_value)
                else:
                    if new_max_value < min_scale.get_value():
                        min_scale.set_value(new_max_value)
                    max_scale.set_value(new_max_value)

            # Unblock all signals and force a single redraw if necessary
            for min_scale, max_scale in zip(self.min_scales.values(), self.max_scales.values()):
                min_scale.handler_unblock_by_func(self.update_min_max_labels)
                max_scale.handler_unblock_by_func(self.update_min_max_labels)
        except Exception as e:
            self.logger.error(f"Error syncing scales: {e}")

    def on_disable_scale_limits_change(self, checkbutton):
        # Handle changes to the disable scale limits setting
        self.global_state.disable_scale_limits = self.disable_scale_limits_checkbutton.get_active()
        try:
            # Iterate over all threads to update their scale ranges
            for thread_num in self.min_scales.keys():
                min_scale, max_scale = self.get_scale_pair(thread_num)
                if min_scale is not None and max_scale is not None:
                    self.set_scale_range(min_scale=min_scale, max_scale=max_scale, thread_num=thread_num)

            # Update the TDP scale range if it exists
            if self.tdp_scale:
                self.set_scale_range(tdp_scale=self.tdp_scale, thread_num=thread_num)

            # Save the new setting to the configuration
            self.config_manager.set_setting('Settings', 'disable_scale_limits', str(self.global_state.disable_scale_limits))

            # Update all scale labels positions
            self.widget_factory.update_frequency_scale_labels()
        except ValueError as ve:
            self.logger.error(f"ValueError changing scale limits: {ve}")
        except Exception as e:
            self.logger.error(f"Error changing scale limits: {e}")

    def on_sync_scales_change(self, checkbutton):
        # Handle changes to the sync scales setting
        try:
            self.global_state.sync_scales = self.sync_scales_checkbutton.get_active()
            self.config_manager.set_setting('Settings', 'sync_scales', str(self.global_state.sync_scales))
        except Exception as e:
            self.logger.error(f"Error changing sync scales setting: {e}")

    def load_scale_config_settings(self):
        # Load the scale configuration settings from the config manager
        try:
            scale_limit_setting = self.config_manager.get_setting('Settings', 'disable_scale_limits', 'False')
            sync_scales_setting = self.config_manager.get_setting('Settings', 'sync_scales', 'False')
            self.global_state.disable_scale_limits = scale_limit_setting == 'True'
            self.global_state.sync_scales = sync_scales_setting == 'True'
            self.disable_scale_limits_checkbutton.set_active(self.global_state.disable_scale_limits)
            self.sync_scales_checkbutton.set_active(self.global_state.sync_scales)
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
