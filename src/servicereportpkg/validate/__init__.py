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

    def get_applicable_plugins(self):
        """Returns a dictionary of applicable plugins"""

        plugins = {}

        for plugin in self.plugin_handler.get_applicable_plugins():
            plugins_obj = plugin()
            plugin_name = plugins_obj.get_name().lower()

            if plugin_name not in plugins:
                plugins[plugin_name] = []

            plugins[plugin_name].append(plugins_obj)

        return plugins

    def is_plugin_executable(self, plugin_name, plugin_obj):
        """Check whether the give plugin is executable in current system
        environment"""

        if self.cmd_opts.all:
            return True

        if self.cmd_opts.plugins:
            return plugin_name in self.cmd_opts.plugins

        if plugin_obj.is_optional():
            if self.cmd_opts.optional:
                return plugin_name in self.cmd_opts.optional

            return False

        return True

    def arrange_execution_order(self, exe_plugins):
        """Decides the plugin execution order"""

        # Obey the order in which plugin are listed against -p or
        # --plugins option
        if self.cmd_opts.plugins:
            od_exe_plugin = OrderedDict()
            for plugin in self.cmd_opts.plugins:
                if plugin in exe_plugins:
                    od_exe_plugin[plugin] = exe_plugins[plugin]

            return od_exe_plugin

        return OrderedDict(sorted(exe_plugins.items()))

    def verify_listed_plugins(self, applicable_plugins, plugins):
        """Find and print if any invalid plugin is listed by user"""

        for plugin in plugins:
            if plugin not in applicable_plugins:
                print("Warning: %s plugin is either invalid or not applicable "
                      "to this system.\n" % plugin)

    def get_executable_plugins(self):
        """Return a dictionary of executable plugins"""

        exe_plugins = {}

        applicable_plugins = self.get_applicable_plugins()

        if self.cmd_opts.plugins:
            self.verify_listed_plugins(applicable_plugins,
                                       self.cmd_opts.plugins)

        if self.cmd_opts.optional:
            self.verify_listed_plugins(applicable_plugins,
                                       self.cmd_opts.optional)

        for plugin in applicable_plugins:
            plugin_objs = applicable_plugins[plugin]
            if self.is_plugin_executable(plugin, plugin_objs[0]):
                exe_plugins[plugin] = plugin_objs

        return self.arrange_execution_order(exe_plugins)

    def list_applicable_plugins(self):
        """List all the applicable plugins"""

        plugins = self.get_applicable_plugins()
        print("The following plugins are applicable:\n")
        print("   {0:20}{1:20}{2}\n".format("Name", "Tags", "Description"))
        for plugin in plugins:
            if not plugins[plugin][0].is_optional():
                print("   {0:20}{1:20}{2}".format(plugin, "M",
                      plugins[plugin][0].get_description()))
            else:
                print("   {0:20}{1:20}{2}".format(plugin, "O",
                      plugins[plugin][0].get_description()))

        print("\n{0}\n{1}\n{2}".format("Tag Info: ",
              "M: Mandatory plugin (runs by default)",
              "O: Optional plugin (use -o option to enable)"))

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
        plugin_dir = self.get_executable_plugins()

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
        if self.cmd_opts.dump:
            if is_string_in_file("fadump=on", "/proc/cmdline"):
                self.cmd_opts.plugins = ["fadump"]
            else:
                self.cmd_opts.plugins = ["kdump"]

        self.execute_plugins()
        return self.validation_results
