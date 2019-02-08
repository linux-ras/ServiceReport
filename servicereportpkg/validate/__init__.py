# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Driving module for validation tool. Responsible for detecting and running
the validation scenarios."""


from collections import OrderedDict

from servicereportpkg.utils import is_string_in_file
from servicereportpkg.global_context import TOOL_NAME
from servicereportpkg.logger import get_default_logger
from servicereportpkg.validate.schemes import SchemeHandler
from servicereportpkg.validate.plugins import PluginHandler
from servicereportpkg.logger import change_log_identifier


class Validate(object):
    """Primary class for validation tool."""

    def __init__(self, cmd_opts):
        self.cmd_opts = cmd_opts
        self.log = get_default_logger()
        self.scheme_handler = SchemeHandler()
        self.plugin_handler = PluginHandler(self.scheme_handler)
        self.validation_results = OrderedDict()

    def get_plugin_dir(self, plugins=None):
        """Returns an ordered directory of list of executable plugins"""

        plugin_dir_tmp = OrderedDict()

        for plugin in self.plugin_handler.get_applicable_plugins():
            plugins_obj = plugin()
            plugin_name = plugins_obj.get_name().lower()
            if plugin_name not in plugin_dir_tmp.keys():
                plugin_dir_tmp[plugin_name] = []
            plugin_dir_tmp[plugin_name].append(plugins_obj)

        # By default plugins are executed in sorted order but If plugins
        # are specified using -p option then the execution order should be
        # same as specified on command line
        if plugins:
            plugin_dir = OrderedDict()
            for plugin in plugins:
                plugin = plugin.lower()
                if plugin in plugin_dir_tmp.keys():
                    if plugin not in plugin_dir.keys():
                        plugin_dir[plugin] = plugin_dir_tmp[plugin]
                else:
                    print("%s plugin is not applicable" % plugin)

            return plugin_dir

        return OrderedDict(sorted(plugin_dir_tmp.items(),
                                  key=lambda tmp: tmp[0]))

    def list_applicable_plugins(self):
        """List all the applicable plugins"""

        plugins = self.get_plugin_dir()
        print("The following plugins are applicable:\n")
        for plugin in plugins:
            print("   {0:25}{1}".format(plugin,
                                        plugins[plugin][0].get_description()))


    def do_execute_plugin(self, plugin):
        """Execute the plugin"""

        try:
            return plugin.validate()
        except Exception as exception:
            self.log.error("Failed to execute plugins: %s reason: %s",
                           plugin.__class__.__name__, exception)
            return False

    def execute_plugins(self):
        """Collect all the executable plugins objects, change the journal
        handler identifier and execute the plugin"""

        successful_plugin_obj = []
        plugin_dir = self.get_plugin_dir(self.cmd_opts.plugins)

        for plugin in plugin_dir:
            change_log_identifier(TOOL_NAME + '.' + plugin, self.log)

            plugin_objs = plugin_dir[plugin]

            # if a plugin fails to execute due an exception then
            # plugin will not be the part of final output
            for plugin_obj in plugin_objs:
                self.do_execute_plugin(plugin_obj)
                successful_plugin_obj.append(plugin_obj)


        change_log_identifier(TOOL_NAME, self.log)
        for plugin_obj in successful_plugin_obj:
            if plugin_obj.get_name() not in self.validation_results.keys():
                self.validation_results[plugin_obj.get_name()] = []

            self.validation_results[plugin_obj.get_name()].append(plugin_obj)

    def validate(self):
        """Validates the system configuration"""

        # Make sure that if -d (--dump) is provided then only
        # dump plugin should run
        if self.cmd_opts.dump and self.cmd_opts.plugins is None:
            if is_string_in_file("fadump=on", "/proc/cmdline"):
                self.cmd_opts.plugins = ["FADump"]
            else:
                self.cmd_opts.plugins = ["Kdump"]

        self.execute_plugins()
        return self.validation_results
