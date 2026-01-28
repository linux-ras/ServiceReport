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

        self.add_copy_spec([
            "/etc/modprobe.d/vfio-pci.conf",
            "/etc/udev/rules.d/95-vfio-3.rules",
            "/etc/security/limits.d/memlock.conf",
        ])

        # collect podman data for non root spyre users
        self.get_podman_data()

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

    def get_podman_data(self):

        # All spyre users must be part of sentient group
        groupname = "sentient"
        # collecting podman data only for spyre users.
        non_root_users = self.exec_cmd("getent group "+ groupname)
        if non_root_users['status'] == 0:
            # parse the output(example: sentient:x:1021:root,user1,user2)
            # to get the user names
            users = [
                        u.strip()
                        for u in non_root_users['output']
                                # split output and fetch usernames from row 3
                                .split(':')[3]
                                # further output by , to get user name
                                .split(',')
                        if u.strip()
                    ]
            subcmds = [
                'info',
                'images',
                'image trust show',
                'images --digests',
                'pod ps',
                'port --all',
                'ps',
                'stats --no-stream --all',
                'version',
                'volume ls',
                'system df -v',
            ]

            for user in users:
                # since root user outputs are collected in podman plugin
                # skipping here
                if not user or user == 'root':
                    continue
                command = "sudo -u "+ user
                cmd = self.exec_cmd(f"{command} podman ps -aq")
                # if command is not successful or no container running in
                # a non root user session not collecting the  data.
                if (cmd['status'] != 0
                    or not cmd['output'].strip()):
                    continue

                self.add_cmd_tags({
                    f'{command} podman images': 'podman_list_images',
                    f'{command} podman ps': 'podman_list_containers'
                })

                self.add_cmd_output(
                        [f"{command} podman {s}" for s in subcmds],
                        subdir=f'podman/{user}',
                        tags='podman_commands'
                )

                # separately grab ps -s as this can take a *very* long time
                self.add_cmd_output(
                        f'{command} podman ps -as',
                        subdir=f'podman/{user}',
                        priority=100
                )

                pnets = self.collect_cmd_output(
                        f'{command} podman network ls',
                         subdir=f'podman/{user}',
                         tags='podman_list_networks'
                )
                if pnets['status'] == 0:
                    nets = [
                        pn.split()[0]
                        for pn in pnets['output'].splitlines()[1:]
                        if pn.strip()
                    ]
                    self.add_cmd_output(
                        [
                            f"{command} podman network inspect {net}"
                            for net in nets
                        ],
                        subdir=f'podman/{user}/networks',
                        tags='podman_network_inspect'
                    )

                containers = self.collect_cmd_output(
                        f'{command} podman ps -a',
                        subdir=f'podman/{user}'
                )
                if containers['status'] == 0:
                    # parse to get container id
                    cids = [
                        # get 1st column container id
                        container.split()[0]
                        # skip the heading line
                        for container in containers['output'].splitlines()[1:]
                        if container.strip()
                    ]
                    self.add_cmd_output(
                        [
                            f"{command} podman inspect {cid}"
                            for cid in cids
                        ],
                        subdir=f'podman/{user}/containers',
                        tags='podman_container_inspect'
                    )
                    self.add_cmd_output(
                        [
                            f"{command} podman logs -t {cid}"
                            for cid in cids
                        ],
                        subdir=f'podman/{user}/containers',
                        priority=50
                    )

                images = self.collect_cmd_output(
                        f'{command} podman images --no-trunc',
                        subdir=f'podman/{user}'
                )
                if images['status'] == 0:
                    # parse to get the image ids
                    imageids = [
                        image.split()[2]
                        # if image id is none fetch image name{name:tag}
                        if image.split()[0].lower() == 'none'
                        else f"{image.split()[0]}:{image.split()[1]}"
                        # split into lines and skip the heading line
                        for image in images['output'].splitlines()[1:]
                        if image.strip()
                    ]
                    self.add_cmd_output(
                        [
                            f"{command} podman inspect {imageid}"
                            for imageid in imageids
                        ],
                        subdir=f'podman/{user}/images',
                        tags='podman_image_inspect'
                    )
                    self.add_cmd_output(
                        [
                            f"{command} podman image tree {imageid}"
                            for imageid in imageids
                        ],
                        subdir=f'podman/{user}/images/tree',
                        tags='podman_image_tree'
                    )

                volumes = self.collect_cmd_output(
                        f'{command} podman volume ls --format "{{{{.Name}}}}"',
                        subdir=f'podman/{user}'
                )
                if volumes['status'] == 0:
                    vols = [
                        v for v in volumes['output'].splitlines()
                        if v.strip()
                    ]
                    self.add_cmd_output(
                        [
                            f"{command} podman volume inspect {vol}"
                            for vol in vols
                        ],
                        subdir=f'podman/{user}/volumes',
                        tags='podman_volume_inspect'
                    )


# vim: set et ts=4 sw=4 :
