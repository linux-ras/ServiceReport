# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Authors: Srikanth Aithal <sraithal@linux.vnet.ibm.com>
#          Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check Kdump configuration"""


import os
import sys
import platform
import subprocess

from servicereportpkg.utils import is_package_installed
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import get_file_content, get_total_ram
from servicereportpkg.utils import get_file_size, is_string_in_file
from servicereportpkg.check import PackageCheck, ServiceCheck, Check
from servicereportpkg.check import SysfsCheck, ConfigurationFileCheck
from servicereportpkg.check import FileCheck
from servicereportpkg.utils import get_service_status, execute_command
from servicereportpkg.validate.schemes.schemes import FedoraScheme, SuSEScheme
from servicereportpkg.validate.schemes.schemes import RHELScheme, UbuntuScheme


class Dump(object):
    """Validates generic dump configurations"""

    def __init__(self):
        self.dump_service_name = ""
        self.dump_comp_name = ""
        self.initial_ramdisk = ""
        self.log = get_default_logger()
        self.kernel_release = platform.release()
        self.active_dump = "/proc/vmcore"

    def check_is_dump_service_active(self):
        """Service status"""

        status = True
        service_status = get_service_status(self.dump_service_name)

        if service_status is None or service_status != 0:
            self.log.error("%s service is not active", self.dump_service_name)
            self.log.recommendation("Start the service: systemctl start %s",
                                    self.dump_service_name)
            self.log.info("%s service may remains inactive if memory reservation fails",
                          self.dump_service_name)
            status = False

        return ServiceCheck(self.check_is_dump_service_active.__doc__,
                            self.dump_service_name, status)


    def check_dump_component_in_initrd(self):
        """Dump component in initial ramdisk"""

        status = True

        if not os.path.isfile(self.initial_ramdisk):
            self.log.error("Initial ramdisk not found %s",
                           self.initial_ramdisk)
            status = False

        elif get_file_size(self.initial_ramdisk) < 1:
            self.log.error("Initial ramdisk file is empty")
            status = False

        else:
            (return_code, stdout) = execute_command(["lsinitrd", "-m",
                                                     self.initial_ramdisk])[:-1]

            if return_code is None:
                self.log.error("Failed to verify %s component in Initial ramdisk",
                               self.dump_comp_name)
                status = False

            elif self.dump_comp_name not in str(stdout):
                self.log.error("kdump component is missing in %s",
                               self.initial_ramdisk)
                status = False

            else:
                self.log.debug("%s component found in %s", self.dump_comp_name,
                               self.initial_ramdisk)

        return Check(self.check_dump_component_in_initrd.__doc__,
                     status)

    def check_kexec_package(self):
        """kexec package"""

        status = True
        package = "kexec-tools"

        if not is_package_installed(package):
            self.log.error("%s package is not installed", package)
            status = False

        return PackageCheck(self.check_kexec_package.__doc__,
                            package, status)

    def check_active_dump(self):
        """Active dump"""

        status = not os.path.isfile(self.active_dump)
        return FileCheck(self.check_active_dump.__doc__,
                         self.active_dump, status)


class Kdump(Dump):
    """Kdump configuration check"""

    def __init__(self):
        Dump.__init__(self)
        self.name = Kdump.__name__
        self.description = Kdump.__doc__
        self.dump_service_name = "kdump"
        self.dump_comp_name = "kdump"
        self.kdump_etc_conf = "/etc/kdump.conf"
        self.kdump_conf_file = "/etc/sysconfig/kdump"
        self.log = get_default_logger()
        self.capture_kernel_mem = [(2048, 128),
                                   (4096, 320),
                                   (32768, 512),
                                   (65536, 1024),
                                   (131072, 2048),
                                   (1048576, 8192),
                                   (8388608, 16384),
                                   (16777216, 32768),
                                   (sys.maxsize, 65536)]

    @classmethod
    def is_applicable(cls):
        """Returns true if boot cmdline doesn't contain fadump=on"""

        if is_string_in_file("fadump=on", "/proc/cmdline"):
            return False

        return True

    def get_required_mem_for_capture_kernel(self):
        """Detects the system configuration and returns the amount of memory
        required for capture kernel in MB"""

        ram = get_total_ram()

        if ram is None:
            return None

        # Change from KB to MB
        ram = ram / 1024

        for (total_mem, need_reservation_mem) in self.capture_kernel_mem:
            if ram <= total_mem:
                return need_reservation_mem

    def is_capture_kernel_memory_sufficient(self, allocated_mem):
        """Returns true if allocated memory for capture kernel is sufficient"""

        required_mem = None

        need_reservation_mem = self.get_required_mem_for_capture_kernel()

        if need_reservation_mem is None:
            self.log.error("Failed to detect memory configuration")
            return False

        if allocated_mem < need_reservation_mem:
            required_mem = need_reservation_mem

        if required_mem:
            self.log.error("Memory reserved for kdump kernel is insufficient")
            self.log.recommendation("Please increase the memory to %d MB",
                                    required_mem)
            return False

        return True

    def check_capture_kernel_memory_allocation(self):
        """Memory allocated for capture kernel"""

        status = None
        allocated_mem_size = None
        kexec_crash_size = "/sys/kernel/kexec_crash_size"

        mem_alloc_capture_kernel = get_file_content(kexec_crash_size)
        self.log.debug("kexec crash size %s: %s",
                       kexec_crash_size, mem_alloc_capture_kernel)

        if mem_alloc_capture_kernel is None:
            self.log.error("Memory allocation to capture kernel failed")
            status = False
        else:
            try:
                allocated_mem_size = int(mem_alloc_capture_kernel) / 1024 / 1024
                status = self.is_capture_kernel_memory_sufficient(allocated_mem_size)
            except ValueError as value_error:
                self.log.error("Invalid crash size found %s, error: %s",
                               kexec_crash_size, value_error)
                status = False

        kdump_mem = SysfsCheck(self.check_capture_kernel_memory_allocation.__doc__,
                               kexec_crash_size, status)
        kdump_mem.set_sysfs_value_found(allocated_mem_size)
        kdump_mem.set_sysfs_expected_value(self.get_required_mem_for_capture_kernel())

        return kdump_mem

    def check_is_kexec_crash_loaded(self):
        """Capture kernel load status"""

        status = True
        kexec_crash_loaded = "/sys/kernel/kexec_crash_loaded"

        try:
            kexec_crash_status = int(get_file_content(kexec_crash_loaded))
            if kexec_crash_status is None or kexec_crash_status != 1:
                self.log.error("Capture kernel is unavailable")
                status = False
        except ValueError as value_error:
            self.log.error("Invalid data found in file %s, error: %s",
                           kexec_crash_loaded, value_error)
            status = False

        kexec_crash_loaded = SysfsCheck(self.check_is_kexec_crash_loaded.__doc__,
                                        kexec_crash_loaded, status)
        kexec_crash_loaded.set_sysfs_value_found(int(kexec_crash_status))
        kexec_crash_loaded.set_sysfs_expected_value(1)

        return kexec_crash_loaded

    def check_kdump_sysconfig(self):
        """Kdump attributes in /etc/sysconfig/kdump"""

        sysconfig_check = ConfigurationFileCheck(self.check_kdump_sysconfig.__doc__,
                                                 self.kdump_conf_file)

        def evaluate_kdump_savedir_attr(val):
            """Raise a flag if the dump location is remote or not found."""

            remote_server_types = ['ftp', 'sftp', 'ssh', 'nfs', 'cifs']

            for remote_server_type in remote_server_types:
                if val.startswith(remote_server_type+'://'):
                    self.log.warning("Dump target location is remote\n"
                                     "\t\t\tPlease ensure that the remote machine is accessible\n"
                                     "\t\t\tand has sufficent storage to store the dump")
                    return True

            if val.startswith('file://'):
                val = val.replace('file://', '')

            return os.path.isdir(val)

        kdump_attr = \
            {"kdumptool_flags": lambda val: val in ["NOSPARSE",
                                                    "SPLIT",
                                                    "SINGLE",
                                                    "XENALLDOMAINS",
                                                    ""],
             "kdump_dumpformat": lambda val: val in ["ELF",
                                                     "compressed",
                                                     "lzo",
                                                     "sanppy",
                                                     ""],
             "kdump_copy_kernel": lambda val: val in ["yes", "no"],
             "kdump_immediate_reboot": lambda val: val in ["yes", "no"],
             "kdump_verbose": lambda val: int(val) > -1 and int(val) < 32,
             "kdump_continue_on_error": lambda val: val in ["true", "false"],
             "kdump_fadump": lambda val: val == "no",
             "kdump_fadump_shell": lambda val: val == "no",
             "kdump_dumplevel": lambda val: int(val) > -1 and int(val) < 32,
             "kdump_savedir": evaluate_kdump_savedir_attr,
             "use_kdump": lambda val: int(val) == 1,
             "kdump_initrd": lambda val: os.path.isfile(val),
             "kdump_coredir": lambda val: os.path.isdir(val),
             "kdump_kernel": lambda val: os.path.isfile(val)}

        status = True
        try:
            with open(self.kdump_conf_file) as file_o:
                for line in file_o:
                    if not (line.startswith('#') or line.startswith('\n')):
                        (key, value) = line[:-1].split('=', 1)

                        # The key-value pair is stored in two formats
                        # 1: key="value"
                        # 2: key=value
                        if value.startswith('"') != value.endswith('"'):
                            status = False
                            self.log.error("Kdump attribute %s is not formatted properly in %s",
                                           key, self.kdump_conf_file)
                            self.log.recommendation("Fix the %s attribute and "
                                                    "restart the kdump service",
                                                    key)
                            continue

                        if value.startswith('"'):
                            argument = value[1:-1]
                        else:
                            argument = value

                        if key.lower() in kdump_attr.keys():
                            is_attribute_conf_correct = True
                            if not kdump_attr[key.lower()](argument):
                                is_attribute_conf_correct = False
                                if status and not is_attribute_conf_correct:
                                    status = False
                                self.log.error("Kdump attribute %s is not configured correctly",
                                               key)
                            sysconfig_check.add_attribute(key,
                                                          is_attribute_conf_correct,
                                                          argument, None)
        except Exception as exception:
            self.log.debug("Failed to access kdump config file %s, error: %s",
                           self.kdump_conf_file, exception)
            status = False

        sysconfig_check.set_status(status)

        return sysconfig_check

    def check_kdump_etc_config(self):
        """Kdump attributes in /etc/kdump.conf"""


        etc_config_check = ConfigurationFileCheck(self.check_kdump_etc_config.__doc__,
                                                  self.kdump_etc_conf)

        def log_remote_dump_warning(val):
            self.log.warning("The dump target location is remote %s\n"
                             "\t\t\tPlease ensure that the remote machine is accessible\n"
                             "\t\t\tand has sufficient storage to store the dump",
                             val)

        def evaluate_ssh_attr(val):
            log_remote_dump_warning(val)
            return True

        def evaluate_nfs_attr(val):
            log_remote_dump_warning(val)
            return True

        kdump_attr = {"path": lambda val: os.path.isdir(val),
                      "ssh": evaluate_ssh_attr,
                      "nfs": evaluate_nfs_attr}

        status = True
        try:
            with open(self.kdump_etc_conf) as file_o:
                for line in file_o:
                    if not (line.startswith('#') or line.startswith('\n')):
                        (key, value) = line.split(' ', 1)
                        argument = value[:-1]
                        if key.lower() in kdump_attr.keys():
                            is_attribute_conf_correct = True
                            if not kdump_attr[key.lower()](argument):
                                is_attribute_conf_correct = False
                                if status and not is_attribute_conf_correct:
                                    status = False
                                self.log.error("Kdump attribute %s is not configured correctly",
                                               key)
                            etc_config_check.add_attribute(key,
                                                           is_attribute_conf_correct,
                                                           argument, None)

        except Exception as exception:
            self.log.error("Failed to access kdump config file %s, error: %s",
                           self.kdump_etc_conf, exception)
            status = False

        etc_config_check.set_status(status)

        return etc_config_check


def get_crashkernel_recomm():
    """Extract crashkernel value from kdump-lib.sh script"""

    kdump_lib_path = ". /lib/kdump/kdump-lib.sh; kdump_get_arch_recommend_size"
    crash_value_cmd = ['bash', '-c', kdump_lib_path]
    crash_ker_val = -1

    # check if we can get crashkernel recommandation from kdump-lib.sh
    try:
        proc = subprocess.Popen(crash_value_cmd, stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        crash_value = proc.stdout.read().decode('ascii')[:-1]
        # expecting crashkernel value in xx[M|MB|G|GB|T|TB] format
        if len(crash_value) > 1:
            unit = ""
            crash_value_tmp = ""
            for ele in crash_value:
                if ele.isdigit():
                    crash_value_tmp = crash_value_tmp+ele
                else:
                    unit = ele
                    break
            crash_value = int(crash_value_tmp)
            if unit in 'G' or unit in 'g':
                crash_value = crash_value * 1024
            elif unit in 'T' or unit in 't':
                crash_value = crash_value * 1024 * 1024

            crash_ker_val = crash_value

    except Exception as e:
        crash_ker_val = -1

    return crash_ker_val

class KdumpFedora(Kdump, Plugin, FedoraScheme):
    """Validates the Kdump configuration on Fedora"""

    def __init__(self):
        Plugin.__init__(self)
        Kdump.__init__(self)
        self.initial_ramdisk = "/boot/initramfs-" \
                               + self.kernel_release \
                               + "kdump.img"

    def get_required_mem_for_capture_kernel(self):
        """detects the system configuration and returns the amount of memory
        required for capture kernel in MB"""

        crash_ker_val = get_crashkernel_recomm()
        if crash_ker_val != -1:
            return crash_ker_val

        ram = get_total_ram()

        if ram is None:
            return None

        # change from kb to mb
        ram = ram / 1024

        for (total_mem, need_reservation_mem) in self.capture_kernel_mem:
            if ram <= total_mem:
                return need_reservation_mem


class KdumpRHEL(Kdump, Plugin, RHELScheme):
    """Validates the Kdump configuration on RHEL"""

    def __init__(self):
        Plugin.__init__(self)
        Kdump.__init__(self)
        self.initial_ramdisk = "/boot/initramfs-" \
                               + self.kernel_release \
                               + "kdump.img"
        self.capture_kernel_mem = [(4096, 384),
                                   (16384, 512),
                                   (65536, 1024),
                                   (131072, 2048),
                                   (sys.maxsize, 4096)]

    def get_required_mem_for_capture_kernel(self):
        """detects the system configuration and returns the amount of memory
        required for capture kernel in MB"""

        crash_ker_val = get_crashkernel_recomm()
        if crash_ker_val != -1:
            return crash_ker_val

        ram = get_total_ram()

        if ram is None:
            return None

        # change from kb to mb
        ram = ram / 1024

        for (total_mem, need_reservation_mem) in self.capture_kernel_mem:
            if ram <= total_mem:
                return need_reservation_mem


class KdumpSuSE(Kdump, Plugin, SuSEScheme):
    """Validates the Kdump configuration on SuSE"""

    def __init__(self):
        Plugin.__init__(self)
        Kdump.__init__(self)
        self.initial_ramdisk = "/boot/initrd-" \
                               + self.kernel_release \
                               + "-kdump"
        self.capture_kernel_mem = [(32768, 512),
                                   (65536, 1024),
                                   (131072, 2048),
                                   (1048576, 4096),
                                   (2097152, 6144),
                                   (4194304, 12288),
                                   (8388608, 20480),
                                   (16777216, 32768),
                                   (sys.maxsize, 65536)]


    def check_kdump_package(self):
        """kdump package"""

        status = True
        package = "kdump"

        if not is_package_installed(package):
            self.log.error("%s package is not installed", package)
            status = False

        return PackageCheck(self.check_kdump_package.__doc__,
                            package, status)

    def check_kdump_etc_config(self):
        """Kdump attributes in /etc/kdump.conf"""

        # Do not have /etc/kdump.cfg file
        return ConfigurationFileCheck(None, None)


class KdumpUbuntu(Kdump, Plugin, UbuntuScheme):
    """Validates the Kdump configuration on Ubuntu"""

    def __init__(self):
        Plugin.__init__(self)
        Kdump.__init__(self)
        self.dump_service_name = "kdump-tools"
        self.initial_ramdisk = "/var/lib/kdump/initrd.img-" \
                               + self.kernel_release
        self.kdump_conf_file = "/etc/default/kdump-tools"

    def check_dump_component_in_initrd(self):
        """Dump component in initial ramdisk"""

        # Do not have dump component in init ramdisk
        return Check(None)

    def check_kdump_etc_config(self):
        """Kdump attributes in /etc/kdump.conf"""

        # Do not have /etc/kdump.cfg file
        return ConfigurationFileCheck(None, None)
