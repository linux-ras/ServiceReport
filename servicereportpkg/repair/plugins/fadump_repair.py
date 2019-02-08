# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the FADump checks"""


import os
import shutil

from servicereportpkg.check import Notes
from servicereportpkg.utils import restart_service
from servicereportpkg.utils import execute_command
from servicereportpkg.file_manager import backup_file
from servicereportpkg.repair.plugins import RepairPlugin
from servicereportpkg.utils import start_service
from servicereportpkg.utils import update_grub, install_package
from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import is_daemon_enabled, enable_daemon
from servicereportpkg.repair.plugins.kdump_repair import update_crashkernel


class FadumpRepair(RepairPlugin):
    """Fix FADump configuration checks"""

    def __init__(self):
        RepairPlugin.__init__(self)
        self.name = "FADump"
        self.log = get_default_logger()

    def fix_kexec_package(self, plugin_obj, check):
        """Instal kexec package"""

        install_package(check.get_package_name())
        re_check = plugin_obj.check_kexec_package()

        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_kdump_package(self, plugin_obj, check):
        """Install kdump package"""

        install_package(check.get_package_name())
        re_check = plugin_obj.check_kdump_package()

        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_mem_reservation(self, check):
        """Update memory reservation for capture kernel"""

        required_mem = check.get_sysfs_expected_value()
        if update_crashkernel(required_mem) and update_grub():
            self.log.info("Successfully updated the crashkernel value")
            check.set_note(Notes.FIXED_NEED_REBOOT)
        else:
            self.log.error("Failed to update the crashkernel value")
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_fadump_enable(self, check):
        """Add Not Fixable note to fadump enable check"""

        check.set_note(Notes.NOT_FIXABLE)

    def replace_sysconfig_kdump(self, sysconfig_file_path,
                                sysconfig_temp_file_path,
                                backup_sysconfig_file_path):
        """Replace temp sysconfig kdump file with original"""

        try:
            os.rename(sysconfig_temp_file_path, sysconfig_file_path)
            return True
        except Exception:
            self.log.debug("Failed to replace %s with %s", sysconfig_file_path,
                           sysconfig_temp_file_path)
            try:
                self.log.debug("Restoring the sysconfig kdump file.")
                shutil.copy2(backup_sysconfig_file_path, sysconfig_file_path)
            except Exception:
                self.log.error("Failed to restore grub file.")
            return False

    def fix_sysconfig_check(self, check):
        """Assign yes to KDUMP_FADUMP attribute"""

        sysconfig_file_path = check.get_file_path()
        backup_sysconfig_file_path = backup_file(sysconfig_file_path)
        sysconfig_temp_file_path = sysconfig_file_path+".tmp"

        if backup_sysconfig_file_path is None:
            self.log.error("Failed to take backup of %s", sysconfig_file_path)
            return False

        self.log.info("Updating %s, backup file present at %s",
                      sysconfig_file_path, backup_sysconfig_file_path)

        if os.path.exists(sysconfig_temp_file_path):
            try:
                os.remove(sysconfig_temp_file_path)
            except Exception:
                self.log.debug("Unable to delete %s file", sysconfig_temp_file_path)
                return False

        try:
            with open(sysconfig_file_path) as sysconfig_file, \
                    open(sysconfig_temp_file_path, "w+") as sysconfig_temp_file:

                for line in sysconfig_file.readlines():
                    if line.startswith("KDUMP_FADUMP="):
                        line = 'KDUMP_FADUMP="yes"\n'

                    sysconfig_temp_file.write(line)
        except Exception:
            self.log.debug("Unable to access files %s, %s",
                           sysconfig_file_path, sysconfig_temp_file_path)
            return False

        if self.replace_sysconfig_kdump(sysconfig_file_path,
                                        sysconfig_temp_file_path,
                                        backup_sysconfig_file_path):
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_dump_comp_initrd(self, plugin_obj, check):
        """Restart the dump service"""

        command = ["touch", "/etc/sysconfig/kdump"]
        execute_command(command)
        restart_service(check.get_service())
        re_check = plugin_obj.check_dump_component_in_initrd()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_fadump_registration_check(self, plugin_obj, check):
        """Set 1 to fadump_registered sysfs file"""

        os.system("echo 1 > /sys/kernel/fadump_registered")
        re_check = plugin_obj.check_fadump_registered()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_service_status(self, check):
        """Restarts the dump service"""

        if start_service(check.get_service()):
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

        # Enable the service to start on boot
        if not is_daemon_enabled(check.get_service()):
            if enable_daemon(check.get_service()):
                self.log.info("%s service is enabled to start on boot",
                              check.get_service())
            else:
                self.log.warning("%s service is not configured to start on boot",
                                 check.get_service())

    def repair(self, plugin_obj, checks):
        """Repair the failed checks in FADump plugin"""

        check_dir = {}
        for check in checks:
            check_dir[check.get_name()] = check

        kexec_package_check = check_dir["kexec package"]
        if kexec_package_check.get_status() is False:
            self.fix_kexec_package(plugin_obj, kexec_package_check)
        elif kexec_package_check.get_status() is None:
            kexec_package_check.set_note(Notes.FAIL_TO_FIX)

        if "kdump package" in check_dir.keys():
            kdump_package_check = check_dir["kdump package"]
            if kdump_package_check.get_status() is False:
                self.fix_kdump_package(plugin_obj, kdump_package_check)
            elif kdump_package_check.get_status() is None:
                kdump_package_check.set_note(Notes.FAIL_TO_FIX)

        mem_reservation_check = check_dir["Memory reservation"]
        if mem_reservation_check.get_status() is False:
            self.fix_mem_reservation(mem_reservation_check)
        elif mem_reservation_check.get_status() is None:
            mem_reservation_check.set_note(Notes.FAIL_TO_FIX)

        fadump_enabled_check = check_dir["FADump enabled check"]
        if fadump_enabled_check.get_status() is False:
            self.fix_fadump_enable(fadump_enabled_check)
        elif fadump_enabled_check.get_status() is None:
            fadump_enabled_check.set_note(Notes.NOT_FIXABLE)

        if "Fadump attributes in /etc/sysconfig/kdump" in check_dir.keys():
            fadump_sysconfig_check = check_dir["Fadump attributes in /etc/sysconfig/kdump"]
            if fadump_sysconfig_check.get_status() is False:
                self.fix_sysconfig_check(fadump_sysconfig_check)
            elif fadump_sysconfig_check.get_status() is None:
                fadump_sysconfig_check.set_note(Notes.FAIL_TO_FIX)

        dump_comp_initrd_check = check_dir["Dump component in initial ramdisk"]
        if dump_comp_initrd_check.get_status() is False:
            self.fix_dump_comp_initrd(plugin_obj, dump_comp_initrd_check)
        elif dump_comp_initrd_check.get_status() is None:
            dump_comp_initrd_check.set_note(Notes.FAIL_TO_FIX)

        fadump_registration_check = check_dir["FADump registration check"]
        if fadump_registration_check.get_status() is False:
            self.fix_fadump_registration_check(plugin_obj, fadump_registration_check)
        elif fadump_registration_check.get_status() is None:
            fadump_registration_check.set_note(Notes.FAIL_TO_FIX)

        service_status_check = check_dir["Service status"]
        if service_status_check.get_status() is False:
            self.fix_service_status(service_status_check)
        elif service_status_check.get_status() is None:
            service_status_check.set_note(Notes.FAIL_TO_FIX)
