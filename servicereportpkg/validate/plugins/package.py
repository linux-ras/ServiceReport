# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check package availability"""


from servicereportpkg.check import PackageCheck
from servicereportpkg.utils import is_package_installed
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.validate.schemes.schemes import FedoraScheme, RHELScheme
from servicereportpkg.validate.schemes.schemes import UbuntuScheme, SuSEScheme
from servicereportpkg.validate.schemes.schemes import PowerPCScheme, PowerNVScheme


def generate_package_check(self, pkg):
    """Generates a function that checks the given pkg is installed or not"""

    def check():
        package = pkg
        package_status = is_package_installed(package)

        if package_status is None:
            self.log.warning("Unable to find %s package status", package)
        elif package_status is False:
            self.log.error("%s package is not present", package)
        else:
            self.log.info("%s package is present", package)

        return PackageCheck(package, package, package_status)

    check.__doc__ = "%s" % (pkg)
    return check


class Package():
    """Package availability check"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = Package.__name__
        self.description = Package.__doc__
        for package in self.packages:
            setattr(self, "check_%s" % package,
                    generate_package_check(self, package))


class RHELPackage(Package, Plugin, RHELScheme):
    """Evaluates the packages on RHEL"""
    packages = ["sos", "perf"]


class FedoraPackage(Package, Plugin, FedoraScheme):
    """Evaluates the packages on Fedora"""
    packages = ["sos", "perf"]


class UbuntuPackage(Package, Plugin, UbuntuScheme):
    """Evaluates the packages on Ubuntu"""
    packages = ["sosreport", "linux-tools-generic", "linux-tools-common"]


class SuSEPackage(Package, Plugin, SuSEScheme):
    """Evaluates the packages of SuSE"""

    packages = ["supportutils", "perf"]


class PowerPCPackage(Package, Plugin, PowerPCScheme):
    """Evaluates the packages on PowerPC"""

    packages = ["ppc64-diag"]


class RHELPowerPCPackage(Package, Plugin, PowerPCScheme, RHELScheme):
    """Evaluates the RHEL packages on PowerPC"""

    packages = ["powerpc-utils"]


class FedoraPowerPCPackage(Package, Plugin, PowerPCScheme, FedoraScheme):
    """Evaluates the Fedora packages on PowerPC"""

    packages = ["powerpc-utils"]


class SuSEPowerPCPackage(Package, Plugin, PowerPCScheme, SuSEScheme):
    """Evaluates the SuSE packages on PowerPC"""

    packages = ["powerpc-utils"]


class UbuntuPowerPCPackage(Package, Plugin, PowerPCScheme, UbuntuScheme):
    """Evaluates the Ubuntu packages on PowerPC"""

    packages = ["powerpc-ibm-utils"]


class PowerNVPackage(Package, Plugin, PowerNVScheme):
    """Evaluates the packages on PowerNV platform of Power systems"""

    packages = ["opal-prd"]
