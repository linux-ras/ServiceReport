# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2020
# Author: Seeteena Thoufeek <s1seetee@linux.vnet.ibm.com>

"""Plugin to check RSCT configuration"""

import os

from servicereportpkg.check import Check
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.utils import execute_command
from servicereportpkg.check import PackageCheck, ServiceCheck
from servicereportpkg.utils import is_package_installed
from servicereportpkg.validate.schemes.schemes import PSeriesScheme


class RSCT(Plugin, PSeriesScheme):
    """RSCT configuration check"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = RSCT.__name__
        self.description = RSCT.__doc__
        self.optional = True
        self.installation_path = "/opt/rsct/bin"
        self.packages = [
            "rsct.core",
            "rsct.core.utils",
            "rsct.basic",
            "src",
            "devices.chrp.base.ServiceRM",
            "DynamicRM",
            ]
        self.subsystems = ["ctrmc", "IBM.DRM", "IBM.HostRM",
                           "IBM.ServiceRM", "IBM.MgmtDomainRM"]

    def check_rsct_installation_path(self):
        """RSCT Installation path"""

        installation_path_exists = True
        self.log.info("RSCT Installation path check")
        if not os.path.isdir(self.installation_path):
            self.log.error("Missing RSCT installation directory %s",
                           self.installation_path)
            installation_path_exists = False

        return Check(self.check_rsct_installation_path.__doc__,
                     installation_path_exists)

    def get_subsystem_status(self, subsystem):
        """Checks the subsystem status"""

        command = ["lssrc", "-s", subsystem]
        (return_code, stdout, err) = execute_command(command)

        if return_code is None or ("active" not in str(stdout)):
            self.log.info("Subsystem %s error %s", subsystem, str(err))
            return False

        return True

    def check_rsct_subsystem_check(self):
        """RSCT service status"""

        subsys_list = []
        subsys_status = True
        status = True
        self.log.info("RSCT Subsystem status check")
        for subsystem in self.subsystems:
            if not self.get_subsystem_status(subsystem):
                self.log.debug("%s Subsystem is not active", subsystem)
                subsys_status = False
                status = False
                subsys_list.append((subsystem, subsys_status))
            else:
                subsys_status = True
                subsys_list.append((subsystem, subsys_status))

        return ServiceCheck(self.check_rsct_subsystem_check.__doc__,
                            subsys_list, status)

    def check_rsct_package_check(self):
        """RSCT package check"""

        pkg_list = []
        pkg_status = True
        status = True
        self.log.info("RSCT Package check")
        for package in self.packages:
            if not is_package_installed(package):
                self.log.error("%s package is not installed", package)
                status = False
                pkg_status = False
                pkg_list.append((package, pkg_status))
            else:
                pkg_status = True
                pkg_list.append((package, pkg_status))

        return PackageCheck(self.check_rsct_package_check.__doc__,
                            pkg_list, status)

    def check_rsct_ibm_power_repo_check(self):
        """IBM Power Repo Package check"""

        status = True
        power_repo_package = "ibm-power-repo"
        self.log.info("ibm-power-repo Package check")
        if not is_package_installed(power_repo_package):
            self.log.error("ibm-power-repo package is not installed")
            status = False

        return PackageCheck(self.check_rsct_ibm_power_repo_check.__doc__,
                            power_repo_package, status)
