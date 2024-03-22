import os
import logging
import platform

LOG = logging.getLogger(__name__)


def check_is_root():
    flag = os.geteuid() == 0
    if not flag:
        LOG.warning("current user not have root permission")
    return flag


def get_architecture():
    m = platform.machine()
    if 'x86' in m.lower():
        return 'x86_64'
    else:
        return 'aarch64'
