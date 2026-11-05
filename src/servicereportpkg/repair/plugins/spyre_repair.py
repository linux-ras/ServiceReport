# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2025
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the spyre card configuration checks"""


import os
import stat

from servicereportpkg.check import Notes
from servicereportpkg.utils import append_to_file
from servicereportpkg.utils import execute_command
from servicereportpkg.repair.plugins import RepairPlugin


class SpyreRepair(RepairPlugin):
    """Spyre repair plugin"""

    def __init__(self):
        RepairPlugin.__init__(self)
        self.name = "Spyre"

    def fix_vfio_drive_config(self, plugin_obj, vfio_drive_config_check):
        """Fix vifo driver config"""

        for config, val in vfio_drive_config_check.get_config_attributes().items():
            if not val["status"]:
                conf = "\noptions " + config[0] + " "
                conf = conf + config[1] + "=" + val["possible_values"]
                append_to_file(vfio_drive_config_check.get_file_path(), conf)

        re_check = plugin_obj.check_driver_config()
        if re_check.get_status():
            vfio_drive_config_check.set_status(True)
            vfio_drive_config_check.set_note(Notes.FIXED)
        else:
            vfio_drive_config_check.set_status(Notes.FAIL_TO_FIX)

    def fix_user_mem_conf(self, plugin_obj, user_mem_conf_check):
        """Fix memory configuration usergroup"""

        for config, val in user_mem_conf_check.get_config_attributes().items():
            if not val["status"]:
                append_to_file(user_mem_conf_check.get_file_path(),
                               "\n"+config)

        re_check = plugin_obj.check_memlock_conf()
        if re_check.get_status():
            user_mem_conf_check.set_status(True)
            user_mem_conf_check.set_note(Notes.FIXED)
        else:
            user_mem_conf_check.set_note(Notes.FAIL_TO_FIX)

    def fix_udev_rules_conf(self, plugin_obj, udev_rules_conf_check):
        """Fix VFIO udev rules"""

        for config, val in udev_rules_conf_check.get_config_attributes().items():
            if not val["status"]:
                append_to_file(udev_rules_conf_check.get_file_path(),
                               "\n"+config)
        re_check = plugin_obj.check_udev_rule()
        if re_check.get_status():
            udev_rules_conf_check.set_status(True)
            udev_rules_conf_check.set_note(Notes.FIXED)
        else:
            udev_rules_conf_check.set_note(Notes.FAIL_TO_FIX)

    def fix_pci_conf(self, plugin_obj, pci_conf_check):
        """Fix VFIO PCI configuration"""

        for config, val in pci_conf_check.get_config_attributes().items():
            if not val["status"]:
                append_to_file(pci_conf_check.get_file_path(),
                               "\n"+config)

        re_check = plugin_obj.check_vfio_pci_conf()
        if re_check.get_status():
            pci_conf_check.set_status(True)
            pci_conf_check.set_note(Notes.FIXED)
        else:
            pci_conf_check.set_note(Notes.FAIL_TO_FIX)

    def fix_user_group_conf(self, plugin_obj, user_group_conf_check):
        """Fix VFIO user group"""

        for config in user_group_conf_check.get_configs_list():
            if not config[1]:
                command = ["groupadd"]
                command.append(config[0])
                (_rc, _stdout, _err) = execute_command(command)

        re_check = plugin_obj.check_user_group()
        if re_check.get_status():
            user_group_conf_check.set_status(True)
            user_group_conf_check.set_note(Notes.FIXED)
        else:
            user_group_conf_check.set_note(Notes.FAIL_TO_FIX)

    def fix_vfio_kernel_mod(self, plugin_obj, vfio_kernel_mod_check):
        """Fix VFIO kernel module"""

        (_rc, _stdout, _err) = execute_command(["modprobe", "vfio_pci"])

        re_check = plugin_obj.check_vfio_module()
        if re_check.get_status():
            vfio_kernel_mod_check.set_note(Notes.FIXED)
            vfio_kernel_mod_check.set_status(True)
        else:
            vfio_kernel_mod_check.set_note(Notes.FAIL_TO_FIX)

    def fix_vfio_perm_check(self, plugin_obj, vfio_device_permission_check):
        """Fix VFIO device permission"""

        vfio_dir = "/dev/vfio/"
        for name in os.listdir(vfio_dir):
            full_path = vfio_dir + name
            try:
                mode = os.stat(full_path).st_mode
                if stat.S_ISCHR(mode):
                    os.chmod(full_path, 0o666)
            except Exception as e:
                self.log.error("Failed to %s file permission to 0o666", full_path)

        re_check = plugin_obj.check_vfio_access_permission()
        if re_check.get_status():
            vfio_device_permission_check.set_note(Notes.FIXED)
            vfio_device_permission_check.set_status(True)
        else:
            vfio_device_permission_check.set_note(Notes.FAIL_TO_FIX)

    def repair(self, plugin_obj, checks):
        """Repair spyre checks"""

        memlock_limit_message = \
            ("\nMemlock limit is set for the sentient group.\n"
            "Spyre user must be in the sentient group.\n"
            "To add run below command:\n"
            "\tsudo usermod -aG sentient <user>\n"
            "\tExample:\n"
            "\tsudo usermod -aG sentient abc\n"
            "\tRe-login as <user>.\n")

        check_dir = {}
        for check in checks:
            check_dir[check.get_name()] = check

        vfio_drive_config_check = check_dir["VFIO Driver configuration"]
        if vfio_drive_config_check.get_status() is False:
            self.fix_vfio_drive_config(plugin_obj, vfio_drive_config_check)
        elif vfio_drive_config_check.get_status() is None:
            vfio_drive_config_check.set_note(Notes.FAIL_TO_FIX)

        user_mem_conf_check = check_dir["User memlock configuration"]
        if user_mem_conf_check.get_status() is False:
            self.fix_user_mem_conf(plugin_obj, user_mem_conf_check)
        elif user_mem_conf_check.get_status() is None:
            user_mem_conf_check.set_note(Notes.FAIL_TO_FIX)

        udev_rules_conf_check = check_dir["VFIO udev rules configuration"]
        if udev_rules_conf_check.get_status() is False:
            self.fix_udev_rules_conf(plugin_obj, udev_rules_conf_check)
        elif udev_rules_conf_check.get_status() is None:
            udev_rules_conf_check.set_note(Notes.FAIL_TO_FIX)

        pci_conf_check = check_dir["VFIO module dep configuration"]
        if pci_conf_check.get_status() is False:
            self.fix_pci_conf(plugin_obj, pci_conf_check)
        elif pci_conf_check.get_status() is None:
            pci_conf_check.set_note(Notes.FAIL_TO_FIX)

        user_group_conf_check = check_dir["User group configuration"]
        if user_group_conf_check.get_status() is False:
            self.fix_user_group_conf(plugin_obj, user_group_conf_check)
        elif user_group_conf_check.get_status() is None:
            user_group_conf_check.set_note(Notes.FAIL_TO_FIX)

        if user_group_conf_check.get_status() and user_mem_conf_check.get_status():
            user_mem_conf_check.set_message(memlock_limit_message)

        vfio_kernel_mod_check = check_dir["VFIO kernel module loaded"]
        if vfio_kernel_mod_check.get_status() is False:
            self.fix_vfio_kernel_mod(plugin_obj, vfio_kernel_mod_check)
        elif vfio_kernel_mod_check.get_status() is None:
            vfio_kernel_mod_check.set_note(Notes.FAIL_TO_FIX)

        vfio_device_permission_check = check_dir["VFIO device permission"]
        if vfio_device_permission_check.get_status() is False:
            self.fix_vfio_perm_check(plugin_obj, vfio_device_permission_check)
        elif vfio_device_permission_check.get_status() is None:
            vfio_device_permission_check.set_note(Notes.NOT_FIXABLE)
