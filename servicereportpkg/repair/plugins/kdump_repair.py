# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the Kdump checks"""


import os
import shutil

from servicereportpkg.check import Notes
from servicereportpkg.utils import restart_service
from servicereportpkg.file_manager import backup_file
from servicereportpkg.repair.plugins import RepairPlugin
from servicereportpkg.utils import start_service
from servicereportpkg.utils import update_grub, install_package
from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import is_daemon_enabled, enable_daemon

def remove_crashkernel_str(_str):
    """Remove crashkernel entry from given string"""

    if not "crashkernel=" in _str:
        return _str

    _str = _str.strip()
    (param, val) = _str.split('=', 1)
    #Extract the string present inside quotes
    val = val[1:-1]

    cmdline_arg_list = val.split()
    cmdline = ""
    for arg in cmdline_arg_list:
        if not arg.startswith("crashkernel="):
            cmdline = cmdline + " " + arg

    return param+'='+'"'+cmdline.strip()+'"'+'\n'

def add_crashkernel_str(_str, crashkernel):
    """Add crashkernel entry to given string"""

    _str = _str.strip()
    (param, val) = _str.split('=', 1)
    #Extract the string present inside quotes
    val = val[1:-1]

    cmdline_arg_list = val.split()
    cmdline_arg_list.append(crashkernel)
    cmdline = ""
    for arg in cmdline_arg_list:
        cmdline = cmdline + " " + arg

    return param+'='+'"'+cmdline.strip()+'"'+'\n'


def is_grub_line_format(line):
    """Check given line format"""

    if not line or not '=' in line:
        return False

    line = line.strip()
    (param, val) = line.split('=', 1)

    if len(param) < 1 or len(val) < 2:
        return False

    startchar = val[0]
    endchar = val[len(val)-1]
    if (startchar != endchar) and (startchar == '"' or startchar == "'"):
        return False

    return True

def replace_grub(grub_file_path, grub_temp_file_path, backup_grub_file_path):
    """Replace the temporary grub file with original"""

    log = get_default_logger()
    try:
        os.rename(grub_temp_file_path, grub_file_path)
        return True
    except Exception:
        log.debug("Failed to replace %s with %s", grub_file_path, grub_temp_file_path)
        try:
            log.debug("Resotring the grub file.")
            shutil.copy2(backup_grub_file_path, grub_file_path)
        except Exception:
            log.error("Failed to restore grub file.")
            print("CRITICAL: Make sure %s file is in correct state before rebooting")

        return False

def update_crashkernel(required_mem):
    """Update the crashkernel arttribute in /etc/default/grub"""

    grub_file_path = "/etc/default/grub"
    backup_grub_file_path = backup_file(grub_file_path)
    grub_temp_file_path = grub_file_path+".tmp"
    log = get_default_logger()

    if backup_grub_file_path is None:
        log.error("Failed to take backup of %s", grub_file_path)
        return False

    log.info("Updating %s, backup file present at %s",
             grub_file_path, backup_grub_file_path)

    if os.path.exists(grub_temp_file_path):
        try:
            os.remove(grub_temp_file_path)
        except Exception:
            log.debug("Unable to delete %s file", grub_temp_file_path)
            return False

    try:
        with open(grub_file_path) as grub_file, \
                open(grub_temp_file_path, "w+") as grub_temp_file:

            grub_cmd_lx = "GRUB_CMDLINE_LINUX"
            grub_cmd_lx_def = "GRUB_CMDLINE_LINUX_DEFAULT"
            crashkernel = "crashkernel="+ str(required_mem) + "M"
            is_crashkernel_updated = False

            for line in grub_file.readlines():
                if line.startswith(grub_cmd_lx_def):
                    if is_grub_line_format(line):
                        line = remove_crashkernel_str(line)
                        line = add_crashkernel_str(line, crashkernel)
                        is_crashkernel_updated = True
                    else:
                        log.debug("Unknown grub line format: %s", line)
                        return False
                elif line.startswith(grub_cmd_lx):
                    if is_grub_line_format(line):
                        line = remove_crashkernel_str(line)
                    else:
                        log.debug("Unknown grub line format: %s", line)
                elif line.startswith("GRUB_DISABLE_RECOVERY") or \
                    line.startswith("GRUB_DISABLE_LINUX_RECOVERY"):
                    line = '#'+line
                grub_temp_file.write(line)

            if not is_crashkernel_updated:
                grub_temp_file.write(grub_cmd_lx_def+'='+'"'+crashkernel+'"'+"\n")
    except Exception:
        log.debug("Unable to access files %s, %s",
                  grub_file_path, grub_temp_file_path)
        return False

    return replace_grub(grub_file_path, grub_temp_file_path, backup_grub_file_path)


class DumpRepair(object):
    """Fix generic dump tool checks"""

    def __init__(self):
        self.log = get_default_logger()

    def fix_dump_component_in_inital_ramdisk(self, plugin_obj, service, check):
        """Rerun the dump service again to populate the dump component
        in init-ramdisk."""

        restart_service(service)
        re_check = plugin_obj.check_dump_component_in_initrd()

        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.NOT_FIXABLE)

    def fix_service_status(self, check):
        """Restarts the dump service."""

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


class KdumpRepair(DumpRepair, RepairPlugin):
    """Fix kdump configuation checks"""

    def __init__(self):
        RepairPlugin.__init__(self)
        DumpRepair.__init__(self)
        self.name = "Kdump"

    def fix_kexec_package(self, plugin_obj, check):
        """Install the kexec package"""

        install_package(check.get_package_name())
        re_check = plugin_obj.check_kexec_package()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_kdump_package(self, plugin_obj, check):
        """Install kdump package, needed only for few distro"""

        install_package(check.get_package_name())
        re_check = plugin_obj.check_kdump_package()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_memory_allocated_for_capture_kernel(self, check):
        """Update memory reservation for capture kernel"""

        required_mem = check.get_sysfs_expected_value()

        if update_crashkernel(required_mem) and update_grub():
            self.log.info("Sucessfully updated the crashkernel value")
            check.set_note(Notes.FIXED_NEED_REBOOT)
        else:
            self.log.error("Failed to update the crashkernel value")
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_capture_kernel_load_status(self, plugin_obj, check):
        """If kdump service is inactive the load status will also
        down, though the capture kernel is loaded sucessfully during
        the system boot. Currently don't know how to fix, just
        checking the load status again after kdump service restart."""

        re_check = plugin_obj.check_is_kexec_crash_loaded()
        if re_check.get_status():
            check.set_status(True)
            check.set_note(Notes.FIXED)
        else:
            check.set_note(Notes.FAIL_TO_FIX)

    def fix_kdump_sysconfig(self, plugin_obj, check):
        """Fix the /etc/sysconfig/kdump file"""

        re_check = plugin_obj.check_kdump_sysconfig()
        if re_check.get_status():
            check.set_status(True)
        else:
            self.log.debug("%s check is not auto-fixable", check.get_name())
            check.set_note(Notes.NOT_FIXABLE)

    def fix_kdump_etc_config(self, plugin_obj, check):
        """Fix the /etc/kdump.cfg, need only for few distro"""

        re_check = plugin_obj.check_kdump_etc_config()
        if re_check.get_status():
            check.set_status(True)
        else:
            self.log.debug("%s check is not auto-fixable", check.get_name())
            check.set_note(Notes.NOT_FIXABLE)

    def repair(self, plugin_obj, checks):
        """Repair the failed checks in kdump plugin"""

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

        mem_allocation_check = check_dir["Memory allocated for capture kernel"]
        if not mem_allocation_check.get_status():
            self.fix_memory_allocated_for_capture_kernel(mem_allocation_check)
        elif mem_allocation_check.get_status is None:
            mem_allocation_check.set_note(Notes.FAIL_TO_FIX)

        kdump_sysconf = check_dir["Kdump attributes in /etc/sysconfig/kdump"]
        if not kdump_sysconf.get_status():
            self.fix_kdump_sysconfig(plugin_obj, kdump_sysconf)

        if "Kdump attributes in /etc/kdump.conf" in check_dir.keys():
            kdump_etc_conf = check_dir["Kdump attributes in /etc/kdump.conf"]
            if not kdump_etc_conf.get_status():
                self.fix_kdump_etc_config(plugin_obj, kdump_etc_conf)

        service_status = check_dir["Service status"]
        if service_status.get_status() is False:
            self.fix_service_status(service_status)
        elif service_status.get_status() is None:
            service_status.set_note(Notes.FAIL_TO_FIX)

        capture_kernel_load_status = check_dir["Capture kernel load status"]
        if capture_kernel_load_status.get_status() is False:
            self.fix_capture_kernel_load_status(plugin_obj,
                                                capture_kernel_load_status)
        elif capture_kernel_load_status.get_status() is None:
            capture_kernel_load_status.set_note(Notes.FAIL_TO_FIX)

        if "Dump component in initial ramdisk" in check_dir.keys():
            init_ramdisk_comp = check_dir["Dump component in initial ramdisk"]
            if init_ramdisk_comp.get_status() is False:
                self.fix_dump_component_in_inital_ramdisk(plugin_obj,
                                                          service_status.get_service(),
                                                          init_ramdisk_comp)
            elif init_ramdisk_comp.get_status() is None:
                init_ramdisk_comp.set_note(Notes.FAIL_TO_FIX)

        active_dump = check_dir["Active dump"]
        if active_dump.get_status() is False:
            active_dump.add_note("Active dump found, needs reboot")
        if active_dump.get_status() is None:
            active_dump.add_note(Notes.FAIL_TO_FIX)
