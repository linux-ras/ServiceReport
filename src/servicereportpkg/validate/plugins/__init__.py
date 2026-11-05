# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Parent module for all plugins"""


from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import get_package_classes


class Plugin(object):
    """Base class for the Plugins."""

    def __init__(self):
        self.name = Plugin.__name__
        self.description = Plugin.__doc__
        self.optional = False
        self.log = get_default_logger()
        self.checks = []

    def get_name(self):
        """Returns plugin name, if a plugin does not define the plugin name
        then the class name will be returned"""

        return self.name

    def get_description(self):
        """Returns plugin description, if a plugin does not define the plugin
        the description then the class name will be returned"""

        return self.description

    def is_optional(self):
        """Return True if plugin is optional else False"""

        return self.optional

    def get_plugin_status(self):
        """Returns the overall status of the plugin. Returns True only if all
        the checks succeed else False"""

        for check in self.checks:
            if not check.get_status():
                return False

        return True

    @classmethod
    def is_applicable(cls):
        """Let plugin decides whether it is applicable to the current
        environment or not"""

        return True

    def validate(self):
        """Get all the functions that start with check_ from a plugin and
        call them sequentially, then creates an instance of Check class for
        each check function and add it to the checks list"""

        plugin_status = True
        check_methods = [method for method in dir(self)
                         if method.startswith("check_")]

        check = None
        for check_method in check_methods:
            try:
                check_method_obj = getattr(self, check_method)
                if not callable(check_method_obj):
                    continue

                check = check_method_obj()
            except Exception as exception:
                self.log.error("Failed to verify %s reason: %s",
                               check_method, exception)
                plugin_status = False
                check = None
                continue

            if check is not None and check.get_name() is not None:
                self.checks.append(check)
                if plugin_status and not check.get_status():
                    plugin_status = False

        return plugin_status


class PluginHandler(object):
    """Handles the plugins package"""

    def __init__(self, scheme_handler):
        self.log = get_default_logger()
        self.scheme_handler = scheme_handler
        self.populate_plugins()
        self.populate_applicable_plugin()

    def get_plugins(self):
        """Returns a list of all the plugins present in plugins package"""

        return self.plugins

    def get_applicable_plugins(self):
        """Returns a list of applicable plguins"""

        return self.applicable_plugins

    def populate_plugins(self):
        """Find all the available plugins"""

        self.plugins = []

        for _class in get_package_classes(__path__, 'servicereportpkg.validate.plugins.'):
            if issubclass(_class, Plugin):
                self.plugins.append(_class)

    def scheme_check(self, plugin):
        """Return true if all the schemes inherited by the plugin are valid"""

        for base in plugin.__bases__:
            if base in self.scheme_handler.get_schemes() and \
                    base not in self.scheme_handler.get_valid_schemes():
                return False

        return True

    def populate_applicable_plugin(self):
        """Filters the applicable plugins from available plguins"""

        self.applicable_plugins = []

        for plugin in self.plugins:
            if self.scheme_check(plugin) and plugin.is_applicable():
                self.applicable_plugins.append(plugin)
