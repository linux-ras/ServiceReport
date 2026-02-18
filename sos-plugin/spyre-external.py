# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# This plugin enables collection of logs for system with IBM Spyre card

import re
import pyudev

from sos.report.plugins import Plugin, IndependentPlugin


class SpyreExternal(Plugin, IndependentPlugin):
    """ Out of tree sos plugin to collect IBM Spyre
    card related logs.
    """

    short_desc = 'IBM Spyre Accelerator Information'
    plugin_name = 'spyre-external'
    architectures = ('ppc.*',)

    # IBM: 1014
    # IDs must be in hex format
    card_vendor_ids = ["0x1014"]
    card_device_ids = ["0x06a7", "0x06a8"]

    def setup(self):
        spyre_cards = self.get_spyre_cards()

        # Nothing to collect if spyre card is not present in the system
        if not spyre_cards:
            return

        # Collects the VFIO device's sysfs directory structure
        for card in spyre_cards:
            match = re.match(r"(\w+:\w+):", card)
            if not match:
                continue

            pci_domain_bus = match.group(1)

            pci_vfio_dir = f"/sys/devices/pci{pci_domain_bus}/{card}/vfio-dev"
            self.add_dir_listing(pci_vfio_dir, tree=True)

        # Lists PCI and PHB (PCI Host Bridge) slots and their details
        # on a Power system
        self.add_cmd_output([
            "lsslot -c pci",
            "lsslot -c phb",
        ])

        self.add_copy_spec([
            "/etc/modprobe.d/vfio-pci.conf",
            "/etc/udev/rules.d/95-vfio-3.rules",
            "/etc/security/limits.d/memlock.conf",
        ])

        spyre_users = self.get_spyre_users()
        # To always collect data for root user regardless
        if 'root' not in spyre_users:
            spyre_users.append('root')
        for user in spyre_users:
            # collects podman disk usage data
            command = f"sudo -iu {user} "
            if user == 'root':
                command = ""
            self.add_cmd_output([
                command + "podman system df",
                command + "podman system df -v",
            ])

    def get_spyre_cards(self):
        context = pyudev.Context()
        spyre_cards_bus_ids = []

        for device in context.list_devices(subsystem='pci'):
            vendor_id = device.attributes.get("vendor").decode("utf-8").strip()
            if vendor_id not in self.card_vendor_ids:
                continue

            device_id = device.attributes.get("device").decode("utf-8").strip()
            if device_id not in self.card_device_ids:
                continue

            spyre_cards_bus_ids.append(device.sys_name)

        return spyre_cards_bus_ids

    """
    get_spyre_users(): Get the names of users belonging to
    the sentient group.

    Currently, all users belonging to the sentient group are
    considered Spyre card users.

    Args:
    None

    Returns:
    List of spyre card users
    """
    def get_spyre_users(self):
        sentient_users = []
        getent_cmd = self.exec_cmd("getent group sentient")
        if getent_cmd['status'] == 0 and getent_cmd['output'].strip():
            for line in getent_cmd['output'].splitlines():
                line = line.strip().split(':')

                # Expected line format
                # group_name:x:group_id:user1,user2
                # No user at this line
                if len(line) < 4:
                    continue

                for user in line[3].split(','):
                    if user.strip() and user not in sentient_users:
                        sentient_users.append(user)

        return sentient_users
# vim: set et ts=4 sw=4 :
