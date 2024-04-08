import os
import re
import json
import logging
import traceback

from oslo_config import cfg

from cc_utils import execute, func, file
from hostadmin.files import FilesDir

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HostEndPoint(object):

    def __init__(self):
        self.support_pci_types = ['gpu', 'vgpu', 'other', 'igd']
        self.pci_device_set_vfio_driver_file_path = '/etc/modprobe.d/vfio-pci.conf'
        self.module_load_vfio_pci_file_path = '/etc/modules-load.d/vfio-pci.conf'
        self.modprobe_blacklist_file_path = '/etc/modprobe.d/blacklist.conf'
        self.apt_source_list_path = '/etc/apt/sources.list'

    def get_machine_code(self, ctxt):
        return_code, content = execute.execute_command(f'atlicense -m')
        LOG.info(f'HostEndPoint get_machine_code return_code={return_code}, content={content}')
        if return_code != 0:
            raise Exception(content)
        hostname = func.get_current_node_hostname()
        return {'machine_code': content, 'hostname': hostname}

    def get_hostname(self, ctxt):
        hostname = func.get_current_node_hostname()
        return hostname
    
    def close_enterprise(self, ctxt):
        hostname = func.get_current_node_hostname()
        return hostname

    def get_ntp_servers(self, ctxt):
        # 字符问题才去掉awk的
        # cmd = "chronyc sources | grep '^^' | awk '{print $2\" (\"$1\")\"}' | sed 's/\^//g'"
        cmd = "set -o pipefail && chronyc sources | grep '^^' | sed 's/\^//g'"
        flag, out = execute.execute_command(cmd, shell=True)
        out_lines = out.split('\n')
        return out_lines

    def set_ntp_server(self, ctxt, ntp_server_ip):
        chrony_path = '/etc/chrony.conf'
        chrony_conf_content = file.read_file_content(chrony_path, mode='r')
        if ntp_server_ip in chrony_conf_content:
            execute.completed(0, f'already set ntp={ntp_server_ip}')
            return
        chrony_conf_content = file.read_file_content(FilesDir.Host.chrony_conf, mode='r')
        chrony_conf_content = chrony_conf_content.replace('localhost', ntp_server_ip)
        file.write_file_content(chrony_path, chrony_conf_content, mode='w')
        flag, content = execute.execute_command('systemctl restart chronyd', shell=False, timeout=10)
        execute.completed(flag, 'restart chronyd', content)

    def set_apt_source_use_ustc(self, ctxt):
        flag, content = execute.execute_command(f'cat {self.apt_source_list_path} |grep pvetui-flag')
        if flag == 0:
            execute.completed(0, 'already set ustc sources')
        else:
            flag, content = execute.execute_command(f'\cp {self.apt_source_list_path} /etc/apt/sources.list.bak.pvetui')
            execute.completed(flag, 'backup origin sources.list', content)
            flag, content = execute.execute_command(f'\cp {FilesDir.Host.ustc_apt_sources} /etc/apt/sources.list')
            execute.completed(flag, 'cp ustc sources.list', content)
        # close enterprise
        cmd = "sed -i 's|^deb|#deb|' /etc/apt/sources.list.d/pve-enterprise.list"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, 'close pve enterprise source', content)
        cmd = "sed -i 's|^deb|#deb|' /etc/apt/sources.list.d/ceph.list"
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, 'close pve ceph source', content)
        cmd = 'echo "deb http://mirrors.ustc.edu.cn/proxmox/debian/pve/ bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-no-sub.list'
        flag = execute.execute_command_in_popen(cmd)
        execute.completed(flag, 'add ustc subscription', content)
        flag = execute.execute_command_in_popen(f'apt update')
        execute.completed(flag, 'apt update')

    def reboot(self, ctxt):
        LOG.info('reboot server..')
        cmd = 'shutdown -r +{}'.format(CONF.shutdown_delay)
        flag, content = execute.execute_command(cmd, shell=True)
        return flag == 0

    def shutdown(self, ctxt):
        LOG.info('shutdown server..')
        cmd = 'shutdown -h +{}'.format(CONF.shutdown_delay)
        flag, content = execute.execute_command(cmd, shell=True)
        return flag == 0

    def get_intel_or_amd_cpu_type(self):
        flag, content = execute.execute_command('cat /proc/cpuinfo |grep vendor_id')
        execute.completed(flag, f'find vendor_id in cpuinfo')
        if 'amd' in content.lower():
            return 'amd'
        elif 'intel' in content.lower():
            return 'intel'
        else:
            execute.completed(1, f'not known cpu type, content={content}')

    def get_node_igd_device(self, ctxt):
        pci_devices = self.get_support_pci_devices(ctxt)
        igd_devices = pci_devices.get('igd')
        if not igd_devices:
            return {}
        igd_pci_full_ids = list(igd_devices.keys())
        if len(igd_pci_full_ids) != 1:
            execute.completed(1, f'读取到多个核显设备，不正常啊! keys={igd_pci_full_ids}')
        igd_full_pci_id = igd_pci_full_ids[0]
        this_device = igd_devices[igd_full_pci_id]
        res = {
            'name': this_device['name'],
            'full_pci_id': igd_full_pci_id,
            'main_vendor': this_device['main_vendor']
        }
        if 'rom' in this_device:
            res['rom'] = this_device['rom']
        if 'audio_rom' in this_device:
            res['audio_rom'] = this_device['audio_rom']
        all_devices = this_device['all_devices']
        audios = [
            {'vendor':value['vendor'], 'pci_id':value['pci_id'], 'name':value['long_name']}
            for value in all_devices if 'audio' in value['long_name'].lower()
        ]
        if audios:
            if len(audios) == 1:
                res['audio'] = audios[0]
            else:
                for audio in audios:
                    if audio['vendor'].startswith(res['main_vendor'][:7]):
                        res['audio']
                        break
                else:
                    execute.completed(1, f'have multi audio pci, not known which is hdmi audio, audios={audios}')
        else:
            flag, content = execute.execute_command('lspci -nn|grep -i audio', shell=True)
            if flag != 0:
                execute.completed(1, f'get audio pci')
            else:
                content_list = func.get_string_split_list(content, split_flag='\n')
                if len(content_list) == 1:
                    temp_id = content_list[0][:7]
                    temp_full_pci_id = '0000:' + temp_id if len(temp_id) == 7 else temp_id
                    audio_dict = self.nnk_analyse(temp_full_pci_id)
                    vendor = audio_dict
                    vendor_id = self._get_vendor_id(content_list[0])
                    if vendor_id:
                        audio_dict['vendor'] = vendor_id
                    res['audio'] = audio_dict
                else:
                    execute.completed(1, f'get multi audio pci, content_list={content_list}')
        return res

    def nnk_analyse(self, pci_id) -> dict:
        cmd = f'lspci -v -s {pci_id}'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'execute {cmd}', content)
        content_list = func.get_string_split_list(content, split_flag='\n')
        return_dict = {'pci_id': pci_id, 'cmd': cmd, 'error': []}
        for i in content_list:
            if pci_id[5:] in i:
                return_dict['long_name'] = i.replace(pci_id[5:], '').strip()
            if 'driver in use' in i.lower():
                return_dict['driver'] = i.split(':')[-1].strip()
            if 'iommu group' in i.lower():
                return_dict['iommu'] = i.lower().split('iommu group')[-1].strip()
            if 'error' in i.lower() or 'unable' in i.lower():
                return_dict['error'].append(i)
        return return_dict

    def _get_vendor_id(self, line):
        pattern = r"\[([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\]"
        matches = re.findall(pattern, line)
        if matches:
            return matches[0]

    def get_support_pci_devices(self, ctxt):
        def get_sub_device_dict(master_pci_id, lspci_nn_content):
            master_pci_id_prifix = master_pci_id[:-1]
            lspci_nn_content_list = func.get_string_split_list(lspci_nn_content, split_flag='\n')
            temp_return_dict = []
            for line in lspci_nn_content_list:
                if master_pci_id_prifix not in line:
                    continue
                temp_id = line.split(' ')[0]
                temp_full_pci_id = '0000:' + temp_id if len(temp_id) == 7 else temp_id
                temp_nnk_dict = self.nnk_analyse(temp_full_pci_id)
                vendor_id = self._get_vendor_id(line)
                if vendor_id:
                    temp_nnk_dict['vendor'] = vendor_id
                temp_return_dict.append(temp_nnk_dict)
            return temp_return_dict

        LOG.info('get_support_pci_devices')
        if not os.path.exists(FilesDir.Host.pci_device_id):
            execute.completed(1, 'check file exist', f'{FilesDir.Host.pci_device_id} is not exist')
        ini_dict = file.ini_file_to_dict(FilesDir.Host.pci_device_id)
        cmd = 'lspci -nn'
        flag, content = execute.execute_command(cmd, shell=True)
        execute.completed(flag, f'execute {cmd}', content)
        in_ids = [key for key in ini_dict.keys() if key in content]
        
        in_ids_dict = {i:{} for i in self.support_pci_types}
        for string in content.split('\n'):
            for i in in_ids:
                temp = {'name': ini_dict[i]['name'], 'main_vendor': i, 'manufacturer':ini_dict[i]['manufacturer']}
                if i not in string:
                    continue
                pci_id = string.split(' ')[0]
                if 'rom' in ini_dict[i]:
                    temp['rom'] = ini_dict[i]['rom']
                if 'audio_rom' in ini_dict[i]:
                    temp['audio_rom'] = ini_dict[i]['audio_rom']
                temp['all_devices'] = get_sub_device_dict(pci_id, content)
                pci_type = func.get_dict_dict_value(ini_dict, i, 'type') or 'other'
                if pci_type not in self.support_pci_types:
                    execute.completed(1, 'check pci_type support', f'pci_type={pci_type} is not support, support={self.support_pci_types}')
                pci_full_id = '0000:' + pci_id if len(pci_id) == 7 else pci_id
                in_ids_dict[pci_type][pci_full_id] = temp
            # wc 忘记这个already_in_vendors有啥用了
            already_in_vendors = []
            for pci_type in self.support_pci_types:
                already_in_vendors = already_in_vendors + list(in_ids_dict[pci_type].keys())
        return in_ids_dict

    def set_vgpu_use_which_size(self, ctxt, main_vendor, size):
        return_dict = self.get_vgpu_mdev_types(ctxt=ctxt)

        def check_vendor_and_size_return_pci_address():
            pci_address = []
            for key, value in return_dict.items():
                if main_vendor == value['main_vendor']:
                    mdev_type = value.get('mdev_type') or {}
                    mdev_type_sizes = list(mdev_type.keys())
                    if size in mdev_type_sizes:
                        pci_address.append(key)
                    else:
                        execute.completed(1, 'check vgpu size', f'{main_vendor} not have size={size}, support is {mdev_type_sizes}')
                        return pci_address
            
            flag = 0 if pci_address else 1
            support_vendor_ids = [value['main_vendor'] for key, value in return_dict.items()]
            execute.completed(flag, 'check vgpu main_vendor', f'not found device={main_vendor} in system, support is {support_vendor_ids}')
            return pci_address
        
        pci_address_list = check_vendor_and_size_return_pci_address()
        flag, content = execute.crudini_set_config(CONF.nova_compute_conf_path, 'devices', 'enabled_mdev_types', size)
        execute.completed(flag, f'set devices enabled_mdev_types as {size}', content)
        pci_address_str = ','.join(pci_address_list)
        flag, content = execute.crudini_set_config(CONF.nova_compute_conf_path, size, 'device_addresses', pci_address_str)
        execute.completed(flag, f'set pci_address_str as {pci_address_str}', content)
        flag, content = execute.execute_command('docker restart nova_compute', shell=False, timeout=30)
        execute.completed(flag, f'restart nova_compute', content)

    def get_vgpu_mdev_types(self, ctxt):
        def filter_flavor(input_string):
            filter_flavor_dict = {}
            for string in input_string.split('\n'):
                if not string.strip():
                    continue
                string = string.replace('grid', '').replace('GRID', '')
                key, value = string.split(' ', 1)
                filter_flavor_dict[key.strip()] = value.strip()
            return filter_flavor_dict

        support_pci_devices = self.get_support_pci_devices(ctxt={})
        return_dict = support_pci_devices.get('vgpu')
        for pci_id, vgpu_dict in return_dict.items():
            manufacturer = vgpu_dict['manufacturer']
            if manufacturer == 'nvidia':
                cmd = f'set -o pipefail && cd /sys/class/mdev_bus/{pci_id}/mdev_supported_types && for i in * ; do echo -n "$i "; cat $i/name ; done'
                flag, flavor_content = execute.execute_command(cmd, shell=True)
                execute.completed(flag, f'get vgpu flavor', flavor_content)
                flavor_content_dict = filter_flavor(flavor_content)
                vgpu_dict['mdev_type'] = flavor_content_dict
            elif manufacturer == 'amd':
                cmd = "set -o pipefail && cat /etc/gim_config | grep vf_num | cut -d= -f2"
                flag, out = execute.execute_command(cmd, shell=True)
                execute.completed(flag, f'get amd {pci_id} vgpu', out)
                # todo 不知道amd什么数据格式
                vgpu_dict['mdev_type'] = out
            else:
                execute.completed(1, f'no support manufacturer={manufacturer}')
        return return_dict

    def set_pci_device_use_vfio(self, ctxt, vendor: str, reset: bool, no_check: bool):
        def set_ids_to_vfio_driver_file_path(string):
            cmd = f'echo options vfio-pci ids={string} > {self.pci_device_set_vfio_driver_file_path}'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'set {string} to {self.pci_device_set_vfio_driver_file_path}', content)
        
        def module_load_vfio():
            cmd = f'echo vfio-pci > {self.module_load_vfio_pci_file_path}'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'set {self.module_load_vfio_pci_file_path}')

        def module_blacklist_nouveau():
            cmd = f'echo -e "blacklist nouveau\noptions nouveau modeset=0" > {self.modprobe_blacklist_file_path}'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'set {self.modprobe_blacklist_file_path}')

        def check_vendor():
            if ':' not in vendor:
                execute.completed(1, f'check vendor format', f'not found : in {vendor}')
            if len(vendor) != 9:
                execute.completed(1, f'check vendor length', f'{vendor} length is not 9')
            if not no_check:
                ini_dict = file.ini_file_to_dict(FilesDir.Host.pci_device_id)
                if vendor not in ini_dict:
                    execute.completed(1, f'check vendor={vendor}', f'main_vendor={vendor} is not support, check {FilesDir.Host.pci_device_id}')

        def get_device_sub_vendors():
            support_pci_devices = self.get_support_pci_devices(ctxt={})
            sub_vendors = [vendor]
            for key, value_dict in support_pci_devices.get('gpu', {}).items():
                if value_dict.get('main_vendor') == vendor:
                    for i_dict in value_dict.get('all_devices', []) or []:
                        sub_vendor = i_dict.get('vendor')
                        if sub_vendor:
                            sub_vendors.append(sub_vendor)
            sub_vendors = list(set(sub_vendors))
            return sub_vendors
        
        def set_nova_pci_device_spec():
            ven = func.get_string_split_list(vendor, split_flag=':')
            vendor_id = ven[0]
            product_id = ven[1]
            value = { "vendor_id": vendor_id, "product_id": product_id}
            value_str = json.dumps(value)
            flag, content = execute.crudini_set_config(CONF.nova_compute_conf_path, 'pci', 'device_spec', f"'{value_str}'")
            execute.completed(flag, f'set {CONF.nova_compute_conf_path} pci device_spec', content)

        check_vendor()
        module_blacklist_nouveau()
        module_load_vfio()
        set_nova_pci_device_spec()
        all_vendors = get_device_sub_vendors()
        LOG.info(f'need set {all_vendors} to {self.pci_device_set_vfio_driver_file_path}')

        cmd = f'cat {self.pci_device_set_vfio_driver_file_path}'
        flag, content = execute.execute_command(cmd, shell=True)
        if flag == 0:
            if reset:
                all_vendors_string = ','.join(all_vendors)
                set_ids_to_vfio_driver_file_path(all_vendors_string)
            else:
                origin_ids_string = content.strip().split('ids=')[-1]
                origin_ids = func.get_string_split_list(origin_ids_string)
                need_add_ids = list(set(all_vendors) - set(origin_ids))
                if not need_add_ids:
                    LOG.info(f'set_pci_device_use_vfio already set {vendor}, current is {origin_ids}')
                else:
                    current_ids = list(set(origin_ids + need_add_ids))
                    current_ids_string = ','.join(current_ids)
                    set_ids_to_vfio_driver_file_path(current_ids_string)
        else:
            if 'no such file or directory' in content.lower():
                LOG.info(f'create {self.pci_device_set_vfio_driver_file_path} and set it')
                all_vendors_string = ','.join(all_vendors)
                set_ids_to_vfio_driver_file_path(all_vendors_string)
            else:
                err = f'read {self.pci_device_set_vfio_driver_file_path} failed'
                raise Exception(err)
        
        cmd = f'cat {self.pci_device_set_vfio_driver_file_path}'
        flag, content = execute.execute_command(cmd, shell=True)
        return content

    def install_base_env(self, ctxt, host):
        current_hostname = func.get_current_node_hostname()
        if current_hostname == host:
            cmd = f'chmod +x {FilesDir.Shell.shell_dir}/*'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'chmod +x {FilesDir.Shell.shell_dir}/*', content)
            cmd = f'bash {FilesDir.Shell.install_base_env}'
            flag = execute.execute_command_in_popen(cmd, shell=True)
            execute.completed(flag, f'install base env on {host}')
        else:
            cmd = f'cc-hostcli ssh scp-dir-to-remote-host {host} {FilesDir.Shell.shell_dir} /tmp'
            flag, content = execute.execute_command(cmd, shell=True)
            execute.completed(flag, f'scp {FilesDir.Shell.shell_dir} to {host}', content)
            cmd = 'bash /tmp/shell/install_base_env.sh'
            ssh_use_which_ip = func.get_hostname_map_ip(current_hostname)
            flag = execute.execute_ssh_command_via_id_rsa_in_popen(cmd, FilesDir.SSH.id_rsa, host, ssh_use_which_ip=ssh_use_which_ip)
            execute.completed(flag, f'install base env on {host}')

    def get_cpu_model(self, ctxt):
        """
        Model name:                         AMD Ryzen 7 5800H with Radeon Graphics
        """
        flag, content = execute.execute_command(f'lscpu |grep -i "^model name:"')
        execute.completed(flag, 'get cpu model')
        content_list = func.get_string_split_list(content, ':')
        return content_list[-1]
