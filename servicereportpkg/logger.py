# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Setup the logging functionality with either journal or file handler"""


import os
import logging
from logging import handlers

from servicereportpkg.global_context import TOOL_NAME


def get_syslog_formatter(ident):
    """Returns log format for syslog handler"""

    return logging.Formatter(ident+': %(levelname)s - %(message)s')


def get_file_formatter(ident):
    """Returns log format for file log handler"""

    _format = '%(asctime)s '+ ident + '['+str(os.getpid())+']: %(levelname)s - %(message)s'
    return logging.Formatter(_format,
                             "%b %d %H:%M:%S")


def configure_syslog_handler():
    """Configure the syslog and returns an instance of SysLogHandler"""

    try:
        log_handler = logging.handlers.SysLogHandler(address="/dev/log")
        log_handler.setFormatter(get_syslog_formatter(TOOL_NAME))
    except Exception:
        print("Failed to configure syslog")
        return None

    return log_handler


def configure_filelog_handler(custom_log_file):
    """Configure the file log handler and returns an instance of
    FileHandler."""

    try:
        log_handler = logging.FileHandler(custom_log_file)
        log_handler.setFormatter(get_file_formatter(TOOL_NAME))
    except IOError:
        print("Failed to access the log file: %s", custom_log_file)
        return None

    return log_handler


def add_log_level(logger, level_name, num_val):
    """Set new log level to given logger object"""

    logging.addLevelName(num_val, level_name)

    setattr(logger, level_name.lower().strip(),
            lambda message, *args, **kwargs:
            logger._log(num_val, message, args, **kwargs))


def setup_logger(custom_log_file=None, enable_debug=0):
    """Setup the logger with either journal or file handler"""

    logger = logging.getLogger(TOOL_NAME)
    add_log_level(logger, '    RECOMMENDATION', 25)

    if enable_debug > 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    log_handler = None

    if custom_log_file:
        log_handler = configure_filelog_handler(custom_log_file)
    else:
        log_handler = configure_syslog_handler()

    if log_handler:
        logger.addHandler(log_handler)
    else:
        logger.addHandler(logging.NullHandler())

    return logger


def change_log_identifier(ident, logger, log_handler_name=None):
    """Change the log identifier for a given log handler. If log handler name
    is not specified function will update the log identifier of all available
    handlers in the logger."""

    for log_handler in logger.handlers:
        log_handler_class = log_handler.__class__.__name__

        if not log_handler_name or log_handler_name == log_handler_class:
            if log_handler_class == "SysLogHandler":
                log_handler.setFormatter(get_syslog_formatter(ident))
            elif log_handler_class == "FileHandler":
                log_handler.setFormatter(get_file_formatter(ident))


def get_default_logger():
    """Returns the logger object crated during setup"""

    return logging.getLogger(TOOL_NAME)
