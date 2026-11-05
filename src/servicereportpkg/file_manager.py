# SPDX-License-Identifier: GPL-2.0-only
#
# (C) Copyright IBM Corp. 2018, 2019
# Author: Sourabh Jain <sourabhjain@linux.ibm.com>

"""Manages configuration files"""


import os
import shutil

from servicereportpkg.logger import get_default_logger


def backup_file(_file):
    """Take file backup with the prefix .sa.backup.

    Do not perform any operation if the backup file is
    already present.

    Returns:
    backup file path on success else None"""

    log = get_default_logger()

    if not os.path.isfile(_file):
        return None

    (file_path, file_name) = os.path.split(_file)
    backup_file_path = file_path+'/'+'.'+file_name+'.sa.backup'

    # Do not update backup file
    if os.path.isfile(backup_file_path):
        return backup_file_path

    try:
        shutil.copy2(_file, backup_file_path)
    except Exception as exception:
        log.debug("Backup Failed %s", exception)

        # Remove the backup file
        if os.path.isfile(backup_file_path):
            os.remove(backup_file_path)

        return None

    return backup_file_path
