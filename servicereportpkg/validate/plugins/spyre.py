# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2025
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check spyre configuration"""

import os
import re
import stat
import pyudev

from servicereportpkg.utils import execute_command
from servicereportpkg.check import Check, ConfigCheck
from servicereportpkg.validate.schemes import Scheme
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.check import FilesCheck
from servicereportpkg.check import ConfigurationFileCheck
from servicereportpkg.utils import is_read_write_to_all_users


class Spyre(Plugin, Scheme):
    """Spyre configuration checks"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = Spyre.__name__
        self.description = Spyre.__doc__

    @classmethod
    def is_spyre_card_exists(cls):
        """Return True if spyre exists in the system otherwise False"""

        context = pyudev.Context()
        # IBM vendor ID
        spyre_vendor_ids = ["0x1014"]
        # Spyre device IDs
        spyre_device_ids = ["0x06a7", "0x06a8"]

        for device in context.list_devices(subsystem='pci'):
            vendor_id = device.attributes.get("vendor").decode("utf-8").strip()
            if vendor_id not in spyre_vendor_ids:
                continue

            device_id = device.attributes.get("device").decode("utf-8").strip()
            if device_id not in spyre_device_ids:
                continue

            return True

        return False

    @classmethod
    def is_valid(cls):
        """Returns True if plugin is applicable otherwise False"""

        return Spyre.is_spyre_card_exists()

    def check_driver_config(self):
        """VFIO Driver configuration"""

        vfio_config_file = "/etc/modprobe.d/vfio-pci.conf"

        vfio_config = {("vfio-pci", "ids"): "1014:06a7,1014:06a8",
                       ("vfio-pci", "disable_idle_d3"): "yes",
                       }
        conf_check = ConfigurationFileCheck(self.check_driver_config.__doc__,
                                            vfio_config_file)

        status = True
        try:
            with open(vfio_config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    match = re.match(r"^options\s+(\S+)\s+(.+)$", line)
                    if not match:
                        continue

                    mod = match.group(1)
                    configs = match.group(2).strip()
                    matches = re.findall(r'(\w+)=([^=\s]+)', configs)
                    for key, value in matches:
                        if (mod, key) not in vfio_config:
                            continue

                        if vfio_config[(mod, key)] == value:
                            conf_check.add_attribute((mod, key),
                                                     True, value, None)
                            vfio_config.pop((mod, key))
        except FileNotFoundError:
            self.log.error("File not found : %s", vfio_config_file)

        for config in vfio_config.items():
            conf_check.add_attribute(config[0], False, None, config[1])

        if vfio_config:
            status = False

        conf_check.set_status(status)

        return conf_check

    def check_udev_rule(self):
        """VFIO udev rules configuration"""

        vfio_udev = "SUBSYSTEM==\"vfio\", MODE=\"0666\""
        config_file = "/etc/udev/rules.d/95-vfio-3.rules"

        conf_check = ConfigurationFileCheck(self.check_udev_rule.__doc__,
                                            config_file)

        status = False
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line == vfio_udev:
                        status = True
                        break
        except FileNotFoundError:
            self.log.error("File not found : %s", config_file)

        conf_check.add_attribute(vfio_udev, status, None, None)
        conf_check.set_status(status)
        return conf_check

    def check_memblock_conf(self):
        """User memblock configuration"""

        vfio_mem_conf = ["@sentient - memlock 134217728"]
        config_file = "/etc/security/limits.d/memlock.conf"

        conf_check = ConfigurationFileCheck(self.check_memblock_conf.__doc__,
                                            config_file)

        status = True
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line in vfio_mem_conf:
                        conf_check.add_attribute(line, True, None, None)
                        vfio_mem_conf.remove(line)

        except FileNotFoundError:
            self.log.error("File not found : %s", config_file)
            status = False

        if vfio_mem_conf:
            status = False
            for conf in vfio_mem_conf:
                conf_check.add_attribute(conf, False, None, None)

        conf_check.set_status(status)

        return conf_check

    def check_vfio_pci_conf(self):
        """VFIO module dep configuration"""

        vfio_mod_conf = ["vfio-pci",
                         "vfio_iommu_spapr_tce"]
        config_file = "/etc/modules-load.d/vfio-pci.conf"

        conf_check = ConfigurationFileCheck(self.check_vfio_pci_conf.__doc__,
                                            config_file)

        status = True
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line in vfio_mod_conf:
                        conf_check.add_attribute(line, True, None, None)
                        vfio_mod_conf.remove(line)
        except FileNotFoundError:
            self.log.error("File not found : %s", config_file)
            status = False

        if vfio_mod_conf:
            for conf in vfio_mod_conf:
                conf_check.add_attribute(conf, False, None, None)

        conf_check.set_status(status)

        return conf_check

    def check_user_group(self):
        """User group configuration"""

        user_groups = ["sentient"]
        user_group_check = ConfigCheck(self.check_user_group.__doc__)

        status = True
        (rc, stdout, _err) = execute_command(["getent", "group"])

        if rc is not None:
            for line in stdout.splitlines():
                line = line.strip()
                match = re.match(r'^([^:]+)', line)
                if not match:
                    continue

                user_group = match.group(1)
                if user_group in user_groups:
                    user_groups.remove(user_group)

        if user_groups:
            status = False
            for user in user_groups:
                user_group_check.add_config(user, False)

        user_group_check.set_status(status)

        return user_group_check

    def check_vfio_module(self):
        """VFIO kernel module loaded"""

        module_name = "vfio_pci"
        module_check = Check(self.check_vfio_module.__doc__)
        (rc, stdout, _err) = execute_command(["lsmod"])
        status = False

        if rc is None:
            return module_check

        for line in stdout.splitlines():
            if not line:
                continue

            if line.split()[0] == module_name:
                status = True
                break

        module_check.set_status(status)
        return module_check

    def check_vfio_access_permission(self):
        """VFIO device permission"""

        vfio_dir = "/dev/vfio/"

        perm_check = FilesCheck(self.check_vfio_access_permission.__doc__)
        status = True

        if not os.path.isdir(vfio_dir):
            self.log.error("No %s directory", vfio_dir)
            return perm_check

        for name in os.listdir(vfio_dir):
            full_path = vfio_dir + name
            try:
                mode = os.stat(full_path).st_mode
                if stat.S_ISCHR(mode):
                    ret = is_read_write_to_all_users(full_path)
                    if not ret and status:
                        status = ret
                    perm_check.add_file(full_path, ret)
            except FileNotFoundError:
                self.log.error("Failed to access %s", full_path)

        perm_check.set_status(status)
        return perm_check
