import os
import json
import base64
import hashlib
import logging
import traceback

from oslo_config import cfg

from cg_utils import execute, func, file, _
from hostadmin.files import FilesDir

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PveEndPoint(object):
    def __init__(self):
        self.SSH_TIMEOUT=2
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.PVETUI_CONF_PATH = '/etc/cg/pvetui.conf'
        self.default_root_password = CONF.ssh.root_pwd
        self.vbios_path = '/opt/cg/presetup/repo/bin/vbios'

    def create_vbios_file(self, ctxt):
        from hostadmin.business import HostEndPoint
        pci_device_dict = HostEndPoint().get_support_pci_devices(ctxt=ctxt)
        igd_dict = pci_device_dict.get('igd')
        execute.completed(not igd_dict, 'check have igd gpu')
        flag = os.path.isfile(self.vbios_path)
        execute.completed(not flag, 'check vbios file exist')
        flag, content = execute.execute_command(f'chmod +x {self.vbios_path}')
        execute.completed(flag, 'chmod +x vbios file')
        vbios_dir_name = os.path.dirname(self.vbios_path)
        vbios_file_name = os.path.basename(self.vbios_path)
        flag, content = execute.execute_command(f'cd {vbios_dir_name} && ./{vbios_file_name}')
        execute.completed(flag, 'generate vbios file')
        content_list = func.get_string_split_list(content, ' ')
        flag = content_list[-1].startswith('vbios_') and content_list[-1].endswith('.bin')
        execute.completed(not flag, 'find vbios file from output')
        vbio_file_path = os.path.join(vbios_dir_name, content_list[-1])
        return vbio_file_path
