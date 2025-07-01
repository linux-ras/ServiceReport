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

        self.add_cmd_output([
            "podman system df",
            "podman system df -v",
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

# vim: set et ts=4 sw=4 :
