import os
import json
import base64
import hashlib
import logging
import traceback

from oslo_config import cfg

from cc_utils import execute, func, file, _, AUTHOR_NAME, AIO_CONF_NAME, network
from hostadmin.files import FilesDir
from hostadmin.config import CONF

LOG = logging.getLogger(__name__)


class PveEndPoint(object):
    def __init__(self):
        self.SSH_TIMEOUT=2
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.AIO_CONF_PATH = f'/etc/{AUTHOR_NAME}/{AIO_CONF_NAME}'
        self.default_root_password = CONF.ssh.root_pwd
        self.vbios_path = f'/opt/{AUTHOR_NAME}/{AUTHOR_NAME}-aio-bin/repo/bin/vbios'
        self.sysctl_conf_path = '/etc/sysctl.conf'
        self.debian_network_interfaces_path = '/etc/network/interfaces'

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

    def change_single_pve_node_network(self, ctxt, ip_mask, gateway, dns, hostname, need_restart = False, need_reboot=False):
        """
        参考资料: https://cloud.tencent.com/developer/article/2007992
        # sed -i -e 's/node009/node011/g' /etc/hostname
        # sed -i -e 's/node009/node011/g' /etc/hosts
        # sed -i -e 's/node009/node011/g' /etc/postfix/main.cf
        """
        if ip_mask:
            flag = func.ValidIpAddress.is_cidr(ip_mask, strict=False)
            execute.completed(not flag, f"check ip_mask={ip_mask} format")
        if gateway:
            flag = func.ValidIpAddress.is_ip(gateway)
            execute.completed(not flag, f"check gateway={gateway} format")
        if ip_mask and gateway:
            flag = func.ValidIpAddress.ip_in_cidr(gateway, ip_mask)
            execute.completed(not flag, f"check gateway={gateway} in cidr={ip_mask}")
        if ip_mask:
            old_ip_address = network.get_main_ip_address()
            if ip_mask != old_ip_address:
                need_restart = True
                content = file.read_file_content(self.debian_network_interfaces_path, mode='r')
                new_content = content.replace(old_ip_address, ip_mask)
                file.write_file_content(self.debian_network_interfaces_path, new_content)
                execute.completed(0, f"replace ip_address from {old_ip_address} to {ip_mask}")
        if hostname:
            current_hostnanme = func.get_current_node_hostname()
            if current_hostnanme != hostname:
                flag, content = execute.execute_command(f"sed -i '/{current_hostnanme}/d' /etc/hosts")
                flag, content = execute.execute_command(f"sed -i '/{hostname}/d' /etc/hosts")
                flag, content = execute.execute_command(f'echo "{new_ip} {hostname}.com {hostname}" >> /etc/hosts')
                execute.completed(flag, f'update hostname from {current_hostnanme} to {hostname} in /etc/hosts', content)
                flag, content = execute.execute_command(f"echo {hostname} > /etc/hostname")
                execute.completed(flag, f"set new hostname as {hostname}")
                flag, content = execute.crudini_set_config('/etc/postfix/main.cf', "", 'myhostname', f'{hostname}.com')
                execute.completed(flag, f'update myhostname to email', content)
                need_reboot = True
        if gateway:
            old_gateway = network.get_default_gateway()
            if gateway != old_gateway:
                need_restart = True
                content = file.read_file_content(self.debian_network_interfaces_path, mode='r')
                new_content = content.replace(old_gateway, gateway)
                file.write_file_content(self.debian_network_interfaces_path, new_content)
                execute.completed(0, f"replace gateway from {old_gateway} to {gateway}")
        if dns:
            flag = func.ValidIpAddress.is_ip(dns)
            execute.completed(not flag, f"check dns format")
            flag, content = execute.execute_command("sed -i '/#aio-dns/d' /etc/resolv.conf")
            flag, content = execute.execute_command(f'echo "nameserver {dns} #aio-dns" >> /etc/resolv.conf')
            execute.completed(flag, f"add dns={dns}")
        if need_restart:
            execute.completed(0, f'will restart network, please wait...', content)
            flag, content = execute.execute_command("service networking restart")
            execute.completed(flag, f'restart network', content)
        if need_reboot:
            execute.completed(0, f'now reboot -f, please wait...', content)
            flag, content = execute.execute_command("reboot -f")
            execute.completed(flag, f'reboot system', content)

    def open_ipv6_support(self, ctxt):
        """
        参考: https://www.icn.ink/pve/57.html
        查看内核也已经开启ipv6自动配置
        cat /proc/sys/net/ipv6/conf/vmbr0/accept_ra
        1
        cat /proc/sys/net/ipv6/conf/vmbr0/autoconf
        1
        查看已开启ipv6转发
        cat /proc/sys/net/ipv6/conf/vmbr0/forwarding
        1
        需要将accept_ra值改成2才能自动配置SLAAC ipv6地址
        /etc/sysctl.conf
        net.ipv6.conf.all.accept_ra=2
        net.ipv6.conf.default.accept_ra=2
        net.ipv6.conf.vmbr0.accept_ra=2
        net.ipv6.conf.all.autoconf=1
        net.ipv6.conf.default.autoconf=1
        net.ipv6.conf.vmbr0.autoconf=1"""
        flag, content = execute.execute_command('echo 1 > /proc/sys/net/ipv6/conf/vmbr0/accept_ra')
        execute.completed(flag, f'open ipv6 accept_ra', content)
        flag, content = execute.execute_command('echo 1 > /proc/sys/net/ipv6/conf/vmbr0/autoconf')
        execute.completed(flag, f'open ipv6 autoconf', content)
        flag, content = execute.execute_command('echo 1 > /proc/sys/net/ipv6/conf/vmbr0/forwarding')
        execute.completed(flag, f'open ipv6 forwarding', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.all.accept_ra', 2)
        execute.completed(flag, f'set net.ipv6.conf.all.accept_ra', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.default.accept_ra', 2)
        execute.completed(flag, f'set net.ipv6.conf.default.accept_ra', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.vmbr0.accept_ra', 2)
        execute.completed(flag, f'set net.ipv6.conf.vmbr0.accept_ra', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.all.autoconf', 1)
        execute.completed(flag, f'set net.ipv6.conf.all.autoconf', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.default.autoconf', 1)
        execute.completed(flag, f'set net.ipv6.conf.default.autoconf', content)
        flag, content = execute.crudini_set_config(self.sysctl_conf_path, "", 'net.ipv6.conf.vmbr0.autoconf', 1)
        execute.completed(flag, f'set net.ipv6.conf.vmbr0.autoconf', content)

    def repair_modify_hostname(self, ctxt):
        # https://bugxia.com/1616.html
        execute.completed(0, f'还没有实现', just_echo=True)
