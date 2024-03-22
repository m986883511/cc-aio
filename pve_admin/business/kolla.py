import os
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file
from pve_admin.files import FilesDir

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class KollaEndPoint(object):
    def __init__(self):
        self.SSH_TIMEOUT=2
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.default_root_password = CONF.ssh.root_pwd

    def deploy(self, ctxt):
        cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
        cmd = f'bash {FilesDir.Shell.deploy_kolla}'
        flag = execute.execute_command_in_popen(cmd, shell=True)
        execute.completed(flag, f'deploy openstack')
    
    def install_kolla_ansible(self, ctxt):
        cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
        cmd = f'bash {FilesDir.Shell.install_kolla_ansible}'
        flag = execute.execute_command_in_popen(cmd, shell=True)
        execute.completed(flag, f'install kolla-ansible')

    def add_compute_node(self, ctxt, host):
        cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
        cmd = f'bash {FilesDir.Shell.add_compute_node} {host}'
        flag = execute.execute_command_in_popen(cmd, shell=True)
        execute.completed(flag, f'add compute node {host}')

    def access_ceph(self, ctxt, ceph_admin_node):
        cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
        cmd = f'bash {FilesDir.Shell.kolla_access_ceph} {ceph_admin_node}'
        flag = execute.execute_command_in_popen(cmd, shell=True)
        execute.completed(flag, f'kolla access ceph {ceph_admin_node}')
