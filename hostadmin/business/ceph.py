import os
import re
import math
import json
import base64
import hashlib
import logging
import traceback

from oslo_config import cfg

from cg_utils import linux, func, execute, file, _, AUTHOR_NAME, AIO_CONF_NAME
from hostadmin.files import FilesDir
from hostadmin.config import CONF

LOG = logging.getLogger(__name__)


class CephEndPoint(object):
    def __init__(self):
        self.version_path = f'/opt/{AUTHOR_NAME}/jmversion'
        self.architecture = linux.get_architecture()

        self.initial_dashboard_password = 'password'
        self.ceph_conf_dir = '/etc/ceph'
        self.ceph_conf_path = f'{self.ceph_conf_dir}/ceph.conf'
        self.ceph_pub_key_path = f'{self.ceph_conf_dir}/ceph.pub'
        self.cluster_network = '192.222.12.0/24'
        self.public_network = '192.222.13.0/24'
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.SSH_PUBLIC_KEY_PATH = FilesDir.SSH.id_rsa_pub

    def _get_ceph_version_path(self):
        assert os.path.isdir(self.version_path), 'jmversion path is not exist'
        pattern = f"^ceph-registry-(.*)-{self.architecture}.tar$"
        result = []
        for name in os.listdir(self.version_path):
            match = re.search(pattern, name)
            if match:
                file_path = os.path.join(self.version_path, name)
                result.append(file_path)
        return result

    def check_host_kernel_support_bcache(self, ctxt):
        cmd = 'grep -E "^CONFIG_BCACHE=(m|y)$" /boot/config-$(uname -r)'
        flag, content = execute.execute_command(cmd)
        # assert flag == 0, f'current host kernel bcache is not support'
        return flag == 0

    def _import_ceph_registry(self, image_file_path):
        filename = os.path.basename(image_file_path)
        registry_tag = filename.replace('ceph-registry-', '').replace('.tar', '')
        assert registry_tag, f'registry_tag={registry_tag} can not be None'
        cmd = f'podman import {image_file_path} ceph-registry:{registry_tag}'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'podman import ceph registry failed, err={content}'
        cmd = f'podman images | grep ceph-registry | grep {registry_tag}'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'podman image ceph-registry:{registry_tag} is not exist, err={content}'

    def run_ceph_registry(self, ctxt, **kwargs):
        def _get_get_ceph_version_path():
            _ceph_version = kwargs.get('ceph_version_path')
            if _ceph_version:
                assert os.path.exists(_ceph_version), f'your input ceph version={_ceph_version} is not exist'
            else:
                _ceph_version = self._get_ceph_version_path()
                assert _ceph_version, f'get ceph registry version in path={self.version_path} failed'
                return _ceph_version[0]
        registry_image_name='ceph-registry'
        registry_container_name='ceph_registry'
        cmd = f'podman images | grep -c {registry_image_name}'
        flag, content = execute.execute_command(cmd)
        ceph_registry_image_count = int(content) if flag == 0 else 0
        if ceph_registry_image_count == 0:
            ceph_version = _get_get_ceph_version_path()
            self._import_ceph_registry(ceph_version)
        elif ceph_registry_image_count > 1:
            raise Exception(f'check ceph-registry image count failed, now={ceph_registry_image_count}')
        cmd = f"podman images | grep {registry_image_name}"
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'get ceph registry image id failed, err={content}'
        content_list = func.get_string_split_list(content, split_flag=' ')
        registry_image_id = content_list[2]
        LOG.info(f'get ceph registry image id os {registry_image_id}')
        LOG.info('delete old ceph registry container')
        cmd = f'podman ps -a | grep {registry_container_name}'
        flag, content = execute.execute_command(cmd)
        if flag == 0:
            cmd = f'podman rm -f {registry_container_name}'
            flag, content = execute.execute_command(cmd)
            assert flag == 0, f'delete old ceph restry container failed, err={content}'

        LOG.info(f"run {registry_container_name} container")
        cmd = f"podman run -d --name={registry_container_name} --restart=always --privileged=true --net=host {registry_image_id} sh -c \"registry serve /etc/docker/registry/config.yml\""
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f'run {registry_container_name} container failed, err={content}'
        return 'run ceph registry success'

    def run_install_ceph_node(self, ctxt, host: str, osd_pool_default_size=3):
        current_hostname = func.get_current_node_hostname()
        if current_hostname == host:
            cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
            cmd = f'bash {FilesDir.Shell.install_as_ceph_admin_node} {osd_pool_default_size}'
            flag = execute.execute_command_in_popen(cmd, shell=True)
            execute.completed(flag, f'install ceph as admin node on {host}')
        else:
            cmd = f'cg-hostcli ssh scp-dir-to-remote-host {host} {FilesDir.Shell.shell_dir} /tmp'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'scp {FilesDir.Shell.shell_dir} to {host}', content)
            cmd = f'bash /tmp/shell/install_as_ceph_admin_node.sh {osd_pool_default_size}'
            flag = execute.execute_ssh_command_via_id_rsa_in_popen(cmd, FilesDir.SSH.id_rsa, host)
            execute.completed(flag, f'install ceph as admin node on {host}')
    
    def _get_suggest_pg_number(self):
        cmd = f'ceph osd tree -f json'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, f'ceph osd tree', content)
        try:
            data_dict = json.loads(content)
        except:
            execute.completed(1, f'json loads')
        nodes_list = data_dict.get('nodes') or []
        osd_names = [value['name'] for value in nodes_list if value.get('type') == 'osd']
        osd_counts = len(osd_names)
        if osd_counts == 0:
            execute.completed(1, 'get suggest pg number', 'no osd')
        cmd = 'ceph config get osd osd_pool_default_size'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'get ceph osd_pool_default_size')
        osd_pool_default_size = int(content)
        input_number = 1.0*osd_counts*100/osd_pool_default_size
        LOG.info(f'input_number input_number={input_number}')
        pg_number = 2 ** math.ceil(math.log2(input_number))
        LOG.info(f'osd_counts={osd_counts}, osd_pool_default_size={osd_pool_default_size}, calc pg_number={pg_number}')
        return pg_number

    def run_add_ceph_node(self, ctxt, host: str):
        current_hostname = func.get_current_node_hostname()
        if current_hostname == host:
            cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
            cmd = f'bash {FilesDir.Shell.add_as_ceph_node}'
            flag = execute.execute_command_in_popen(cmd, shell=True)
            execute.completed(flag, f'add ceph node {host}')
        else:
            cmd = f'cg-hostcli ssh scp-dir-to-remote-host {host} {FilesDir.Shell.shell_dir} /tmp'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'scp {FilesDir.Shell.shell_dir} to {host}', content)
            cmd = f'bash /tmp/shell/add_as_ceph_node.sh'
            flag = execute.execute_ssh_command_via_id_rsa_in_popen(cmd, FilesDir.SSH.id_rsa, host)
            execute.completed(flag, f'add ceph node {host}')

    def get_ceph_fsid(self, ctxt):
        cmd = f'ceph fsid'
        flag, content = execute.execute_command(cmd, shell=False, timeout=5)
        execute.completed(flag, f'get ceph fsid', content)
        return content

    def ceph_orch_ps_current_node(self, ctxt):
        current_hostname = func.get_current_node_hostname()
        cmd = f'ceph orch ps {current_hostname}'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, f'{cmd}', content)
        should_have_names = [f'{i}.{current_hostname}' for i in ['mgr', 'mon']]
        for name in should_have_names:
            if name not in content:
                execute.completed(1, f"not have {name} in '{cmd}'")
    
    def check_ceph_node_network(self, ctxt, ceph_node_hostname):
        ip = func.get_hostname_map_ip(ceph_node_hostname)
        ip_endwith = func.get_string_split_list(ip, split_flag='.')[-1]
        public_ip = f'192.222.13.{ip_endwith}'
        cluster_ip = f'192.222.12.{ip_endwith}'
        cmd = f'ping -t 1 -c 1 {public_ip}'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'ping {ceph_node_hostname} public_ip={public_ip}', content)
        cmd = f'ping -t 1 -c 1 {cluster_ip}'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'ping {ceph_node_hostname} cluster_ip={cluster_ip}', content)
    
    def get_ceph_orch_ls(self, ctxt):
        flag, content = execute.execute_command('ceph orch ls -f json', shell=False, timeout=5)
        execute.completed(flag, 'ceph orch ls', content)
        try:
            value = json.loads(content)
        except Exception as e:
            execute.completed(1, 'json load content')
        flag = 0 if isinstance(value, list) else 1
        execute.completed(flag, 'check content is list')
        return value

    def set_current_node_as_mon_mgr_node(self, ctxt):
        current_hostname = func.get_current_node_hostname()
        value = self.get_ceph_orch_ls(ctxt=ctxt)
        for data in value:
            flag = 0 if isinstance(data, dict) else 1
            execute.completed(flag, 'check date is dict')
            service_name = data['service_name']
            if service_name not in ['mgr', 'mon']:
                continue
            hosts = data['placement'].get('hosts') or []
            if current_hostname not in hosts:
                hosts.append(current_hostname)
                LOG.info(f'add {current_hostname} as {service_name}')
                hosts_str = ','.join(hosts)
                flag, content = execute.execute_command(f'ceph orch apply {service_name} {hosts_str}', shell=False, timeout=10)
                execute.completed(flag, f'ceph orch apply {service_name} {hosts_str}', content)
        
    def copy_ceph_public_key_to_remote_host(self, ctxt, remote_host):
        fsid = self.get_ceph_fsid(ctxt)
        assert fsid, f'copy ceph public key failed, no fsid found'
        check_key_name = f"ceph-{fsid}"
        cmd = f'ssh -i {self.SSH_PRIVATE_KEY_PATH} root@{remote_host} cat /root/.ssh/authorized_keys|grep {check_key_name}'
        flag, content = execute.execute_command(cmd)
        if flag != 0:
            cmd = f'cat {self.ceph_pub_key_path} | ssh -i {self.SSH_PRIVATE_KEY_PATH} root@{remote_host} "cat >> /root/.ssh/authorized_keys"'
            flag, content = execute.execute_command(cmd)
            assert flag == 0, f'copy {self.ceph_pub_key_path} to {remote_host} failed'
        else:
            LOG.info(f"no need copy ceph.pub to {remote_host}")
        return flag, content
    
    def _get_ceph_default_registry_url(self):
        cmd = 'cat /usr/bin/cephadm|grep "^DEFAULT_REGISTRY"'
        flag, content = execute.execute_command(cmd)
        # DEFAULT_REGISTRY = 'ceph.repo:4002'
        assert flag == 0, f"get cephadm DEFAULT_REGISTRY failed"
        ceph_default_registry_url = content.replace('DEFAULT_REGISTRY','').replace('=','').replace("'", '').replace(' ','')
        assert ':' in ceph_default_registry_url, f'get ceph_default_registry_url failed, it={ceph_default_registry_url}'
        LOG.info(f'get ceph DEFAULT_REGISTRY={ceph_default_registry_url}')
        return ceph_default_registry_url

    def set_ceph_registry_url(self, ctxt, host):
        ceph_default_registry_url = self._get_ceph_default_registry_url()
        ceph_default_registry_host = ceph_default_registry_url.split(':')[0]
        LOG.info(f'get ceph DEFAULT_REGISTRY={ceph_default_registry_host}')

        cmd = f'sed -i "/{ceph_default_registry_host}/d" /etc/hosts'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f"delete old ceph_default_registry_host failed"
        host_222_ip = func.get_hostname_map_ip(host)
        cmd = f'echo "{host_222_ip} {ceph_default_registry_host}" >> /etc/hosts'
        flag, content = execute.execute_command(cmd)
        assert flag == 0, f"write new ceph_default_registry_host failed"
        return "set ceph registry url success"

    def cephadm_init_pools(self, ctxt):
        pg_num = self._get_suggest_pg_number()
        cmd = f'ceph osd pool create volumes {pg_num}'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph create volumes pools", content)
        cmd = f'ceph osd pool create images {pg_num}'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph create images pools", content)
        cmd = f'ceph osd pool create backups {pg_num}'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph create backups pools", content)
        cmd = f'ceph osd pool create vms {pg_num}'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph create vms pools", content)
        cmd = 'rbd pool init volumes'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph init volumes pools", content)
        cmd = 'rbd pool init images'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph init images pools", content)
        cmd = 'rbd pool init backups'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph init backups pools", content)
        cmd = 'rbd pool init vms'
        flag, content = execute.execute_command(cmd, shell=False, timeout=10)
        execute.completed(flag, "ceph init vms pools", content)
        cmd = "ceph auth get-or-create client.glance mon 'profile rbd' osd 'profile rbd pool=images' mgr 'profile rbd pool=images'"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "ceph create user glance", content)

        cmd = "ceph auth get-or-create client.cinder mon 'profile rbd' osd 'profile rbd pool=volumes, profile rbd pool=vms, profile rbd-read-only pool=images' mgr 'profile rbd pool=volumes, profile rbd pool=vms'"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "ceph create user cinder", content)
        cmd = "ceph auth get-or-create client.cinder-backup mon 'profile rbd' osd 'profile rbd pool=backups' mgr 'profile rbd pool=backups'"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "ceph create user cinder-backup", content)
        cmd = "ceph auth get-or-create client.cinder > /etc/ceph/ceph.client.cinder.keyring"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "generate keyring for cinder", content)
        cmd = "ceph auth get-or-create client.glance > /etc/ceph/ceph.client.glance.keyring"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "generate keyring for glance", content)
        cmd = "ceph auth get-or-create client.nova > /etc/ceph/ceph.client.nova.keyring"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "generate keyring for nova", content)
        cmd = "ceph auth get-or-create client.cinder-backup > /etc/ceph/ceph.client.cinder-backup.keyring"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, "generate keyring for cinder-backup", content)
        return 'ceph init pools success'

    def delete_ceph_cluster(self, ctxt):
        # 删除ceph之前检查osd有没有
        ceph_fsid=self.get_ceph_fsid(ctxt)
        if ceph_fsid:
            cmd = f"cephadm rm-cluster --force --zap-osds --fsid {ceph_fsid}"
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f"delete ceph cluster fsid={ceph_fsid}", content)
        else:
            LOG.warning(f'no fsid found, skip delete ceph cluster')
        if os.path.isdir(self.ceph_conf_dir):
            flag, content = execute.execute_command(f'rm -rf {self.ceph_conf_dir}/*')
            execute.completed(flag, f"clear {self.ceph_conf_dir}", content)
        cmd = f'crudini --set /etc/{AUTHOR_NAME}/{AIO_CONF_NAME} ceph current_node_installed_ceph false'
        flag, content = execute.execute_command(cmd)
        execute.completed(0, f"set current_node_installed_ceph flag, return_code={flag}")
        cmd = "sed -i '/ ceph-/d' /root/.ssh/authorized_keys"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f"clear ceph pub key in /root/.ssh/authorized_keys failed", content)
        return 'delete ceph cluster success'

    def get_ceph_nodes(self, ctxt):
        flag, content = execute.execute_command('ceph orch host ls -f json', shell=False, timeout=5)
        execute.completed(flag, 'ceph orch host ls', content)
        try:
            value = json.loads(content)
        except Exception as e:
            execute.completed(1, 'json load content')
        flag = 0 if isinstance(value, list) else 1
        execute.completed(flag, 'check content is list')
        return value

    def pull_ceph_image(self, ctxt):
        ceph_registry = self._get_ceph_default_registry_url()
        cmd = f'podman pull --tls-verify=false {ceph_registry}/ceph/ceph:v17'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f"pull ceph image", content)
        return flag, content

    def check_ceph_health(self, ctxt):
        flag, content = execute.execute_command('ceph health', shell=False)
        execute.completed(flag, 'check ceph health', content)
        return flag == 0

    def restart_ceph_about_container(self, ctxt):
        flag, content = execute.execute_command('docker ps -a --format "{{.Names}}"', shell=False)
        execute.completed(flag, 'docker ps', content)
        names = func.get_string_split_list(content, '\n')
        restart_names = ['nova_compute', 'cinder_volume', 'glance_api', 'nova_conductor', 'nova_libvirt', 'cinder_backup']
        for name in names:
            name = name.replace('"', '').replace("'", '')
            if name in restart_names:
                flag, content = execute.execute_command(f'docker restart {name}', shell=False)
                execute.completed(flag, f'docker restart {name}', content)
