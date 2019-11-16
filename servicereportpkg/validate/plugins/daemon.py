# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check daemon availability"""


from servicereportpkg.check import DaemonCheck
from servicereportpkg.utils import is_daemon_enabled
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.validate.schemes.schemes import PSeriesScheme
from servicereportpkg.validate.schemes.schemes import BMCPowerNVScheme
from servicereportpkg.validate.schemes.schemes import FSPSPowerNVScheme
from servicereportpkg.validate.schemes.schemes import FedoraScheme
from servicereportpkg.validate.schemes.schemes import SuSEScheme
from servicereportpkg.validate.schemes.schemes import RHELScheme
from servicereportpkg.validate.schemes.schemes import UbuntuScheme


def generate_daemon_check(self, daemon):
    """Generates a function that checks the given daemon is enabled or not"""

    def check():
        check_daemon = daemon
        daemon_status = is_daemon_enabled(check_daemon)

        if daemon_status is None:
            self.log.warning("Unable to find %s daemon status", check_daemon)
        elif daemon_status is False:
            self.log.error("%s is not enabled" % check_daemon)
        else:
            self.log.info("%s is enabled" % check_daemon)

        return DaemonCheck(check_daemon, check_daemon, daemon_status)

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
