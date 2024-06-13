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
from cpu_management import cpu_manager

class ScaleManager:
    def __init__(self):
        # Initialize the logger
        self.logger = get_logger()

        self.min_scales = {}
        self.max_scales = {}
        self.disable_scale_limits_checkbutton = None
        self.sync_scales_checkbutton = None
        self.tdp_scale = None

    def setup_gui_components(self):
        try:
            self.disable_scale_limits_checkbutton = gui_components['disable_scale_limits_checkbutton']
            self.sync_scales_checkbutton = gui_components['sync_scales_checkbutton']
            self.tdp_scale = gui_components['tdp_scale']

            for thread_num in gui_components['cpu_min_scales'].keys():
                try:
                    self.min_scales[thread_num] = gui_components['cpu_min_scales'][thread_num]
                    self.max_scales[thread_num] = gui_components['cpu_max_scales'][thread_num]
                except KeyError as e:
                    self.logger.error(f"Error setting up scale for thread {thread_num}: Component {e} not found")
        except KeyError as e:
            self.logger.error(f"Error setting up scale_manager's GUI components: Component {e} not found")

    def get_scale_pair(self, thread_num):
        try:
            min_scale = self.min_scales[thread_num]
            max_scale = self.max_scales[thread_num]
            return min_scale, max_scale
        except KeyError:
            self.logger.error(f"Scale widget for thread {thread_num} not found.")
            return None, None

    def extract_thread_num(self, scale_name):
        try:
            return int(scale_name.split('_')[-1])
        except ValueError:
            self.logger.error(f"Invalid scale name format: {scale_name}")
            return None

    def update_min_max_labels(self, event):
        if not event:
            return
        try:
            scale_name = event.get_name()
            source_value = event.get_value()
            thread_num = self.extract_thread_num(scale_name)
            if thread_num is None:
                return
            min_scale, max_scale = self.get_scale_pair(thread_num)
            if not (min_scale and max_scale):
                return
            if 'min' in scale_name and source_value > max_scale.get_value():
                max_scale.set_value(source_value)
            elif source_value < min_scale.get_value():
                min_scale.set_value(source_value)
            if global_state.sync_scales:
                self.sync_scales(event)
            else:
                self.set_scale_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error updating min-max labels: {e}")

    def set_scale_range(self, min_scale=None, max_scale=None, thread_num=None, tdp_scale=None):
        try:
            if global_state.disable_scale_limits:
                self.set_unlimited_range(min_scale, max_scale)
            else:
                self.set_limited_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error setting scale range: {e}")

    def set_unlimited_range(self, min_scale, max_scale):
        try:
            if min_scale and max_scale:
                min_scale.set_range(global_state.SCALE_MIN, global_state.SCALE_MAX)
                max_scale.set_range(global_state.SCALE_MIN, global_state.SCALE_MAX)
            if self.tdp_scale:
                self.tdp_scale.set_range(global_state.TDP_SCALE_MIN, global_state.TDP_SCALE_MAX)
        except Exception as e:
            self.logger.error(f"Error setting unlimited range: {e}")

    def set_limited_range(self, min_scale, max_scale, thread_num):
        try:
            min_allowed_freqs, max_allowed_freqs = cpu_manager.get_allowed_cpu_frequency()
            if not min_allowed_freqs or not max_allowed_freqs:
                self.logger.error("Failed to retrieve allowed CPU frequencies")
                return
            if thread_num is not None and thread_num >= len(min_allowed_freqs):
                self.logger.error(f"Allowed frequencies for thread {thread_num} not found")
                return
            if min_scale and max_scale:
                min_scale.set_range(min_allowed_freqs[thread_num], max_allowed_freqs[thread_num])
                max_scale.set_range(min_allowed_freqs[thread_num], max_allowed_freqs[thread_num])
            if self.tdp_scale:
                max_tdp_value_w = cpu_manager.get_allowed_tdp_values()
                self.tdp_scale.set_range(global_state.TDP_SCALE_MIN, max_tdp_value_w)
        except Exception as e:
            self.logger.error(f"Error setting limited range: {e}")

    def sync_scales(self, source_scale):
        try:
            source_value = source_scale.get_value()
            is_min_scale = 'min' in source_scale.get_name()

            for thread_num in self.min_scales.keys():
                min_scale, max_scale = self.get_scale_pair(thread_num)
                if not min_scale or not max_scale:
                    self.logger.error(f"Scale pair for thread {thread_num} not found")
                    continue

                min_scale.handler_block_by_func(self.update_min_max_labels)
                max_scale.handler_block_by_func(self.update_min_max_labels)

                if is_min_scale:
                    new_min_value = source_value
                    new_max_value = max(source_value, max_scale.get_value())
                else:
                    new_min_value = min(source_value, min_scale.get_value())
                    new_max_value = source_value

                min_scale.set_value(new_min_value)
                max_scale.set_value(new_max_value)

                min_scale.handler_unblock_by_func(self.update_min_max_labels)
                max_scale.handler_unblock_by_func(self.update_min_max_labels)

                self.set_scale_range(min_scale, max_scale, thread_num)
        except Exception as e:
            self.logger.error(f"Error synchronizing scales: {e}")

    def on_disable_scale_limits_change(self, checkbutton):
        global_state.disable_scale_limits = self.disable_scale_limits_checkbutton.get_active()
        try:
            for thread_num in self.min_scales.keys():
                min_scale, max_scale = self.get_scale_pair(thread_num)
                if min_scale and max_scale:
                    self.set_scale_range(min_scale=min_scale, max_scale=max_scale, thread_num=thread_num)
            if self.tdp_scale:
                self.set_scale_range(tdp_scale=self.tdp_scale)
            config_manager.set_setting('Settings', 'DisableScaleLimits', str(global_state.disable_scale_limits))
        except Exception as e:
            self.logger.error(f"Error changing scale limits: {e}")

    def on_sync_scales_change(self, checkbutton):
        try:
            global_state.sync_scales = self.sync_scales_checkbutton.get_active()
            config_manager.set_setting('Settings', 'SyncScales', str(global_state.sync_scales))
        except Exception as e:
            self.logger.error(f"Error changing sync scales setting: {e}")

    def load_scale_config_settings(self):
        try:
            scale_limit_setting = config_manager.get_setting('Settings', 'DisableScaleLimits', 'False')
            sync_scales_setting = config_manager.get_setting('Settings', 'SyncScales', 'False')
            global_state.disable_scale_limits = scale_limit_setting == 'True'
            global_state.sync_scales = sync_scales_setting == 'True'
            self.disable_scale_limits_checkbutton.set_active(global_state.disable_scale_limits)
            self.sync_scales_checkbutton.set_active(global_state.sync_scales)
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")

scale_manager = ScaleManager()
