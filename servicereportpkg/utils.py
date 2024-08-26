# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Provides utility functions to validation tool"""


import os
import inspect
import pkgutil
import importlib
import subprocess
from distutils.spawn import find_executable


from servicereportpkg.logger import get_default_logger


def get_package_classes(pkg_path, prefix):
    """Returns all the classes present in a given package"""

    log = get_default_logger()

    try:
        pkg_classes = []

        for (module_loader, name, ispkg) in \
                pkgutil.walk_packages(pkg_path,
                                      prefix):
            if ispkg:
                continue

            module = importlib.import_module(name)
            module_classes = [_class for cname, _class in
                              inspect.getmembers(module, inspect.isclass)
                              if _class.__module__ == name]

            pkg_classes.extend(module_classes)

    except SyntaxError as syntax_error:
        log.debug("Syntax error in module %s, error: %s", name, syntax_error)

    except ImportError as import_error:
        log.debug("Invalid import statement in %s module, error %s", name,
                  import_error)

    return pkg_classes


def get_distro_name():
    """Finds the distro name from /etc/os-release and on success returns
    the distro name else empty string"""

    os_release = '/etc/os-release'
    distro_search_key = 'PRETTY_NAME'
    log = get_default_logger()

    try:
        with open(os_release, 'r') as _file:
            for line in _file:
                (key, value) = line.split("=")
                if key.startswith(distro_search_key):
                    return value.strip()

    except IOError as io_error:
        log.debug("Unable to open the file: /etc/os-release, error: %s",
                  io_error)

    except IndexError as index_error:
        log.debug("Format issue in file /etc/os-release, error: %s",
                  index_error)

    return ""


def get_system_platform():
    """Finds the platform information in cpuinfo. On success returns the
    system platform else empty string"""

    log = get_default_logger()
    cpuinfo_file = "/proc/cpuinfo"
    system_platform = ""

    try:
        with open(cpuinfo_file) as o_file:
            for line in o_file:
                if "platform" in line:
                    name = line.split(':')[1]
                    system_platform = name.strip()
                    return system_platform.lower()

    except IOError as io_error:
        log.debug("Failed to open file: /proc/cpuinfo, error: %s", io_error)

    return system_platform


def is_command_exists(command):
    """Return True if the given command present in the system else False"""

    return find_executable(command) is not None


def execute_command(command, sh=False):
    """Executes the command with given arguments and returns a tuple of three
    values exit status, stdout, and stderr. In case of command not found or an
    exception occurs during the command execution it returns (None, None, None)
    """

    log = get_default_logger()

    try:
        if not is_command_exists(command[0]):
            log.debug("%s command not found", command[0])
            return (None, None, None)

        if sh:
            command = ' '.join(command)

        process = subprocess.Popen(command,
                                   shell=sh,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        (output, err) = process.communicate()
        output = output.decode('utf-8')
        return(process.returncode, output, err)

    except OSError as os_error:
        log.debug("Failed create process to execute %s command: error: %s",
                  command[0], os_error)
        return(None, None, None)


def find_package_manager():
    """Returns the package manager supported in the current system"""

    distro = get_distro_name()
    package_manager_options = \
        {"Fedora": {"command": "rpm", "search_option": "-qi",
                    "installer": "yum", "install_option": "install -y"},
         "Red Hat": {"command": "rpm", "search_option": "-qi",
                     "installer": "yum", "install_option": "install -y"},
         "Ubuntu": {"command": "dpkg", "search_option": "-s",
                    "installer": "apt", "install_option": "install -y"},
         "SUSE": {"command": "rpm", "search_option": "-qi",
                  "installer": "zypper", "install_option": "install -y"}}

    for key in package_manager_options:
        if key in distro:
            return package_manager_options[key]

    return None


def is_package_installed(package):
    """Return True if given package is present in the system else False"""

    package_manager_options = find_package_manager()
    log = get_default_logger()

    if package_manager_options is None:
        log.warning("Unable to locate the package manager")
        return None

    package_manager = package_manager_options["command"]
    search_option = package_manager_options["search_option"]
    (return_code, stdout) = \
        execute_command([package_manager, search_option, package])[:-1]

    if return_code is None:
        return None
    elif return_code == 0:
        return True

    return False


def get_service_processor():
    """Find and return the service processor type if present else
    empty string"""

    service_processor = ""

    if os.path.isdir("/proc/device-tree/fsps"):
        service_processor = "fsps"
    elif os.path.isdir("/proc/device-tree/bmc"):
        service_processor = "bmc"

    return service_processor


def is_daemon_enabled(daemon):
    """Returns True if given daemon is enabled in the system else False"""

    command = ["systemctl", "is-enabled", daemon]
    return_code = execute_command(command)[0]

    if return_code is None:
        return None
    elif return_code == 0:
        return True

    return False


def get_service_status(service):
    """Checks the service status by issuing the systemctl command"""

    command = ["systemctl", "is-active", service]
    return_code = execute_command(command)[0]
    log = get_default_logger()

    if return_code is None:
        log.debug("Failed to get the status of service %s", service)
    return return_code


def get_file_content(file_path):
    """Returns the given file content as a string. None is returned
    if file is not present"""

    log = get_default_logger()

    try:
        with open(file_path, 'r') as o_file:
            data = o_file.read()
            return data.strip()

    except IOError as io_error:
        log.debug("Failed to open file: %s, error: %s", file_path, io_error)

    return None


def get_file_size(file_path):
    """Returns the size of file or None if file is not present"""

    log = get_default_logger()

    try:
        file_info = os.stat(file_path)
        return file_info.st_size

    except OSError as os_error:
        log.debug("Failed to open file: %s, error: %s", file_path, os_error)

    return None


def is_string_in_file(string, file_path):
    """Check the given string is present in the file or not"""

    file_content = get_file_content(file_path)

    if file_content and string in file_content:
        return True

    return False


def trigger_kernel_crash():
    """Trigger the crash"""

    os.system("echo 1 > /proc/sys/kernel/sysrq")
    os.system("sync")
    os.system("echo c > /proc/sysrq-trigger")


def get_total_ram():
    """Returns the RAM size in KB"""

    log = get_default_logger()

    try:
        with open('/proc/meminfo') as o_file:
            for line in o_file.readlines():
                (key, val) = line.split(':', 1)
                if "MemTotal" in key:
                    mem = val.strip().split(' ', 1)[0]
                    return int(mem)
    except (IOError, ValueError) as exception:
        log.debug("Unable to extract the total RAM from /proc/meminfo, %s",
                  exception)

    return None


def install_package(package):
    """Install the given package."""

    package_manager = find_package_manager()
    log = get_default_logger()

    if package_manager is None:
        log.warning("Unable to locate the package manager")
        return None

    command = package_manager["installer"]+" "+package_manager["install_option"]+" "+package
    return_code = os.system(command)

    if return_code is None:
        return None
    elif return_code == 0:
        return True

    return False


def enable_daemon(daemon):
    """Enables the daemon to start at boot time."""

    command = ["systemctl", "enable", daemon]
    return_code = execute_command(command)[0]

    if return_code == 0:
        return True

    return False

def start_service(service):
    """Start the given service."""

    command = ["systemctl", "start", service]

    return_code = execute_command(command)[0]
    if return_code == 0:
        return True

    return False


def restart_service(service):
    """Restart the given service"""

    command = ["systemctl", "restart", service]

    return_code = execute_command(command)[0]
    if return_code == 0:
        return True

    return False


def is_update_bls_supported():
    """Returns True if grub2-mkconfig command support update
    bls support, False otherwise"""

    (stdout) = execute_command(["grub2-mkconfig", "-h"])[1]

    if stdout is None:
        return False

    if "update-bls-cmdline" in stdout:
        return True

    return False


def update_grub():
    command = ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"]

    if is_update_bls_supported():
        command.append("--update-bls-cmdline")

    return_code = execute_command(command)[0]
    if return_code == 0:
        return True

    return False
