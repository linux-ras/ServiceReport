# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Plugin to repair the daemon checks"""


from servicereportpkg.repair.plugins import RepairPlugin
from servicereportpkg.utils import enable_daemon
from servicereportpkg.check import Notes

class DaemonRepair(RepairPlugin):
    """Enable daemon to start on boot"""

    def __init__(self):
        RepairPlugin.__init__(self)
        self.name = "Daemon"

    def repair(self, plugin_obj, checks):
        """Repair daemon checks"""

        for check in checks:
            if not check.get_status():
                if enable_daemon(check.get_name()):
                    check.set_status(True)
                    check.set_note(Notes.FIXED)
                else:
                    check.set_note(Notes.NOT_FIXABLE)
