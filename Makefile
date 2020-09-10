# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

PYTHON:=python3


# build everything needed to install
build:
	$(PYTHON) setup.py build

# install everything from build directory
install:
	$(PYTHON) setup.py install

# build the rpm package
build_rpm:
	$(PYTHON) setup.py bdist_rpm

# clean up temporary files from 'build' command
clean:
	$(PYTHON) setup.py clean --all
