# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2025
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the spyre card configuration checks"""


import os
import stat
import re
import shutil

from servicereportpkg.check import Notes
from servicereportpkg.utils import append_to_file
from servicereportpkg.utils import execute_command
from servicereportpkg.utils import install_package
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

    def fix_sos_package(self, plugin_obj, sos_package_check):
        """install sos package"""

        install_package(sos_package_check.get_package_name())
        re_check = plugin_obj.check_sos_package()
        if re_check.get_status():
            sos_package_check.set_status(True)
            sos_package_check.set_note(Notes.FIXED)
        else:
            sos_package_check.set_note(Notes.FAIL_TO_FIX)

    def fix_sos_config(self, plugin_obj, sos_config_check):
        """Update sos config"""

        sos_config_file = sos_config_check.get_file_path()
        try:
            with open(sos_config_file, 'r', encoding="utf-8") as f:
                lines = f.readlines()

        except (FileNotFoundError, PermissionError) as e:
            self.log.error("Error reading file %s: %s", sos_config_file, str(e))
            sos_config_check.set_note(Notes.FAIL_TO_FIX)
            return

            # Normalize for detection (but preserve original lines for writing)
        pattern_logs = re.compile(r'^\s*podman\.logs\s*=\s*true\s*$', re.IGNORECASE)
        pattern_all = re.compile(r'^\s*podman\.all\s*=\s*true\s*$', re.IGNORECASE)
        section_pattern = re.compile(r'^\s*\[\s*plugin_options\s*\]\s*$')

        in_plugin_options = False
        found_plugin_section = False
        podman_logs_present = False
        podman_all_present = False
        updated_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect start of [plugin_options] section
            if section_pattern.match(stripped):
                in_plugin_options = True
                found_plugin_section = True
                updated_lines.append(line)
                continue

            # Detect other sections, stop plugin_options scope
            if in_plugin_options and re.match(r'^\s*\[.*\]\s*$', stripped):
                in_plugin_options = False

            # Inside [plugin_options] section
            if in_plugin_options:
                if pattern_logs.match(stripped):
                    podman_logs_present = True
                if pattern_all.match(stripped):
                    podman_all_present = True

            updated_lines.append(line)

        # Append missing section and/or options
        if not found_plugin_section:
            updated_lines.append('\n[plugin_options]\n')
            updated_lines.append('podman.logs = true\n')
            updated_lines.append('podman.all = true\n')
        else:
            # Add missing entries at the end of [plugin_options]
            insert_index = None
            for i in range(len(updated_lines)):
                if section_pattern.match(updated_lines[i].strip()):
                    insert_index = i + 1
                    break

            # Move to the point just before the next section or EOF
            while insert_index < len(updated_lines):
                if re.match(r'^\s*\[.*\]\s*$', updated_lines[insert_index].strip()):
                    break
                insert_index += 1

            if not podman_logs_present:
                updated_lines.insert(insert_index, 'podman.logs = true\n')
                insert_index += 1
            if not podman_all_present:
                updated_lines.insert(insert_index, 'podman.all = true\n')

        # Backup original file
        try:
            shutil.copy(sos_config_file, sos_config_file + ".bak")
        except Exception as e:
            self.log.error("Error backing up %s: %s", sos_config_file, str(e))
            sos_config_check.set_note(Notes.FAIL_TO_FIX)
            return

        # Write the updated config
        try:
            with open(sos_config_file, 'w', encoding="utf-8") as f:
                f.writelines(updated_lines)

        except (PermissionError, OSError) as e:
            self.log.error("Error writing to file %s : %s",
                           sos_config_file, str(e))
            return

        re_check = plugin_obj.check_sos_config()
        if re_check.get_status():
            sos_config_check.set_status(True)
            sos_config_check.set_note(Notes.FIXED)
        else:
            sos_config_check.set_note(Notes.FAIL_TO_FIX)

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

        sos_package_check = check_dir["sos package"]
        if sos_package_check.get_status() is False:
            self.fix_sos_package(plugin_obj, sos_package_check)
        elif sos_package_check.get_status is None:
            sos_package_check.set_note(Notes.NOT_FIXABLE)

        sos_config_check = check_dir["sos config"]
        # if sos package is not intalled, not much can be done
        if not sos_package_check.get_status():
            sos_config_check.set_note(Notes.NOT_FIXABLE)
        elif sos_config_check.get_status() is False:
            self.fix_sos_config(plugin_obj, sos_config_check)
        elif sos_config_check.get_status is None:
            sos_config_check.set_note(Notes.NOT_FIXABLE)
