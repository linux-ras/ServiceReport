# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the package checks"""


from servicereportpkg.repair.plugins import RepairPlugin
from servicereportpkg.utils import install_package
from servicereportpkg.utils import is_package_installed
from servicereportpkg.check import Notes


class PackageRepair(RepairPlugin):
    """Install packages"""

    def __init__(self):
        RepairPlugin.__init__(self)
        self.name = "Package"

    def repair(self, plugin_obj, checks):
        """Repair package checks"""

        for check in checks:
            if not check.get_status():
                install_package(check.get_package_name())
                if is_package_installed(check.get_package_name()):
                    check.set_status(True)
                    check.set_note(Notes.FIXED)
                else:
                    check.set_note(Notes.FAIL_TO_FIX)
