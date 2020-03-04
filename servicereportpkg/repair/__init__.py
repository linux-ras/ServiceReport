# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Driving module for repair package"""


from servicereportpkg.global_context import TOOL_NAME
from servicereportpkg.logger import get_default_logger
from servicereportpkg.repair.plugins import RepairPluginHandler
from servicereportpkg.logger import change_log_identifier

class Repair(object):
    """Base class of all repair plugins"""

    def __init__(self, cmd_opts):
        self.cmd_opts = cmd_opts
        self.log = get_default_logger()
        self.repair_plugin_handler = RepairPluginHandler()

    def repair(self, validation_results):
        """Go through all the validation plugins and try to
        fix the failed plugins by calling their corresponding
        repair plugin if available."""

        repair_plugins = self.repair_plugin_handler.get_repair_plugins()

        self.log.debug("Start repairing the failed plugins.")
        for plugin in validation_results.keys():
            # Find whether repair plugin is available or not
            if plugin in repair_plugins.keys():
                repair_plugin_obj = repair_plugins[plugin]()
                change_log_identifier(TOOL_NAME+ '.' + plugin, self.log)

                for plugin_obj in validation_results[plugin]:
                    repair_plugin_obj.repair(plugin_obj, plugin_obj.checks)
            else:
                self.log.debug("Repair plugin is not available for %s", plugin)

        change_log_identifier(TOOL_NAME, self.log)
    def repair_plugin(self,validation_results,plugins):
        
        repair_plugin=self.repair_plugin_handler.get_repair_plugins()
        for plugin in plugins:
            if plugin in repair_plugin.keys():
                repair_plugin_obj = repair_plugin[plugin]()
                for plugin_obj in validation_results[plugin]:
                    repair_plugin_obj.repair(plugin_obj, plugin_obj.checks)
            else:
                self.log.debug("Repair plugin is not available for %s", plugin)
        change_log_identifier(TOOL_NAME, self.log)

