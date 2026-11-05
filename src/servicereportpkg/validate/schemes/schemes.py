# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Provide scheme classes"""


import platform

from servicereportpkg.validate.schemes import Scheme
from servicereportpkg.utils import get_service_processor
from servicereportpkg.utils import get_distro_name, get_system_platform

DISTRO = get_distro_name()


class RHELScheme(Scheme):
    """Applicable to RHEL distro"""

    @classmethod
    def is_valid(cls):
        return "Red Hat" in DISTRO


class FedoraScheme(Scheme):
    """Applicable to Fedora distro"""

    @classmethod
    def is_valid(cls):
        return "Fedora" in DISTRO


class SuSEScheme(Scheme):
    """Applicable to SuSE distro"""

    @classmethod
    def is_valid(cls):
        return "SUSE" in DISTRO


class UbuntuScheme(Scheme):
    """Applicable to Ubuntu distro"""

    @classmethod
    def is_valid(cls):
        return "Ubuntu" in DISTRO


class PowerPCScheme(Scheme):
    """Applicable to all platforms of PowerPC machine"""

    @classmethod
    def is_valid(cls):
        return "ppc64" in platform.machine()


class PowerNVScheme(Scheme):
    """Applicable to PowerNV platform of PowerPC"""

    @classmethod
    def is_valid(cls):
        if not PowerPCScheme.is_valid() or \
               get_system_platform() != "powernv":
            return False

        return True


class FSPSPowerNVScheme(PowerNVScheme):
    """Applicable to FSPS based PowerNV systems"""

    @classmethod
    def is_valid(cls):
        if not PowerNVScheme.is_valid() or \
               get_service_processor() != "fsps":
            return False

        return True


class BMCPowerNVScheme(PowerNVScheme):
    """Applicable to BMC based PowerNV systems"""

    @classmethod
    def is_valid(cls):
        if not PowerNVScheme.is_valid() or \
               get_service_processor() != "bmc":
            return False

        return True


class PSeriesScheme(PowerPCScheme):
    """Applicable to PSeries platform of PowerPC"""

    @classmethod
    def is_valid(cls):
        if not PowerPCScheme.is_valid() or \
               get_system_platform() != "pseries":
            return False

        return True
