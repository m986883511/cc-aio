import os
import base64
import hashlib
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file, _
from hostadmin.files import FilesDir

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Bond:
    access = 'mgtbond'
    mgt = 'mgtbond'
    vm = 'vmbond'
    ceph_cluster = 'cephclusterbond'
    ceph_public = 'cephpublicbond'
    ext = 'extbond'
    access_con = 'bond-mgtbond'
    mgt_con = 'bond-mgtbond'
    vm_con = 'bond-vmbond'
    ceph_cluster_con = 'bond-cephclusterbond'
    ceph_public_con = 'bond-cephpublicbond'
    ext_con = 'bond-extbond'


class Usage:
    access = 'access'
    mgt = 'manage'
    vm = 'vm'
    ceph_cluster = 'ceph-cluster'
    ceph_public = 'ceph-public'
    ext = 'external'


class BondMode:
    name = ['balance-rr','active-backup','balance-xor','broadcast','802.3ad','balance-tlb','balance-alb']

    @classmethod
    def get_mode_str(cls, number):
        number = number or 0
        number = int(number)
        if number < 0 or number > 6:
            flag = 1
        else:
            flag = 0
        execute.completed(flag, f'check bond_mode number', f'{number} should be in 0-6')
        return cls.name[number]
    
    @classmethod
    def get_mode_number(cls, mode_str):
        flag = 0 if mode_str in cls.name else 1
        execute.completed(flag, f'check bond_mode str', f'{mode_str} is not in {cls.name}')
        return cls.name.index(mode_str)


class NetworkEndPoint(object):
    def __init__(self):
        self.SSH_TIMEOUT=2
        self.SSH_PRIVATE_KEY_PATH = FilesDir.SSH.id_rsa
        self.custom_udev_file_path = '/etc/udev/rules.d/10-net-my.rules'
        self.available_usages = func.get_class_var_values(Usage)
        self.sysctl_conf_path = '/etc/sysctl.conf'

    def check_network_connection(self, ctxt, host):
        cmd = f'ping -t 1 -c 1 {host}'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'check network connection to {host}', content)
        return flag==0

    def open_pve_ipv6_support(self, ctxt):
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
    
    def change_single_pve_node_ip(self, ctxt, new_ip):
        """
        参考资料: https://cloud.tencent.com/developer/article/2007992
        # sed -i -e 's/node009/node011/g' /etc/hostname
        # sed -i -e 's/node009/node011/g' /etc/hosts
        # sed -i -e 's/node009/node011/g' /etc/postfix/main.cf
        """
        current_hostnanme = func.get_current_node_hostname()
        new_hostname = func.get_ip_hostname_use_end_number(new_ip)
        flag, content = execute.execute_command(f"sed -i '/{current_hostnanme}/d' /etc/hosts")
        execute.completed(flag, f'delete old {current_hostnanme} in /etc/hosts', content)
        flag, content = execute.execute_command(f"echo {new_hostname} >> /etc/hostname")
        execute.completed(flag, f"set new hostname as {new_hostname}")
        flag, content = execute.crudini_set_config('/etc/postfix/main.cf', "", 'myhostname', f'{new_hostname}.com')
        execute.completed(flag, f'update myhostname to email', content)
        flag, content = execute.execute_command("service networking restart")
        execute.completed(flag, f'restart network', content)


    def check_kolla_interface_exist(self, ctxt, host):
        flag, content = execute.execute_command(f"nmcli device show {Bond.vm}")
        if flag == 0:
            if 'ovs-interface' in content or 'openvswitch' in content:
                vm_bond_exist = False
            else:
                vm_bond_exist = True
        else:
            vm_bond_exist = False
        current_hostname = func.get_current_node_hostname()
        if current_hostname == host:
            cmd = f'nmcli device show {Bond.ext}'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'check {Bond.ext} on {host} exist', content)
            cmd = f'nmcli device show {Bond.mgt}'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'check {Bond.mgt} on {host} exist', content)
        else:
            cmd = f'nmcli device show {Bond.ext}'
            flag, content = execute.execute_ssh_command_via_id_rsa(cmd, self.SSH_PRIVATE_KEY_PATH, host)
            execute.completed(flag, f'check {Bond.ext} on {host} exist', content)
            cmd = f'nmcli device show {Bond.mgt}'
            flag, content = execute.execute_ssh_command_via_id_rsa(cmd, self.SSH_PRIVATE_KEY_PATH, host)
            execute.completed(flag, f'check {Bond.mgt} on {host} exist', content)
            if vm_bond_exist:
                cmd = f'nmcli device show {Bond.vm}'
                flag, content = execute.execute_ssh_command_via_id_rsa(cmd, self.SSH_PRIVATE_KEY_PATH, host)
                execute.completed(flag, f'check {Bond.vm} on {host} exist', content)

    def _get_nic_detail(self, nic):
        LOG.info(f'_get_nic_detail nic={nic}')
        flag, c0 = execute.execute_command(f'ip a s {nic}')
        execute.completed(flag, f'execute ip a s {nic}', c0)
        flag, c1 = execute.execute_command(f'ethtool {nic}')
        execute.completed(flag, f'execute ethtool {nic}', c1)
        flag, c2 = execute.execute_command(f'ethtool -i {nic}')
        execute.completed(flag, f'execute ethtool -i {nic}', c2)
        result = {}
        ipv4 = []
        ipv6 = []
        altname = []
        c0_list = func.get_string_split_list(c0, split_flag='\n')
        for i in c0_list:
            if 'link/ether' in i.lower():
                result['mac'] = func.get_string_split_list(i, split_flag=' ')[1]
            if 'altname' in i.lower():
                altname.append(func.get_string_split_list(i, split_flag=' ')[1])
        for i in c0_list:
            if 'inet ' in i.lower():
                temp = {}
                temp['ip'] = func.get_string_split_list(i, split_flag=' ')[1]
                if 'dynamic' in i:
                    temp['dynamic'] = True
                ipv4.append(temp)
            if 'inet6 ' in i.lower():
                temp = {}
                temp['ip'] = func.get_string_split_list(i, split_flag=' ')[1]
                ipv6.append(temp)
            if ' mtu ' in i.lower():
                i_list = func.get_string_split_list(i, split_flag=' ')
                mtu_index = i_list.index('mtu')
                result['mtu'] = i_list[mtu_index+1]
            if ' master 'in i:
                i_list = func.get_string_split_list(i, split_flag=' ')
                master_index = i_list.index('master')
                name = i_list[master_index+1]
                if name == 'ovs-system':
                    result['ovs'] = True
                elif 'bond' in name or 'ceph' in name:
                    result['bond'] = name
        c1_list = func.get_string_split_list(c1, split_flag='\n')
        for i in c1_list:
            if 'link detected:' in i.lower():
                result['link'] = func.get_string_split_list(i, split_flag=':')[-1]
            if 'speed:' in i.lower():
                speed = i[6:].strip()
                result['speed'] = "" if 'unknown' in speed.lower() else speed
        c2_list = func.get_string_split_list(c2, split_flag='\n')
        for i in c2_list:
            if 'driver:' in i.lower():
                result['driver'] = i[7:].strip()
        result['ipv4'] = ipv4
        result['ipv6'] = ipv6
        result['altname'] = altname
        result['name'] = nic
        # result['altname'].append(nic)
        return result
    
    def _get_original_manage_ip_mask(self):
        hostname = func.get_current_node_hostname()
        node_222_ip = func.get_hostname_map_ip(hostname)
        nic_detail = self._get_nic_detail(Bond.mgt)
        for ip in nic_detail['ipv4']:
            temp_ip = ip.get('ip') or ''
            if temp_ip.startswith(node_222_ip):
                return temp_ip
        execute.completed(1, f'not found manage ip on {hostname}!')

    def clear_usage_network(self, ctxt, usage):
        LOG.info(f'clear_usage_network usage={usage}')
        available_usages = [x for x in self.available_usages if x != Usage.mgt]
        flag = 0 if usage in available_usages else 1
        execute.completed(flag, f'check usage', f'usage must be in {available_usages}')
        nmcli_con_dict = self.get_nmcli_connection(ctxt=ctxt, output_format='dict')
        if usage == Usage.access:
            flag = 0 if Bond.access_con in nmcli_con_dict else 1
            execute.completed(flag, f'check {Bond.access_con} exist')
            manage_ip = self._get_original_manage_ip_mask()
            cmd = f'nmcli connection modify {Bond.access_con} ipv4.method manual ipv6.method ignore ipv4.addresses {manage_ip} ipv4.gateway ""'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'set {Bond.access_con} ip method as manual ip={manage_ip}', content)
            cmd = f'nmcli connection up {Bond.access_con}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'nmcli up {Bond.access_con}', content)
        elif usage == Usage.vm:
            self._delete_bond_eth(Bond.vm)
            self._delete_nic_vlan(Bond.vm_con)
            self._delete_nmcli_connection(Bond.vm_con)
        elif usage == Usage.ext:
            self._delete_bond_eth(Bond.ext)
            self._delete_nic_vlan(Bond.ext_con)
            self._delete_nmcli_connection(Bond.ext_con)
        elif usage == Usage.ceph_cluster:
            if Bond.ceph_cluster_con in nmcli_con_dict:
                self._delete_bond_eth(Bond.ceph_cluster)
                self._delete_nic_vlan(Bond.ceph_cluster_con)
                self._delete_nmcli_connection(Bond.ceph_cluster_con)
            elif Usage.ceph_cluster in nmcli_con_dict:
                self._delete_nmcli_connection(Usage.ceph_cluster)
        elif usage == Usage.ceph_public:
            if Bond.ceph_public_con in nmcli_con_dict:
                self._delete_bond_eth(Bond.ceph_public)
                self._delete_nic_vlan(Bond.ceph_public_con)
                self._delete_nmcli_connection(Bond.ceph_public_con)
            elif Usage.ceph_public in nmcli_con_dict:
                self._delete_nmcli_connection(Usage.ceph_public)
        LOG.info(f'clear usage {usage} success')
        return self.get_all_physical_nics(ctxt=ctxt)

    def get_pve_main_bridge_nics(self, ctxt, format='list'):
        # flag, content = execute.execute_command('cat /etc/network/interfaces')
        # execute.completed(flag, f'cat /etc/network/interfaces', content)
        return self._get_nic_detail('vmbr0')

    def get_all_physical_nics(self, ctxt, format='list'):
        LOG.info('get_all_physical_nics')
        assert format in ['list', 'dict'], f'format={format} is not support'
        cmd = 'find /sys/class/net -type l -not -lname "*virtual*" -printf "%f\n"'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'find physical nic in /sys/class/net', content)
        nic_list = func.get_string_split_list(content, split_flag='\n')
        nic_list.sort()
        LOG.info(f'physical nic is {nic_list}')
        nic_dict = {}
        for nic in nic_list:
            nic_dict[nic] = self._get_nic_detail(nic)
        
        bond_list = list(set([value.get('bond') for key, value in nic_dict.items() if value.get('bond')]))
        bond_dict = {}
        for bond in bond_list:
            bond_dict[bond] = self._get_nic_detail(bond)
        for key, value in nic_dict.items():
            bond = value.get('bond')
            if bond:
                value['ipv4']=bond_dict[bond]['ipv4']
                value['ipv6']=bond_dict[bond]['ipv6']
                bond_mode = self._get_bond_mode(bond)
                value['bond_mode'] = bond_mode
        # 补齐ips # 动态的不要 link-local的不要
        for key, value in nic_dict.items():
            ip_static = []
            ipv4 = value.get('ipv4')
            ipv6 = value.get('ipv6')
            for ip_dict in ipv4:
                if ip_dict.get('dynamic'):
                    continue
                if ip_dict.get('ip').endswith('/32'):
                    continue
                ip_static.append(ip_dict.get('ip'))
            for ip_dict in ipv6:
                if ip_dict.get('dynamic'):
                    continue
                if ip_dict.get('ip').startswith('fe80'):
                    continue
                ip_static.append(ip_dict.get('ip'))
            value['ip'] = ip_static
        # 补齐usage
        for key, value in nic_dict.items():
            value['usage'] = []
            if value.get('bond') == Bond.mgt:
                value['usage'].append(Usage.mgt)
                default_gateway = self._get_default_gateway(Bond.mgt_con)
                value['default_gateway'] = default_gateway
                node_222_ip = func.get_hostname_map_ip(func.get_current_node_hostname())
                for ip in value['ip']:
                    if not ip.startswith(node_222_ip):
                        value['usage'].append(Usage.access)
                        break
            elif value.get('bond') == Bond.ext:
                value['usage'].append(Usage.ext)
                all_bond = [value.get('bond') for key, value in nic_dict.items() if value.get('bond')]
                if Bond.vm not in all_bond:
                    value['usage'].append(Usage.vm)
            elif value.get('bond') == Bond.vm:
                value['usage'].append(Usage.vm)
            elif value.get('bond') == Bond.ceph_cluster:
                value['usage'].append(Usage.ceph_cluster)
            elif value.get('bond') == Bond.ceph_public:
                value['usage'].append(Usage.ceph_public)
            else:
                for ip in value['ip']:
                    if ip.startswith('192.222.13.'):
                        value['usage'].append(Usage.ceph_public)
                    elif ip.startswith('192.222.12.'):
                        value['usage'].append(Usage.ceph_cluster)

        if format == 'list':
            nic_list = [value for key, value in nic_dict.items()]
            return nic_list
        elif format == 'dict':
            return nic_dict

    def get_nmcli_connection(self, ctxt, output_format='list'):
        LOG.info('get_nmcli_connection')
        assert output_format in ['list', 'dict'], f'output_format={output_format} is not support'
        cmd  = f"nmcli con"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'get nmcli connection', content)
        content_list = func.get_string_split_list(content, split_flag='\n')
        keys = None
        result = []
        for i, line in enumerate(content_list):
            if i == 0:
                keys = func.get_string_split_list(line, split_flag=' ')
                keys = [i.lower() for i in keys]
            else:
                values = func.get_string_split_list(line, split_flag=' ')
                length = len(values)
                new_values = [' '.join(values[:length-3])]
                new_values.extend(values[length-3:])
                result.append(dict(zip(keys, new_values)))
        if output_format == 'dict':
            return_dict = {i.get('name'):i for i in result}
            return return_dict
        return result
    
    def _create_bond_connection(self, nic_list, bond_name=None, bond_mode=0, vlan=None, input_ip=None):
        LOG.info(f'_create_bond_connection nic_list={nic_list} bond_name={bond_name}')
        LOG.info(f'clear bond={bond_name} before create it')
        for nic in nic_list:
            self._delete_nic_vlan(nic)
        self._delete_nic_vlan(bond_name)
        self._delete_bond_eth(bond_name)
        nmcli_cons_dict = self.get_nmcli_connection(ctxt={}, output_format='dict')
        bond_con_name = f'bond-{bond_name}'
        if bond_con_name not in nmcli_cons_dict:
            LOG.info(f'create bond={bond_name}')
            bond_mode_str = BondMode.get_mode_str(bond_mode)
            cmd = f'nmcli con add type bond ifname {bond_name} bond.options "mode={bond_mode_str}"'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'create bond_name={bond_name}, bond_con_name={bond_con_name}', content)
        for nic in nic_list:
            cmd = f'nmcli con add type ethernet con-name {bond_name}-{nic} ifname {nic} master {bond_name}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'add eth={nic} to bond={bond_name}')
        if input_ip:
            cmd = f'nmcli connection modify {bond_con_name} ipv4.method manual ipv6.method ignore ipv4.addresses {input_ip} ipv4.gateway ""'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'set {bond_con_name} ip method as manual ip={input_ip}', content)
        else:
            cmd = f'nmcli connection modify {bond_con_name} ipv4.method disabled ipv6.method disabled'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'set {bond_con_name} ip method is disabled', content)
        for nic in nic_list:
            cmd = f'nmcli con up {bond_name}-{nic}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'up bond con={bond_name}-{nic}', content)
        cmd = f'nmcli con up {bond_con_name}'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'up bond con={bond_con_name}', content)
    
    def _create_eth_con(self, nic, input_ip, con_name=None, vlan=None, input_gateway=None):
        LOG.info(f'_create_eth_con nic={nic} input_ip={input_ip}')
        self._delete_nic_vlan(nic)
        self._delete_nic_device(nic)
        con_name = con_name or nic
        cmd = f'nmcli connection add type ethernet con-name {con_name} ifname {nic} ipv4.addr {input_ip} ipv4.method manual'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'create con={con_name} use device={nic}', content)
    
    def _get_bond_mode(self, bond_name):
        LOG.info(f'_get_bond_mode bond_name={bond_name}')
        con_name = f'bond-{bond_name}'
        cmd = f"nmcli connection show {con_name} | grep 'bond.options'"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'get con={con_name} bond mode', content)
        content_list = func.get_string_split_list(content, split_flag='=')
        bond_mode = content_list[-1]
        bond_mode_number = BondMode.get_mode_number(bond_mode)
        return str(bond_mode_number)
    
    def _get_default_gateway(self, con_name):
        LOG.info(f'_get_default_gateway con_name={con_name}')
        cmd = f'nmcli c show {con_name} |grep ipv4.gateway'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'get con={con_name} gateway', content)
        content_list = func.get_string_split_list(content, split_flag=':')
        default_gateway = content_list[-1]
        return default_gateway

    def set_usage_network(self, ctxt, usage, nic, bond_mode, input_ip, input_gateway):
        vlan = None
        LOG.info(f'set_usage_network usage={usage} nic={nic}')
        flag = 0 if usage in self.available_usages else 1
        err = f'usage={usage} must be in {self.available_usages}'
        execute.completed(flag, 'check usage', err)
        nmcli_cons = self.get_nmcli_connection(ctxt=ctxt)
        phy_nics = self.get_all_physical_nics(ctxt=ctxt, format='dict')
        bond_mode = bond_mode or 0
        nic_list = func.get_string_split_list(nic, split_flag=',')
        flag = 1 if len(nic_list) > 2 else 0
        execute.completed(flag, 'check nic count', 'not support more than 2 eths make bond')
        hostname = func.get_current_node_hostname()
        hostname_last_ip = int(hostname[4:])

        def check_nic_is_use_as_other():
            for nic in nic_list:
                nic_original_usage = phy_nics.get(nic, {}).get('usage', [])
                if nic_original_usage and usage not in nic_original_usage:
                    execute.completed(1, 'check nic usage', f'nic={nic} is already set as {nic_original_usage}, if need clear it first!')

        def get_original_usage_nics():
            temp = []
            for nic, value in phy_nics.items():
                usage_list = value.get('usage', [])
                if usage in usage_list:
                    if usage == Usage.vm:
                        if Usage.ext in usage_list:
                            continue
                    temp.append(nic)
            return temp

        original_usage_nics = get_original_usage_nics()
        if original_usage_nics and original_usage_nics != nic_list:
            execute.completed(1, 'check nic usage', f'you need clear usage={usage} on {original_usage_nics}, then config new {usage}')

        if usage == Usage.vm:
            check_nic_is_use_as_other()
            vm_ip = f'192.222.22.{hostname_last_ip}/24'
            self._create_bond_connection(nic_list, Bond.vm, bond_mode, vlan, input_ip=vm_ip)
        elif usage == Usage.ceph_public:
            check_nic_is_use_as_other()
            ceph_ip = f'192.222.13.{hostname_last_ip}/24'
            if len(nic_list) == 2:
                self._create_bond_connection(nic_list, Bond.ceph_public, bond_mode, vlan, input_ip=ceph_ip)
            else:
                self._create_eth_con(nic_list[0], ceph_ip, con_name=usage)
                cmd = f'nmcli con up {usage}'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'up {usage} con={usage}', content)
        elif usage == Usage.ceph_cluster:
            check_nic_is_use_as_other()
            ceph_ip = f'192.222.12.{hostname_last_ip}/24'
            if len(nic_list) == 2:
                self._create_bond_connection(nic_list, Bond.ceph_cluster, bond_mode, vlan, input_ip=ceph_ip)
            else:
                self._create_eth_con(nic_list[0], ceph_ip, con_name=usage)
                cmd = f'nmcli con up {usage}'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'up {usage} con={usage}', content)
        elif usage == Usage.ext:
            check_nic_is_use_as_other()
            self._create_bond_connection(nic_list, Bond.ext, bond_mode, vlan)
        elif usage == Usage.access:
            bond_name = Bond.access
            flag = 0 if func.ValidIpAddress.is_cidr(input_ip, strict=False) else 1
            execute.completed(flag, 'check input ip', f'ip={input_ip} is not format like a.b.c.d/x')
            flag = 0 if func.ValidIpAddress.is_ip(input_gateway) else 1
            execute.completed(flag, 'check input gateway', f'input_gateway={input_gateway} is not a ip')
            mgt_bond_detail = self._get_nic_detail(bond_name)
            original_222_ip = [ip_dict.get('ip') for ip_dict in mgt_bond_detail['ipv4'] if '192.222.1.' in ip_dict.get('ip')]
            flag = 0 if len(original_222_ip) == 1 else 1
            execute.completed(flag, 'get original manage ip', f'original_222_ip={original_222_ip}')
            original_222_ip = original_222_ip[0]
            cmd = f'nmcli connection modify {Bond.access_con} ipv4.addresses {original_222_ip},{input_ip} ipv4.gateway {input_gateway} ipv4.method manual'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'add {input_ip} gw={input_gateway} to {bond_name}', content)
            cmd = f'nmcli connection up {Bond.access_con}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'nmcli up {Bond.access_con}', content)
        nic_list = self.get_all_physical_nics(ctxt=ctxt)
        nic_usage_list = [data for data in nic_list if usage in data.get('usage')]
        return nic_usage_list

    def _delete_nic_vlan(self, nic_device):
        LOG.info(f'_delete_nic_vlan nic_device={nic_device}')
        nmcli_cons = self.get_nmcli_connection(ctxt={})
        for con in nmcli_cons:
            device = con.get('device') or ''
            con_name = con.get('name') or ''
            con_type = con.get('type') or ''
            if con_type == 'vlan' and f"{nic_device}." in device:
                cmd = f'nmcli c delete "{con_name}"'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'delete {nic_device} vlan device={device}', content)

    def _delete_nmcli_connection(self, con_name):
        LOG.info(f'_delete_nmcli_connection con_name={con_name}')
        nmcli_cons = self.get_nmcli_connection(ctxt={}, output_format='dict')
        if con_name in nmcli_cons:
            cmd = f'nmcli c delete "{con_name}"'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'delete con_name={con_name}', content)
    
    def _delete_nic_device(self, nic_device):
        LOG.info(f'_delete_nic_device nic_device={nic_device}')
        nmcli_cons = self.get_nmcli_connection(ctxt={})
        for con in nmcli_cons:
            con_device = con.get('device') or ''
            con_name = con.get('name') or ''
            if nic_device == con_device:
                cmd = f'nmcli c delete "{con_name}"'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'delete con_name={con_name} device={nic_device}', content)

    def _delete_bond_eth(self, bond_device):
        LOG.info(f'_delete_bond_eth bond_device={bond_device}')
        nmcli_cons = self.get_nmcli_connection(ctxt={})
        bond_con = f'bond-{bond_device}'
        has_delete_con_list = []
        for con in nmcli_cons:
            con_name = con.get('name') or ''
            con_type = con.get('type') or ''
            con_device = con.get('device') or ''
            if bond_device in con_name and con_type == 'ethernet' and con_name not in has_delete_con_list:
                cmd = f'nmcli c delete "{con_name}"'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'delete bond_device={bond_device} eth={con_device}', content)
                has_delete_con_list.append(con_name)

    def set_nic_altname(self, ctxt, origin_nic_name, new_nic_name):
        LOG.info(f'set_nic_altname origin_nic_name={origin_nic_name} new_nic_name={new_nic_name}')
        nic_dict = self.get_all_physical_nics(ctxt=ctxt)
        phy_nics = []
        old_nic_mac = None
        for key, value in nic_dict.items():
            for i in value.get('altname'):
                phy_nics.append(i)
                if i == origin_nic_name:
                    old_nic_mac = value.get('mac')
        if origin_nic_name not in phy_nics:
            execute.completed(1, f'check old_eth={origin_nic_name} in system network', f'phy_nics={phy_nics}')
        flag = 0 if old_nic_mac else 1
        execute.completed(flag, f'check new_eth={new_nic_name} not in system network')

        if os.path.isfile(self.custom_udev_file_path):
            cmd  = f"sed -i '/{old_nic_mac}/d' {self.custom_udev_file_path}"
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'altname {origin_nic_name} to {new_nic_name}', content)
            cmd  = f"sed -i '/{new_nic_name}/d' {self.custom_udev_file_path}"
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'altname {origin_nic_name} to {new_nic_name}', content)
        address = '{address}'
        content = f'SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="{old_nic_mac}", NAME="{new_nic_name}"'
        cmd  = f"echo '{content}' >> {self.custom_udev_file_path}"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'add {origin_nic_name} to {new_nic_name} to udev file', content)
        if new_nic_name in phy_nics:
            LOG.info(f'{new_nic_name} already in system network, skip config')
        else:
            cmd = f'ip link property add dev {origin_nic_name} altname {new_nic_name}'
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'altname {origin_nic_name} to {new_nic_name}', content)
        return self.get_all_physical_nics(ctxt=ctxt)
