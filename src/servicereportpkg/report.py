# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Generate final report using the validation results"""


import os


class Color():
    """Maps the color with their ANSI escape codes"""

    RED = '\033[1;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'


def color_msg(msg, color):
    """Encodes the status string with the specified color"""

    color_end = '\033[0m'

    if color and os.getenv('ANSI_COLORS_DISABLED') is None:
        return color + str(msg) + color_end

    return str(msg)


def get_colored_status_msg(status):
    """Map the given status with their colored keyword"""

    status_to_color = {"PASS": Color.GREEN,
                       "FAIL": Color.RED,
                       "UNKNOWN": Color.YELLOW}

    status_msg = "PASS"
    if status is False:
        status_msg = "FAIL"
    elif status is None:
        status_msg = "UNKNOWN"

    return color_msg(status_msg, status_to_color[status_msg])


def print_report_on_console(validation_results, cmd_opts):
    """Prints the report on the terminal in table format
    [Plugin Description | Plugin status].
    If user either choose verbose or repair option then
    detailed report is printed on the terminal. The detailed
    report includes the information about every check performed
    during the validation."""

    for key in validation_results.keys():
        plugin_description = validation_results[key][0].get_description()
        overall_status = True
        for plugin in validation_results[key]:
            if not plugin.get_plugin_status():
                overall_status = False
                break

        print("{0:52}{1}\n".format(plugin_description,
                                   get_colored_status_msg(overall_status)))

        if cmd_opts.verbose < 1 and not cmd_opts.repair:
            continue

        for plugin_obj in validation_results[key]:
            for check in plugin_obj.checks:
                if check.get_note() is None:
                    print("  {0:50}{1}".format(check.get_name(),
                                               get_colored_status_msg(check.get_status())))
                else:
                    print("  {0:50}{1:20}{2}".format(check.get_name(),
                                                     get_colored_status_msg(check.get_status()),
                                                     check.get_note()))

            for check in plugin_obj.checks:
                message = check.get_message()
                if message is not None:
                    print(message)
        print('\n')


def generate_report(validation_results, cmd_opts):
    """Generate the report based on the validation results"""

    print_report_on_console(validation_results, cmd_opts)
