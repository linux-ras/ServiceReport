#SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2020
# Author: Seeteena Thoufeek  <s1seetee@linux.vnet.ibm.com>

"""Plugin to repair the rsct configuration check"""


from servicereportpkg.repair.plugins import RepairPlugin
from servicereportpkg.check import Notes
from servicereportpkg.utils import execute_command
from servicereportpkg.validate.schemes.schemes import PSeriesScheme
from servicereportpkg.utils import install_package


class RSCTRepair(RepairPlugin, PSeriesScheme):
    """Plugin to repair the RSCT configuration check"""

    def __init__(self):
        RepairPlugin.__init__(self)
        self.name = 'RSCT'
        self.optional = True

    def enable_subsystem(self, plugin_obj, check):
        """Enables the subsystem if not active"""

        subsys_list = check.get_service()
        for subsystem in subsys_list:
            subsystem_status = subsystem[1]
            if subsystem_status is False:
                command = ["startsrc", "-s", subsystem[0]]
                execute_command(command)
        re_check = plugin_obj.check_rsct_subsystem_check()
        if re_check.get_status():
            self.log.debug("Subsystems active")
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            self.log.debug("Subsystems not active")
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_rsct_package(self, plugin_obj, check):
        """fix rsct package"""

        self.log.info("RSCT package repair")
        pkg_list = check.get_package_name()
        for package in pkg_list:
            install_package(package[0])
        re_check = plugin_obj.check_rsct_package_check()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_rsct_install_path(self, plugin_obj, check):
        """Fix rsct install path"""

        re_check = plugin_obj.check_rsct_installation_path()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def repair(self, plugin_obj, checks):
        """Repair rsct subsystem checks"""

        self.log.info("RSCT Subsystem Repair")
        check_dir = {}
        for check in checks:
            check_dir[check.get_name()] = check

        rsct_package_check = check_dir["RSCT package check"]
        self.log.debug("package_check: %s", rsct_package_check.get_name())
        if not rsct_package_check.get_status():
            rsct_power_repo_check = \
                check_dir["IBM Power Repo Package Check"]
            self.log.debug("rsct_power_repo_check %s",
                           rsct_power_repo_check.get_name())
            if not rsct_power_repo_check.get_status():
                rsct_power_repo_check.set_note(Notes.NOT_FIXABLE + "\n \n \
WARNING!!!! ibm-power-repo package needs to be enabled to install rsct \
packages on this machine. \n Please follow below steps to install \
ibm-power-repo package. \n 1. Download and install ibm-power-repo package. \
\n 2. run /opt/ibm/lop/configure to agree with the license. \
\n Refer https://www.ibm.com/support/pages/service-and-productivity-tools \
for more details")
                return
            if rsct_package_check.get_status() is False:
                self.fix_rsct_package(plugin_obj, rsct_package_check)
            elif rsct_package_check.get_status() is None:
                rsct_package_check.set_note(Notes.FAIL_TO_FIX)

        if "RSCT Installation path" in check_dir.keys():
            rsct_install_exists = check_dir["RSCT Installation path"]
            if rsct_install_exists.get_status() is False:
                self.fix_rsct_install_path(plugin_obj, rsct_install_exists)
            elif rsct_install_exists.get_status() is None:
                rsct_install_exists.set_note(Notes.FAIL_TO_FIX)

        if "RSCT service status" in check_dir.keys():
            rsct_service_check = check_dir["RSCT service status"]
            self.log.debug("rsct_service_check %s %s",
                           rsct_service_check.get_status(),
                           rsct_service_check.get_service())
        if rsct_service_check.get_status() is False:
            self.enable_subsystem(plugin_obj, rsct_service_check)
        elif rsct_service_check.get_status() is None:
            rsct_service_check.set_note(Notes.FAIL_TO_FIX)
