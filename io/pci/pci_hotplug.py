#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2016 IBM
# Author: Narasimhan V <sim@linux.vnet.ibm.com>

"""
PCI Hotplug can remove and add pci devices when the system is active.
This test verifies that for supported slots.
"""

import os
import time
import re
from avocado import Test
from avocado import main
from avocado.utils import process, linux_modules, genio, pci, cpu


class PCIHotPlugTest(Test):

    """
    PCI Hotplug can remove and add pci devices when the system is active.
    This test verifies that for supported slots.

    :param device: Name of the pci device
    """

    def setUp(self):
        """
        Setup the device.
        """
        cmd = "uname -p"
        if 'ppc' not in process.system_output(cmd, ignore_status=True):
            self.cancel("Processor is not ppc64")
        cmd = "cat /proc/cpuinfo"
        if cpu._list_matches(open('/proc/cpuinfo').readlines(),
                             'platform\t: pSeries\n'):
            PowerVM = True
            for mdl in ['rpaphp', 'rpadlpar_io']:
                if not linux_modules.module_is_loaded(mdl):
                    linux_modules.load_module(mdl)
        elif cpu._list_matches(open('/proc/cpuinfo').readlines(),
                               'platform\t: PowerNV\n'):
            PowerVM = False
            if not linux_modules.module_is_loaded("pnv_php"):
                linux_modules.load_module("pnv_php")
        self.return_code = 0
        self.device = self.params.get('pci_device', default=' ')
        if not os.path.isdir('/sys/bus/pci/devices/%s' % self.device):
            self.cancel("PCI device given does not exist")
        if PowerVM:
            devspec = genio.read_file("/sys/bus/pci/devices/%s/devspec"
                                      % self.device)
            self.slot = genio.read_file("/proc/device-tree/%s/ibm,loc-code"
                                        % devspec)
            self.slot = re.match(r'((\w+)[\.])+(\w+)-P(\d+)-C(\d+)|Slot(\d+)',
                                 self.slot).group()
        else:
            self.slot = pci.get_pci_prop(self.device, "PhySlot")
        if not os.path.isdir('/sys/bus/pci/slots/%s' % self.slot):
            self.cancel("%s Slot not available" % self.slot)
        if not os.path.exists('/sys/bus/pci/slots/%s/power' % self.slot):
            self.cancel("%s Slot does not support hotplug" % self.slot)

    def test(self):
        """
        Creates namespace on the device.
        """
        genio.write_file("/sys/bus/pci/slots/%s/power" % self.slot, "0")
        time.sleep(5)
        cmd = "lspci -k -s %s" % self.device
        if process.system_output(cmd, shell=True).strip('\n') is not '':
            self.return_code = 1
        else:
            print "Adapter %s removed successfully" % self.device
        genio.write_file("/sys/bus/pci/slots/%s/power" % self.slot, "1")
        time.sleep(5)
        cmd = "lspci -k -s %s" % self.device
        if process.system_output(cmd, shell=True).strip('\n') is '':
            self.return_code = 2
        else:
            print "Adapter %s added back successfully" % self.device
        if self.return_code == 1:
            self.fail('%s not removed' % self.device)
        if self.return_code == 2:
            self.fail('%s not attached back' % self.device)


if __name__ == "__main__":
    main()
