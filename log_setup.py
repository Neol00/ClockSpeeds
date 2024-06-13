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
from logging.handlers import RotatingFileHandler
from config_setup import config_manager

# Valid log levels
valid_log_levels = frozenset(['ERROR', 'INFO', 'WARNING'])

class DeduplicationFilter(logging.Filter):
    # A logging filter that avoids logging duplicate messages, except for INFO messages.
    def __init__(self):
        super(DeduplicationFilter, self).__init__()
        self.logged_messages = set()

    def filter(self, record):
        # Allow INFO messages to be logged regardless of duplication
        if record.levelno == logging.INFO:
            return True

        # Generate a unique key for the log record
        log_key = (record.levelno, record.msg, record.args)
        if log_key in self.logged_messages:
            # If the message has already been logged, reject it
            return False
        else:
            # If it's a new message, add it to the set and allow logging
            self.logged_messages.add(log_key)
            return True

class LogSetup:
    _logging_initialized = False  # Class variable to track if the logging level has been set

    def __init__(self, log_file_path=None, max_file_size=20 * 1024 * 1024, backup_count=2):
        # Initialize the LogSetup instance with default parameters.
        self.log_file_path = log_file_path or self.default_log_file_path()
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        if not LogSetup._logging_initialized:
            self.logger = self.setup_logging()
            LogSetup._logging_initialized = True
        else:
            self.logger = logging.getLogger()  # Get the already configured logger

    def default_log_file_path(self):
        # Use the script's directory as the base for the log file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, 'logs', 'clockspeeds.log')

    def setup_logging(self):
        # Setup the logging configuration with rotation and deduplication filter.
        try:
            # Ensure the log directory exists
            log_dir = os.path.dirname(self.log_file_path)
            os.makedirs(log_dir, exist_ok=True)

            # Retrieve the logging level from configuration
            config_log_level = config_manager.get_setting('Settings', 'LoggingLevel', default='WARNING').upper()
            log_level = {'ERROR': logging.ERROR, 'INFO': logging.INFO, 'WARNING': logging.WARNING}.get(config_log_level, logging.ERROR)
            logger = logging.getLogger()
            logger.setLevel(log_level)

            # Check if a similar handler is already attached and skip adding if found
            if not any(isinstance(handler, RotatingFileHandler) and handler.baseFilename == os.path.abspath(self.log_file_path) for handler in logger.handlers):
                handler = RotatingFileHandler(self.log_file_path, maxBytes=self.max_file_size, backupCount=self.backup_count)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                deduplication_filter = DeduplicationFilter()
                handler.addFilter(deduplication_filter)
                logger.addHandler(handler)

            logger.info(f"Logging started with level {config_log_level}")

        except Exception as e:
            # Fallback logger setup in case of any error
            logging.basicConfig(level=logging.ERROR)
            logger = logging.getLogger()
            logger.error(f"Failed to set up custom logging, using basic config. Error: {e}")

        return logger

# Create an instance of LogSetup
log_setup = LogSetup()

# Provide a method to get the configured logger
def get_logger():
    return log_setup.logger
