import os
import re
import json
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file
from hostadmin.files import FilesDir

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class ServiceEndPoint(object):

    def __init__(self):
        self.support_pci_types = ['gpu', 'vgpu', 'other']
        self.pci_device_set_vfio_driver_file_path = '/etc/modprobe.d/vfio-pci.conf'
        self.module_load_vfio_pci_file_path = '/etc/modules-load.d/vfio-pci.conf'
        self.modprobe_blacklist_file_path = '/etc/modprobe.d/blacklist.conf'
        self.apt_source_list_path = '/etc/apt/sources.list'

    def install_alist(self, ctxt):
        return_code, content = execute.execute_command(f'atlicense -m')
        LOG.info(f'HostEndPoint get_machine_code return_code={return_code}, content={content}')
        if return_code != 0:
            raise Exception(content)
        hostname = func.get_current_node_hostname()
        return {'machine_code': content, 'hostname': hostname}

    def get_hostname(self, ctxt):
        hostname = func.get_current_node_hostname()
        return hostname