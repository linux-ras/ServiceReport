# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Primary module of the ServiceReport tool. It parses the commandline
argument and based on setup the logger, calls the validation package to
validate the system configuration and also repair the possible failed
check during validation."""


import os
import sys
import time
from argparse import ArgumentParser

from servicereportpkg.repair import Repair
from servicereportpkg.validate import Validate
from servicereportpkg.logger import setup_logger
from servicereportpkg.report import generate_report
from servicereportpkg.global_context import TOOL_NAME
from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import trigger_kernel_crash


__version__ = '2.2.0'


def parse_commandline_args(args):
    """Command line argument parser"""

    parser = ArgumentParser(description="Validation tool to \
                                        verify the system configurations")

    parser.add_argument("-d", "--dump", action="store_true",
                        dest="dump", default=False,
                        help="Trigger a dump")

    parser.add_argument("-f", "--file", dest="log_file",
                        help="creates LOG_FILE in the current directory \
                              and stores the logs into it")

    parser.add_argument("-l", "--list-plugins", action="store_true",
                        dest="list_plugins", default=False,
                        help="list all applicable plugins")

    parser.add_argument("-p" "--plugins", dest="plugins",
                        nargs='+', default=None,
                        help="validates the specified plugins only")

    parser.add_argument("-q", "--quiet", action="store_true",
                        dest="quite", default=False,
                        help="no output on console")

    parser.add_argument("-r", "--repair", action="store_true",
                        dest="repair", default=False,
                        help="Auto fix the incorrection configurations")

    parser.add_argument("-V", "--version", action="store_true",
                        dest="cmdarg_version", default=False,
                        help="print the tool version and exit")

    parser.add_argument("-v", "--verbose", action="count",
                        dest="verbose", default=0,
                        help="increase the logging verbosity")

    return parser.parse_args(args)


def get_version():
    """Returns the tool version"""

    return __version__


def get_dump_plugin(validation_results):
    """Returns the object list of configured dump plugin"""

    validation_plugins = validation_results.keys()
    if "Kdump" in validation_plugins:
        return validation_results["Kdump"]
    elif "FADump" in validation_plugins:
        return validation_results["FADump"]

    return None


def main():
    """Entry point of ServiceReport tool"""

    cmd_opts = parse_commandline_args(sys.argv[1:])
    log = setup_logger(cmd_opts.log_file, cmd_opts.verbose)

    print(TOOL_NAME + " " + get_version()+"\n")

    if cmd_opts.cmdarg_version:
        return 0

    if not os.getuid() == 0:
        print("Must be root to run the tool")
        return 0

    if cmd_opts.quite:
        sys.stdout = open(os.devnull, 'a')
        sys.stderr = open(os.devnull, 'a')

    validator = Validate(cmd_opts)

    if cmd_opts.list_plugins:
        validator.list_applicable_plugins()
        return 0

    validation_results = validator.validate()
    log.debug("Completed the validation.")

    if cmd_opts.repair:
        Repair(cmd_opts).repair(validation_results)
        log.debug("Completed the repair.")

    generate_report(validation_results, cmd_opts)

    if cmd_opts.dump:
        dump_plugins = get_dump_plugin(validation_results)
        if dump_plugins:
            for dump_plugin in dump_plugins:
                if not dump_plugin.get_plugin_status():
                    return 1
            print("About to crash the kernel, press Ctrl+c to stop")
            time.sleep(5)
            trigger_kernel_crash()
        else:
            log.warning("Dump plugin not found, dummy dump not initiated")

    # Tool returns 1 even if a single check fails
    # in any plugin.
    for key in validation_results:
        for plugin in validation_results[key]:
            if not plugin.get_plugin_status():
                return 1
    return 0
