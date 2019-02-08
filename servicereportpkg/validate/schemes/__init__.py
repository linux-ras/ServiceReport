# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Schemes package provides the system environment details"""


from servicereportpkg.logger import get_default_logger
from servicereportpkg.utils import get_package_classes


class Scheme(object):
    """Base class of all schemes"""

    def __init__(self):
        self.log = get_default_logger()

    @classmethod
    def is_valid(cls):
        """Returns true if the scheme is valid"""

        return False


class SchemeHandler(object):
    """Handles the schemes package"""

    def __init__(self):
        self.log = get_default_logger()
        self.populate_schemes()
        self.populate_valid_schemes()

    def get_schemes(self):
        """Returns a list of all the schemes present in schemes package"""

        return self.schemes

    def get_valid_schemes(self):
        """Returns a list of valid schemes"""

        return self.valid_schemes

    def populate_schemes(self):
        """Find all the available schemes package"""

        self.schemes = []

        for _class in get_package_classes(__path__, 'servicereportpkg.validate.schemes.'):
            if issubclass(_class, Scheme):
                self.schemes.append(_class)

    def populate_valid_schemes(self):
        """Extracts the valid schemes from available schemes"""

        self.valid_schemes = []

        for scheme in self.schemes:
            if scheme.is_valid():
                self.valid_schemes.append(scheme)
