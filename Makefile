# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

PYTHON:=python3


# build everything needed to install
build:
	$(PYTHON) -mpip wheel --verbose --progress-bar off --disable-pip-version-check --use-pep517 --no-build-isolation --wheel-dir ./build .

# install everything from build directory
install:
	$(PYTHON) -mpip install --verbose --progress-bar off --disable-pip-version-check --no-compile --ignore-installed --no-index --find-links ./build servicereport

# build the rpm package
build_rpm:
	$(PYTHON) -c "from setuptools import setup; setup()" bdist_rpm

# clean up temporary files from 'build' command
clean:
	rm -rf build
