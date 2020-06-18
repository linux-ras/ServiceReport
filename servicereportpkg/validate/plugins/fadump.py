# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check FADump configuration"""


import os
import sys

from servicereportpkg.check import SysfsCheck
from servicereportpkg.check import FileCheck
from servicereportpkg.check import PackageCheck
from servicereportpkg.utils import get_total_ram
from servicereportpkg.utils import execute_command
from servicereportpkg.utils import get_file_content
from servicereportpkg.utils import is_string_in_file
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.utils import is_package_installed
from servicereportpkg.logger import get_default_logger
from servicereportpkg.validate.plugins.kdump import Dump
from servicereportpkg.validate.schemes.schemes import PowerPCScheme
from servicereportpkg.validate.schemes.schemes import FedoraScheme, RHELScheme
from servicereportpkg.validate.schemes.schemes import UbuntuScheme, SuSEScheme


class FADump(Dump):
    """FADump configuration check"""

    def __init__(self):
        Dump.__init__(self)
        self.name = FADump.__name__
        self.description = FADump.__doc__
        self.dump_service_name = "kdump"
        self.dump_comp_name = "kdump"
        # (system mem, mem reservation needed)
        # (GB, MB)
        self.log = get_default_logger()
        self.capture_kernel_mem = [(4, 0),
                                   (64, 1024),
                                   (128, 2048),
                                   (1024, 4096),
                                   (2048, 6144),
                                   (4096, 12288),
                                   (8192, 20480),
                                   (16384, 36864),
                                   (32786, 65536),
                                   (65536, 131072),
                                   (sys.maxsize, 184320)]

    @classmethod
    def is_applicable(cls):
        """Returns true if boot cmdline contain fadump=on"""

        if is_string_in_file("fadump=on", "/proc/cmdline"):
            return True

        return False


    def check_fadump_enabled(self):
        """FADump enabled check"""

        status = True
        sys_kernel_fadump_enabled = "/sys/kernel/fadump_enabled"
        fadump_enabled = get_file_content(sys_kernel_fadump_enabled)

        try:
            if fadump_enabled is None or int(fadump_enabled) != 1:
                self.log.error("FADump is not enabled")
                status = False
            else:
                self.log.info("FADump is enabled")

        except ValueError as value_error:
            self.log.debug("Invalid data found in file %s, error: %s",
                           sys_kernel_fadump_enabled, value_error)
            status = False

        return SysfsCheck(self.check_fadump_enabled.__doc__,
                          sys_kernel_fadump_enabled, status)

    def check_fadump_registered(self):
        """FADump registration check"""

        status = True
        sys_kernel_fadump_registered = "/sys/kernel/fadump_registered"
        fadump_registered = get_file_content(sys_kernel_fadump_registered)

        try:
            if fadump_registered is None or int(fadump_registered) != 1:
                self.log.error("FADump is not registered")
                status = False
            else:
                self.log.info("FADump is registered")

        except ValueError as value_error:
            self.log.debug("Invalid data found in file %s, error: %s",
                           sys_kernel_fadump_registered, value_error)
            status = False

        return SysfsCheck(self.check_fadump_registered.__doc__,
                          sys_kernel_fadump_registered, status)

    def get_mem_reserved(self):
        """Returns the size of memory reserved by fadump in MB"""

        fadump_mem_file = "/sys/kernel/fadump_mem_reserved"
        if os.path.exists(fadump_mem_file):
            fadump_mem = get_file_content(fadump_mem_file)
            if fadump_mem is None:
                self.log.debug("Unable to get fadump mem size from %s",
                               fadump_mem_file)
                return None
            else:
                try:
                    self.log.debug("%s: %s", fadump_mem_file, fadump_mem)
                    return int(fadump_mem) / 1024 / 1024
                except Exception:
                    self.log.debug("Invalid value (%s) found in %s file:",
                                   fadump_mem, fadump_mem_file)
            return None

        fadump_region_file = "/sys/kernel/debug/powerpc/fadump_region"
        if not os.path.exists(fadump_region_file):
            debugfs = "/sys/kernel/debug"
            command = ["mount", "-t", "debugfs", "nodev", debugfs]

            self.log.debug("Mounting %s", debugfs)
            if execute_command(command)[0] != 0:
                self.log.debug("Unable to mount %s", debugfs)
                return None

            if not os.path.exists(fadump_region_file):
                self.log.debug("%s file not found", fadump_region_file)
                return None

        fadump_regions = get_file_content(fadump_region_file)
        if fadump_regions is None:
            return None

        fadump_mem = 0
        for region in fadump_regions.split('\n'):
            self.log.debug("Fadump region(%s)", region)
            region = region.strip()
            try:
                if region.startswith("CPU") or region.startswith("HPTE"):
                    region_size = region[region.find(':')+1 : len(region)].strip().split()[1]
                elif region.startswith("DUMP"):
                    region_list = region.split()
                    if len(region_list) > 6:
                        region_size = region_list[4][:-1]
                    else:
                        region_size = region_list[2]
                else:
                    self.log.warning("Unknown Fadump region(%s)", region)
                    continue
                fadump_mem = fadump_mem + int(region_size, 16)

            except Exception:
                self.log.debug("Unable to parse %s", fadump_region_file)
                return None

        self.log.debug("Fadump mem from (%s): %s bytes", fadump_region_file, fadump_mem)
        return fadump_mem / 1024 / 1024

    def get_crash_mem_needed(self):
        """Returns the memory needs to be reserved for crash dump in MB"""

        ram = get_total_ram()

        if ram is None:
            self.log.debug("Failed to detect total ram")
            return None

        # change from KB to MB
        ram = ram / 1024 / 1024

        for (sys_mem, mem_reservation_needed) in self.capture_kernel_mem:
            if ram <= sys_mem:
                return mem_reservation_needed

    def check_mem_reservation(self):
        """Memory reservation"""

        status = True

        mem_needed = self.get_crash_mem_needed()
        mem_reserved = self.get_mem_reserved()

        if mem_needed is None or mem_reserved is None:
            status = None
        elif mem_needed > mem_reserved:
            self.log.error("Memory reserved for FADump is insufficient")
            self.log.recommendation("Increase the memory reservation to %d MB",
                                    mem_needed)
            status = False

        if status:
            self.log.info("Sufficient memory reserved for dump collection")

        mem_reserve_check = SysfsCheck(self.check_mem_reservation.__doc__,
                                       "", status)
        mem_reserve_check.set_sysfs_value_found(mem_reserved)
        mem_reserve_check.set_sysfs_expected_value(mem_needed)

        return mem_reserve_check


class FADumpFedora(FADump, Plugin, FedoraScheme):
    """Validates the FADump on Fedora"""

    def __init__(self):
        Plugin.__init__(self)
        FADump.__init__(self)
        self.initial_ramdisk = "/boot/initramfs-" \
                               + self.kernel_release + ".img"


class FADumpRHEL(FADump, Plugin, RHELScheme, PowerPCScheme):
    """Validates the FADump on RHEL"""

    def __init__(self):
        Plugin.__init__(self)
        FADump.__init__(self)
        self.initial_ramdisk = "/boot/initramfs-" \
                               + self.kernel_release + ".img"


class FADumpSuSE(FADump, Plugin, SuSEScheme, PowerPCScheme):
    """Validates the FADump on SuSE"""

    def __init__(self):
        Plugin.__init__(self)
        FADump.__init__(self)
        self.initial_ramdisk = "/boot/initrd-" \
                               + self.kernel_release

    def check_kdump_sysconfig(self):
        """Fadump attributes in /etc/sysconfig/kdump"""

        sysconfig_kdump = "/etc/sysconfig/kdump"
        status = True
        found_kdump_fadump_attr = False

        try:
            with open(sysconfig_kdump) as file_o:
                for line in file_o:
                    # let the loop continue in case we have multiple
                    # entries for KDUMP_FADUMP attributes
                    if line.startswith("KDUMP_FADUMP="):
                        found_kdump_fadump_attr = True
                        (attr, val) = line.split('=')
                        val = val.strip()

                        if len(val) > 2 and (val.startswith('"') or val.startswith("'")):
                            if val[0] != val[-1]:
                                status = False
                            val = val[1:-1]

                        if val != "yes":
                            status = False

            if not found_kdump_fadump_attr:
                status = False

        except Exception as exception:
            status = False
            self.log.debug("Failed to access %s, reason: %s", sysconfig_kdump,
                           exception)

        if not status:
            if found_kdump_fadump_attr:
                self.log.error("KDUMP_FADUMP attribute in %s has incorrect value",
                               sysconfig_kdump)
                self.log.recommendation("Update KDUMP_FADUMP attribute value to yes in %s",
                                        sysconfig_kdump)
            else:
                self.log.error("KDUMP_FADUMP attribute is not available in %s",
                               sysconfig_kdump)
                self.log.recommendation('Add KDUMP_FADUMP="yes" in %s',
                                        sysconfig_kdump)

        return FileCheck(self.check_kdump_sysconfig.__doc__,
                         sysconfig_kdump, status)

    def check_kdump_package(self):
        """kdump package"""

        status = True
        package = "kdump"

        if not is_package_installed(package):
            status = False
            self.log.error("%s package is not installed", package)

        return PackageCheck(self.check_kdump_package.__doc__,
                            package, status)


class FADumpUbuntu(FADump, Plugin, UbuntuScheme, PowerPCScheme):
    """Validates the FADump on Ubuntu"""

    def __init__(self):
        Plugin.__init__(self)
        FADump.__init__(self)
        self.initial_ramdisk = "/boot/initrd.img-" \
                               + self.kernel_release
        self.kdump_service_name = "kdump-tools"
