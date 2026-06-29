# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2025
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to check spyre configuration"""

import os
import grp
import re
import stat
import pyudev

from servicereportpkg.utils import execute_command
from servicereportpkg.check import Check, ConfigCheck
from servicereportpkg.check import PackageCheck
from servicereportpkg.validate.schemes import Scheme
from servicereportpkg.validate.plugins import Plugin
from servicereportpkg.check import FilesCheck
from servicereportpkg.utils import is_package_installed
from servicereportpkg.check import ConfigurationFileCheck
from servicereportpkg.utils import is_read_write_to_owner_group_users


class Spyre(Plugin, Scheme):
    """Spyre configuration checks"""

    def __init__(self):
        Plugin.__init__(self)
        self.name = Spyre.__name__
        self.description = Spyre.__doc__

    """
    get_number_of_spyre_cards(): Get the number of spyre cards available in
    the system.

    Args:
        None

    Returns:
        int: Number of spyre cards in the system.
    """
    @classmethod
    def get_number_of_spyre_cards(cls):
        """Returns number of spyre cards in the system"""

        number_of_cards = 0
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

            number_of_cards += 1

        return number_of_cards

    @classmethod
    def is_applicable(cls):
        """Returns True if plugin is applicable otherwise False"""

        return Spyre.get_number_of_spyre_cards() > 0

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

        vfio_udev = "SUBSYSTEM==\"vfio\", GROUP:=\"sentient\", MODE:=\"0660\""
        config_file = "/etc/udev/rules.d/95-vfio-3.rules"

        conf_check = ConfigurationFileCheck(self.check_udev_rule.__doc__,
                                            config_file)

        status = False
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line and line.startswith("#"):
                        continue
                    if line == vfio_udev:
                        status = True
                        break
                    # If incorrect vfio rules exists in file which
                    # will persist and overwrites the correct config
                    # which present later validation fails.
                    elif ('SUBSYSTEM=="vfio"' in line and
                        ("GROUP:=" in line or "MODE:=" in line)):
                        status = False
                        break
        except FileNotFoundError:
            self.log.error("File not found : %s", config_file)

        conf_check.add_attribute(vfio_udev, status, None, None)
        conf_check.set_status(status)
        return conf_check

    """
    is_mem_limit_config_valid(): Verify whether the current memlock
    configuration satisfies or exceeds the expected VFIO memory configuration.

    Args:
        config_file (str): File path to existing configuration
        conf (str): Expected memlimit configuration

    Returns:
        bool: True if current memlimit config is valid, False otherwise.
    """
    def is_mem_limit_config_valid(self, config_file, conf):

        # Example strings matching the pattern:
        # "@sentient 1234", "@sentient unlimited", "@sentient 7890",
        # "@sentient -memlock unlimited"
        pattern = r'^(@sentient.+)\s+(unlimited|\d+)$'
        status = False
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    if line == conf:
                        status = True
                        continue

                    line_match = re.match(pattern, line)
                    conf_match = re.match(pattern, conf)
                    if line_match and conf_match:
                        line_str = line_match.group(1)
                        line_value = line_match.group(2)
                        conf_str = conf_match.group(1)
                        conf_value = conf_match.group(2)
                        if line_str == conf_str:
                            if (line_value == "unlimited"
                                    or (int(line_value) >= int(conf_value))):
                                status = True
                            else:
                                status = False

        except FileNotFoundError:
            self.log.error("File not found : %s", config_file)
            status = False

        except ValueError as e:
            self.log.error("Type casting error: %s", e)
            status = False

        return status

    def check_memlock_conf(self):
        """User memlock configuration"""

        num_cards = Spyre.get_number_of_spyre_cards()
        memlimit = num_cards * 134234112
        vfio_mem_conf = [f"@sentient - memlock {memlimit}"]
        config_file = "/etc/security/limits.d/memlock.conf"

        conf_check = ConfigurationFileCheck(self.check_memlock_conf.__doc__,
                                            config_file)

        status = True
        for conf in vfio_mem_conf[:]:
            if self.is_mem_limit_config_valid(config_file, conf):
                conf_check.add_attribute(conf, True, None, None)
                vfio_mem_conf.remove(conf)

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
            perm_check.set_status(False)
            return perm_check

        group_name = 'sentient'
        try:
            gid = grp.getgrnam(group_name).gr_gid
        except Exception as e:
            self.log.error("Failed to get groupid of group: %s", group_name)
            perm_check.set_status(False)
            return perm_check

        for name in os.listdir(vfio_dir):
            full_path = vfio_dir + name
            try:
                ret = True
                mode = os.stat(full_path).st_mode
                # /dev/vfio/vfio file permissions doesn't need to be
                # validated as its permissons doesnt affect
                # the vfio spyre card permissions
                if stat.S_ISCHR(mode) and name != 'vfio':
                    if os.stat(full_path).st_gid != gid:
                        ret = False
                    ret = ret & is_read_write_to_owner_group_users(full_path)
                    if not ret and status:
                        status = ret
                    perm_check.add_file(full_path, ret)
            except FileNotFoundError:
                self.log.error("Failed to access %s", full_path)

        perm_check.set_status(status)
        return perm_check

    def check_sos_package(self):
        """sos package"""

        status = True
        package = "sos"

        if not is_package_installed(package):
            self.log.error("%s package is not installed", package)
            status = False

        return PackageCheck(self.check_sos_package.__doc__,
                            package, status)

    def check_sos_config(self):
        "sos config"

        status = True
        sos_config_file = "/etc/sos/sos.conf"
        sos_config = {"podman.logs": False,
                      "podman.all": False,
                       }

        sos_config_check = ConfigurationFileCheck(self.check_sos_config.__doc__,
                                            sos_config_file)

        # Patterns to match podman.logs = true and podman.all = true
        pattern_logs = re.compile(r'^\s*podman\.logs\s*=\s*true\s*$', re.IGNORECASE)
        pattern_all = re.compile(r'^\s*podman\.all\s*=\s*true\s*$', re.IGNORECASE)

        try:
            with open(sos_config_file, 'r', encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Detect section headers
                    if line.startswith('[') and line.endswith(']'):
                        section = line[1:-1].strip()
                        if section == "plugin_options":
                            in_plugin_options = True
                        else:
                            in_plugin_options = False
                        continue

                    if in_plugin_options:
                        if pattern_logs.match(line):
                            sos_config["podman.logs"] = True
                        elif pattern_all.match(line):
                            sos_config["podman.all"] = True

            for key, value in sos_config.items():
                if not value:
                    status = False
                sos_config_check.add_attribute(key, value, None, None)

        except (FileNotFoundError, PermissionError) as e:
            status = False
            self.log.error("Error reading file %s: %s", sos_config_file,
                           str(e))

        sos_config_check.set_status(status)
        return sos_config_check

    def check_max_spyre_cards_supported(self):
        """Maximum Spyre cards supported in system"""

        max_supported_cards = 24
        num_cards = Spyre.get_number_of_spyre_cards()
        card_check = Check(self.check_max_spyre_cards_supported.__doc__)
        status = num_cards <= max_supported_cards

        if not status:
            message = (
                f"\nBad configuration detected.\n"
                f"Number of Spyre cards found: {num_cards}\n"
                f"Maximum Spyre cards supported in system: {max_supported_cards}\n"
                f"Please reduce the number of Spyre cards to {max_supported_cards} or fewer.\n"
            )
            card_check.set_message(message)

        card_check.set_status(status)
        return card_check
