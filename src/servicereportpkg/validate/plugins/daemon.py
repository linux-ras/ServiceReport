# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check daemon availability"""


from servicereportpkg.check import DaemonCheck
from servicereportpkg.utils import is_daemon_enabled
from servicereportpkg.utils import get_service_status
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.validate.schemes.schemes import PSeriesScheme
from servicereportpkg.validate.schemes.schemes import BMCPowerNVScheme
from servicereportpkg.validate.schemes.schemes import FSPSPowerNVScheme
from servicereportpkg.validate.schemes.schemes import FedoraScheme
from servicereportpkg.validate.schemes.schemes import SuSEScheme
from servicereportpkg.validate.schemes.schemes import RHELScheme
from servicereportpkg.validate.schemes.schemes import UbuntuScheme


def generate_daemon_check(self, daemon):
    """Generates a function to check daemon status"""

    def check():
        status = True
        enabled = is_daemon_enabled(daemon)

        if enabled is None:
            self.log.warning("Unable to find %s daemon status", daemon)
        elif enabled is False:
            self.log.error("%s is not enabled" % daemon)

        active = get_service_status(daemon)
        if active is None or active != 0:
            self.log.error("%s daemon is not active", daemon)
            self.log.recommendation("Start the service: systemctl start %s",
                                    daemon)
            active = False
        else:
            self.log.info("%s is active" % daemon)
            active = True

        if enabled is None or active is None:
            status = None
        elif enabled is False or active is False:
            status = False

        return DaemonCheck(daemon, status, enabled, active)

    check.__doc__ = "%s" % (daemon)
    return check


class Daemon():
    """Daemon availability checks"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = Daemon.__name__
        self.description = Daemon.__doc__
        for daemon in self.daemons:
            setattr(self, "check_%s" % daemon,
                    generate_daemon_check(self, daemon))


class FedoraDaemon(Daemon, Plugin, FedoraScheme):
    """Evaluates the daemons on Fedora"""

    daemons = ["irqbalance"]


class REHLDaemon(Daemon, Plugin, RHELScheme):
    """Evaluates the daemons on Fedora"""

    daemons = ["irqbalance"]


class SuSEDaemon(Daemon, Plugin, UbuntuScheme):
    """Evaluates the daemons on Fedora"""

    daemons = ["irqbalance"]


class UbuntuDaemon(Daemon, Plugin, SuSEScheme):
    """Evaluates the daemons on Fedora"""

    daemons = ["irqbalance"]


class PSeriesDaemon(Daemon, Plugin, PSeriesScheme):
    """Evaluates the daemons on PowerPC PSeries platform"""

    daemons = ["rtas_errd"]


class FSPSPowerNVDaemon(Daemon, Plugin, FSPSPowerNVScheme):
    """Evaluates the daemons on FSPS service processor based PowerNV
    machines"""

    daemons = ["opal_errd"]


class BMCPowerNVDaemon(Daemon, Plugin, BMCPowerNVScheme):
    """Evaluates the daemons on BMC service processor based PowerNV machines"""

    daemons = ["opal-prd"]
