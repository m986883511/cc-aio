import os
import json
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class NovaEndPoint(object):
    def __init__(self):
        self.default_need_change_config_list = [
            'cpu_allocation_ratio', 
            'ram_allocation_ratio', 
            'disk_allocation_ratio', 
            'vcpu_pin_set',
            'reserved_host_memory_mb'
        ]

    def get_nova_allocation_ratio_settings(self, ctxt):
        settings = {}
        try:
            nova_conf = file.ini_file_to_dict(CONF.nova_compute_conf_path, strict=False)
        except Exception as e:
            LOG.error("failed to read nova.conf! err={}, exc={}".format(str(e), traceback.format_exc()))
            return settings

        for i in self.default_need_change_config_list:
            value = func.get_dict_dict_value(nova_conf, "DEFAULT", i)
            settings[i] = value
        return settings

    def config_host_nova_settings(self, ctxt, config: dict):
        if not isinstance(config, dict):
            execute.completed(1, 'check config instance', f'config={config} is not dict')
        for key, value in config.items():
            assert isinstance(key, str), f'key={key} is not str'
            assert isinstance(value, str), f'value={value} is not str'
            flag, value = execute.crudini_set_config(CONF.nova_compute_conf_path, 'DEFAULT', key, value)
            if flag != 0:
                return False
        # restart nova_compute docker
        cmd = 'docker restart nova_compute'
        LOG.info('in config_host_nova_settings func, will restart nova_compute, wait...')
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'docker restart nova_compute', content)
        return self.get_nova_allocation_ratio_settings(ctxt={})

    def get_nova_mdev_types_settings(self, ctxt):
        settings = {}
        try:
            nova_conf = file.ini_file_to_dict(CONF.nova_compute_conf_path, strict=False)
        except Exception as e:
            LOG.error("failed to read nova.conf! err={}, exc={}".format(str(e), traceback.format_exc()))
            return settings
        enabled_mdev_types = func.get_dict_dict_value(nova_conf, 'devices', 'enabled_mdev_types') or ''
        settings['enabled_mdev_types'] = enabled_mdev_types
        if enabled_mdev_types:
            content_list = func.get_string_split_list(enabled_mdev_types)
            for i in content_list:
                mdev_types_section_name = f'mdev_{i}'
                if value := func.get_dict_dict_value(nova_conf, mdev_types_section_name, 'device_addresses') or '':
                    settings[mdev_types_section_name] = value
        return settings

    def config_nova_mdev_types_settings(self, ctxt, pci_address, mdev_type_name):
        from pve_admin import business
        original_nova_mdev_settings = business.HostEndPoint().get_vgpu_mdev_types(ctxt={})
        support_vgpu_pci_address = original_nova_mdev_settings.keys()
        if pci_address not in support_vgpu_pci_address:
            execute.completed(1, 'check pci_address', f'pci_address={pci_address} not in {support_vgpu_pci_address}')
        support_mdev_type_name = original_nova_mdev_settings[pci_address].get('mdev_type', {}).keys()
        if mdev_type_name not in support_mdev_type_name:
            execute.completed(1, 'check mdev_type_name', f'mdev_type_name={mdev_type_name} not in {support_mdev_type_name}')

        restart_flag = False
        nova_conf = file.ini_file_to_dict(CONF.nova_compute_conf_path, strict=False)
        enabled_mdev_types = func.get_dict_dict_value(nova_conf, 'devices', 'enabled_mdev_types') or ''
        if mdev_type_name not in enabled_mdev_types:
            enabled_mdev_types_list = func.get_string_split_list(enabled_mdev_types)
            enabled_mdev_types_list.append(mdev_type_name)
            enabled_mdev_types_string = ','.join(enabled_mdev_types_list)
            flag, value = execute.crudini_set_config(CONF.nova_compute_conf_path, 'devices', 'enabled_mdev_types', enabled_mdev_types_string)
            execute.completed(flag, f'enabled_mdev_types {mdev_type_name}', value)
            restart_flag = True
        else:
            LOG.info(f'{mdev_type_name} is already enabled')

        mdev_type_section_name = f'mdev_{mdev_type_name}'
        mdev_type_section_value = func.get_dict_dict_value(nova_conf, mdev_type_section_name, 'device_addresses') or ''
        if pci_address not in mdev_type_section_value:
            mdev_type_section_value_list = func.get_string_split_list(mdev_type_section_value)
            mdev_type_section_value_list.append(pci_address)
            mdev_type_section_value_string = ','.join(mdev_type_section_value_list)
            flag, value = execute.crudini_set_config(CONF.nova_compute_conf_path, mdev_type_section_name, 'device_addresses', mdev_type_section_value_string)
            execute.completed(flag, f'set {mdev_type_section_name} to {mdev_type_section_value_string}', value)
            restart_flag = True
        else:
            LOG.info(f'mdev_type_address {pci_address} is already set')

        if restart_flag:
            cmd = 'docker restart nova_compute'
            LOG.info('in config_nova_mdev_types_settings func, will restart nova_compute, wait...')
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'docker restart nova_compute', content)

        current_nova_mdev_settings = self.get_nova_mdev_types_settings(ctxt={})
        return current_nova_mdev_settings

    def get_pci_device_spec(self, ctxt):
        nova_compute_conf = file.ini_file_to_dict(CONF.nova_compute_conf_path, strict=False)
        device_spec = func.get_dict_dict_value(nova_compute_conf, 'pci', 'device_spec') or "[]"
        device_spec_list = json.loads(device_spec)
        return device_spec_list
    
    def set_pci_device_spec(self, ctxt, vendor):
        vendor_list = vendor.split(':')
        if len(vendor_list) != 2:
            execute.completed(1, 'check vendor', f'vendor={vendor} format is not correct, like 10de:xxxx')
        vendor_id, product_id = vendor_list[0], vendor_list[1]

        from pve_admin import business
        support_pci_devices = business.HostEndPoint().get_support_pci_devices(ctxt={})
        gpu_pci_devices = support_pci_devices.get('gpu')
        available_vendor_dict = {value.get('main_vendor'):value.get('name') for key, value in gpu_pci_devices.items()}
        if vendor not in available_vendor_dict.keys():
            err = f'{vendor} not in host support available_vendors={available_vendor_dict.keys()}'
            execute.completed(1, 'check vendor', err)

        nova_compute_conf = file.ini_file_to_dict(CONF.nova_compute_conf_path, strict=False)
        device_spec = func.get_dict_dict_value(nova_compute_conf, 'pci', 'device_spec') or "[]"
        device_spec_list = json.loads(device_spec)
        need_set_nova_compute_flag = False
        new_config = {"vendor_id": vendor_id, "product_id": product_id}
        if new_config not in device_spec_list:
            device_spec_list.append(new_config)
            need_set_nova_compute_flag = True
        if need_set_nova_compute_flag:
            value = json.dumps(device_spec_list)
            value = value.replace('"', '\\"')
            flag, content = execute.crudini_set_config(CONF.nova_compute_conf_path, 'pci', 'device_spec', f"'{value}'")
            execute.completed(flag, f'set nova-compute device_spec', content)
            cmd = 'docker restart nova_compute'
            LOG.info('in set_pci_passthrough_config func, will restart nova_compute, wait...')
            flag, content = execute.execute_command(cmd)
            execute.completed(flag, f'docker restart nova_compute', content)
        return self.get_pci_device_spec(ctxt={})
