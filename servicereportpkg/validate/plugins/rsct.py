# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2020
# Author: Seeteena Thoufeek <s1seetee@linux.vnet.ibm.com>

"""Plugin to check RSCT configuration"""


import os
import sys

from servicereportpkg.check import Check, SysfsCheck
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.utils import execute_command
from servicereportpkg.check import PackageCheck,ServiceCheck
from servicereportpkg.utils import is_package_installed
from servicereportpkg.logger import get_default_logger
from servicereportpkg.validate.schemes.schemes import PSeriesScheme

class RSCT(Plugin, PSeriesScheme):
    """RSCT configuration check"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = RSCT.__name__
        self.description = RSCT.__doc__
        self.service_name = "ctrmc"
        self.installation_path = "/opt/rsct/bin"
        self.packages = ["rsct.core","rsct.core.utils","rsct.basic","src",
                "devices.chrp.base.ServiceRM","DynamicRM"]
        self.subsystems = ["ctrmc","IBM.DRM","IBM.HostRM","IBM.ServiceRM",
                "IBM.MgmtDomainRM"]
        self.subsystem_active = "active"

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

    def get_subsystem_status(self,subsystem):
        """Checks the subsystem status by issuing the lssrc command"""
        
        command = ["lssrc", "-s", subsystem]
        (return_code,stdout,err) = execute_command(command)
        
        if return_code is None or self.subsystem_active not in str(stdout):
            return False
            
        return True

    def check_rsct_subsystem_check(self):
        """RSCT service status"""

        status = True
        self.log.info("RSCT Subsystem status check")
        for subsystem in self.subsystems:
            if self.get_subsystem_status(subsystem) ==0:
             self.log.debug("%s Subsystem is not active", subsystem)
             status = False

        return ServiceCheck(self.check_rsct_subsystem_check.__doc__, 
                subsystem, status)

    def check_rsct_package(self):
        """RSCT package check"""

        status = True
        self.log.info("RSCT Package check")
        for package in self.packages:
          if not is_package_installed(package):
            self.log.error("%s package is not installed", package)
            status = False

        return PackageCheck(self.check_rsct_package.__doc__,
                            package, status)

