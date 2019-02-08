# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check HTX configuration"""


import os

from servicereportpkg.utils import get_file_content
from servicereportpkg.check import Check, SysfsCheck
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.utils import get_service_status
from servicereportpkg.validate.schemes.schemes import PowerPCScheme


class HTX(Plugin, PowerPCScheme):
    """HTX configuration check"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = HTX.__name__
        self.description = HTX.__doc__
        self.service_name = "htxd"
        self.installation_path = "/var/log/htx_install_path"

    def check_htx_installation_path(self):
        """HTX Installation path"""

        installation_path_exists = True

        if os.path.isfile(self.installation_path):
            htx_install_dir = get_file_content(self.installation_path)

            if (htx_install_dir is None) or \
               (not os.path.isdir(htx_install_dir)):
                self.log.error("Missing HTX installation directory %s",
                               htx_install_dir)
                installation_path_exists = False
        else:
            self.log.error("Unable to locate %s file", self.installation_path)
            installation_path_exists = False

        return Check(self.check_htx_installation_path.__doc__,
                     installation_path_exists)

    def check_htx_service_check(self):
        """HTX service status"""

        status = True
        if get_service_status(self.service_name) != 0:
            status = False
            self.log.debug("HTX service %s is not active", self.service_name)

        return SysfsCheck(self.check_htx_service_check.__doc__,
                          self.service_name, status)
