# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Parent module for all repair plugins"""


from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import get_package_classes

class RepairPlugin(object):
    """Base class for the Repair Plugins"""

    def __init__(self):
        self.name = RepairPlugin.__name__
        self.log = get_default_logger()

    def get_name(self):
        """Returns the repair plugin name"""

        return self.name

    def repair(self, plugin_obj, checks):
        """Repair and update the status of all the received checks"""

        pass

class RepairPluginHandler(object):
    """Handles the repair plugin package"""

    def __init__(self):
        self.log = get_default_logger()
        self.repair_plugins = {}
        self.populate_repair_plugins()

    def get_repair_plugins(self):
        """Returns a dic of repair plugin"""

        return self.repair_plugins

    def populate_repair_plugins(self):
        """Scan the repair plugin package and populate
        the repair_plugin dic"""

        for _class in get_package_classes(__path__, 'servicereportpkg.repair.plugins.'):
            if issubclass(_class, RepairPlugin):
                self.repair_plugins[_class().get_name()] = _class
