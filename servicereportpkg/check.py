# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Module provides different Check classes to store validation information"""


class Check(object):
    """A check performed in a plugin is stored as a Check class instance"""

    def __init__(self, name, status=None, note=None):
        self.name = name
        self.status = status
        self.note = note

    def get_name(self):
        """Return the check name"""

        return self.name

    def get_status(self):
        """Return the check status"""

        return self.status

    def set_status(self, status):
        """Set the check status"""

        self.status = status

    def get_note(self):
        """Returns the check note"""

        return self.note

    def set_note(self, note):
        """Set the check note"""

        self.note = note


class ServiceCheck(Check):
    """Manage service check information"""

    def __init__(self, name, service, status=None, note=None):
        Check.__init__(self, name, status, note)
        self.service = service

    def get_service(self):
        """Return the service name"""

        return self.service


class DaemonCheck(Check):
    """Manage daemon check information"""

    def __init__(self, name, daemon, status=None, note=None):
        Check.__init__(self, name, status, note)
        self.daemon = daemon

    def get_daemon(self):
        """Returns the daemon name"""

        return self.daemon


class PackageCheck(Check):
    """Manage package check information"""

    def __init__(self, name, package_name, status=None, note=None):
        Check.__init__(self, name, status, note)
        self.package_name = package_name

    def get_package_name(self):
        """Returns the package name"""

        return self.package_name


class FileCheck(Check):
    """Manage file check information"""

    def __init__(self, name, file_path, status=None, note=None):
        Check.__init__(self, name, status, note)
        self.file_path = file_path

    def get_file_path(self):
        """Returns the file path"""

        return self.file_path


class SysfsCheck(FileCheck):
    """Manage sysfs file check information"""

    def __init__(self, name, file_path, status=None, note=None):
        FileCheck.__init__(self, name, file_path, status, note)
        self.expected_value = None
        self.value_found = None

    def set_sysfs_expected_value(self, value):
        """Set the expected value"""

        self.expected_value = value

    def get_sysfs_expected_value(self):
        """Returns the expected value"""

        return self.expected_value

    def set_sysfs_value_found(self, value):
        """Set the value found in sysfs file"""

        self.value_found = value

    def get_sysfs_value_found(self):
        """Returns the value stored in sysfs file"""

        return self.value_found


class ConfigurationFileCheck(FileCheck):
    """Manages config_attributes files check information"""

    def __init__(self, name, file_path, status=None, note=None):
        FileCheck.__init__(self, name, file_path, status, note)
        self.config_attributes = {}

    def get_config_attributes(self):
        """Returns the configuration file attributes"""

        return self.config_attributes

    def add_attribute(self, attribute,
                      is_config_correct, configured_value,
                      possible_values):
        """Add new attribute to configuration attribute dictionary"""

        self.config_attributes[attribute] = {"status": is_config_correct,
                                             "current_value": configured_value,
                                             "possible_values": possible_values}


class Notes(object):
    """Stores common notes used to define the status of the
    check after the repair operation"""

    FIXED = "Auto Fixed"
    FAIL_TO_FIX = "Unable to Fix"
    NOT_FIXABLE = "Not Auto-Fixable"
    FIXED_NEED_REBOOT = "Auto Fixed, Needs Reboot"
    MANUAL_FIX = "Manual Fix Needed"
