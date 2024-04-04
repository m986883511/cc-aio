import os
import json
import base64
import hashlib
import logging
import traceback

from oslo_config import cfg

from cg_utils import execute, func, file, _, AUTHOR_NAME
from hostadmin.files import FilesDir
from hostadmin.config import CONF

LOG = logging.getLogger(__name__)


class SshEndPoint(object):
    def __init__(self):
        self.SSH_TIMEOUT=2
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.PVETUI_CONF_PATH = f'/etc/{AUTHOR_NAME}/pvetui.conf'
        self.default_root_password = CONF.ssh.root_pwd

    def check_ssh_passwordless(self, ctxt, host):
        assert os.path.exists(self.SSH_PRIVATE_KEY_PATH), f'ssh_key_file={self.SSH_PRIVATE_KEY_PATH} is not exit'
        cmd = f"ssh -o PreferredAuthentications=publickey -o ConnectTimeout={self.SSH_TIMEOUT} -i {self.SSH_PRIVATE_KEY_PATH} root@{host} /bin/true"
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'{host} is not ssh passwordless, err={content}'
        return flag == 0
    
    def ssh_passwordless_to_host(self, ctxt, host):
        try:
            self.check_ssh_passwordless(ctxt=ctxt, host=host)
        except Exception as e:
            cmd = f'sshpass -p {self.default_root_password} ssh-copy-id -i {FilesDir.SSH.id_rsa_pub} root@{host}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'ssh_passwordless_to_host to {host}', content)

    def ssh_run_on_remote(self, ctxt, host, cmd):
        assert os.path.exists(self.SSH_PRIVATE_KEY_PATH), f'ssh_key_file={self.SSH_PRIVATE_KEY_PATH} is not exit'
        cmd = f"ssh -o PreferredAuthentications=publickey -o ConnectTimeout={self.SSH_TIMEOUT} -i {self.SSH_PRIVATE_KEY_PATH} root@{host} \"{cmd}\""
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'ssh run on remote', content)
        return flag, content

    def ssh_run_on_remote_via_popen(self, ctxt, host, cmd):
        assert os.path.exists(self.SSH_PRIVATE_KEY_PATH), f'ssh_key_file={self.SSH_PRIVATE_KEY_PATH} is not exit'
        return_code = execute.execute_ssh_command_via_id_rsa_in_popen(cmd, self.SSH_PRIVATE_KEY_PATH, host)
        execute.completed(return_code, f'ssh run on remote via popen', f'cmd={cmd}')
        return return_code

    def rsync_dir_to_remote_host(self, ctxt, host, src_dir, progress):
        flag = 0 if os.path.exists(src_dir) else 1
        execute.completed(flag, f'check src_dir={src_dir} exist')
        src_dir_dir = os.path.dirname(src_dir)
        self.ssh_run_on_remote(ctxt=ctxt, host=host, cmd=f'mkdir -p {src_dir_dir}')
        progress_str = '--progress' if progress else ''
        cmd = f'rsync -avz {progress_str} -e "ssh -i {self.SSH_PRIVATE_KEY_PATH}" {src_dir} root@{host}:{src_dir_dir}'
        return_code = execute.execute_command_in_popen(cmd)
        execute.completed(return_code, f'rsync {src_dir} to root@{host}:{src_dir_dir}')

    def scp_dir_to_remote_host(self, ctxt, host, src_dir, dst_dir):
        cmd = f'scp -o StrictHostKeyChecking=no -i {self.SSH_PRIVATE_KEY_PATH} -r {src_dir} root@{host}:{dst_dir}'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'scp {src_dir} to {host}:{dst_dir} failed, err={content}'
        return flag, content

    def scp_remote_host_dir_to_current_host(self, ctxt, host, src_dir, dst_dir):
        cmd = f'scp -o StrictHostKeyChecking=no -i {self.SSH_PRIVATE_KEY_PATH} -r root@{host}:{src_dir} {dst_dir}'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'scp {host}:{src_dir} {dst_dir} to failed, err={content}'
        return flag, content

    def execute_on_all_hosts(self, ctxt, command):
        import click
        flag = 0 if os.path.exists(self.PVETUI_CONF_PATH) else 1
        execute.completed(flag, f'check {self.PVETUI_CONF_PATH} exist')
        value = file.ini_file_to_dict(self.PVETUI_CONF_PATH)
        flag = 0 if isinstance(value, dict) else 1
        execute.completed(flag, f'check ini_file_to_dict return value', f'value type is {type(value)}')

        def get_host_list():
            hosts = []
            nodes = func.get_dict_dict_value(value, 'base_env', f'installed_nodes') or ''
            nodes = nodes.replace(',', ' ').split()
            nodes = [i for i in nodes if i]
            hosts.extend(nodes)
            hosts = list(set(hosts))
            hosts.sort()
            return hosts

        hosts = get_host_list()
        for host in hosts:
            flag = execute.check_ssh_can_connect_via_id_rsa(self.SSH_PRIVATE_KEY_PATH, host)
            execute.completed(not flag, f'check {host} can not ssh via id_rsa', raise_flag=False)

        all_result = {}
        failed_flag = False
        for host in hosts:
            click.secho(f"#--- exec '{command}' on {host} ---#", fg='green')
            flag, content = execute.execute_ssh_command_via_id_rsa(command, self.SSH_PRIVATE_KEY_PATH, host)
            if flag == 0:
                all_result[host] = 'ok'
            else:
                all_result[host] = content
                failed_flag = True
            click.secho(content)

        all_result = json.dumps(all_result, indent=4)
        color = 'red' if failed_flag else 'green'
        click.secho(f"\n#--- summary: execute '{command}' on {hosts} ---#", fg='green')
        click.secho(all_result, fg=color)
