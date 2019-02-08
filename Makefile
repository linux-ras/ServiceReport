# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>


# build everything needed to install
build:
	python setup.py build

# install everything from build directory
install:
	python setup.py install

# build the rpm package
build_rpm:
	python setup.py bdist_rpm

# clean up temporary files from 'build' command
clean:
	python setup.py clean --all
