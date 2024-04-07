import os
import ipaddress
import socket
import inspect
import logging
import urllib.request
import re
import requests 

from cc_utils import execute, file, func

LOG = logging.getLogger(__name__)


def analyse_debian_network_interfaces():
    content_list = file.read_file_list('/etc/network/interfaces', mode='r')
    content_list = [i.strip() for i in content_list if i.strip()]
    res_dict = {}
    for line in content_list:
        iface_net_name = ''
        if line.startswith('auto'):
            line_tmp_list = func.get_string_split_list(line, split_flag=' ')
            net_name = line_tmp_list[1]
            if net_name not in res_dict:
                res_dict[net_name] = {}
            res_dict[net_name]['auto'] = True
        elif line.startswith('iface'):
            line_tmp_list = func.get_string_split_list(line, split_flag=' ')
            net_name = line_tmp_list[1]
            if net_name not in res_dict:
                res_dict[net_name] = {}
            res_dict[net_name]['inet'] = line_tmp_list[-1]
            iface_net_name = res_dict[net_name]['inet']
        elif line.startswith('address'):
            line_tmp_list = func.get_string_split_list(line, split_flag=' ')
            res_dict[net_name]['address'] = line_tmp_list[-1]
        elif line.startswith('gateway'):
            line_tmp_list = func.get_string_split_list(line, split_flag=' ')
            res_dict[net_name]['gateway'] = line_tmp_list[-1]
    return res_dict


def get_default_gateway():
    flag, content = execute.crudini_get_config('/etc/os-release', '', "ID")
    execute.completed(flag, 'read os ID')
    if content.lower() == 'debian':
        network_dict = analyse_debian_network_interfaces()
        for key, value_dict in network_dict.items():
            if 'gateway' in value_dict:
                return value_dict['gateway']


def get_main_ip_address():
    flag, content = execute.crudini_get_config('/etc/os-release', '', "ID")
    execute.completed(flag, 'read os ID')
    if content.lower() == 'debian':
        network_dict = analyse_debian_network_interfaces()
        for key, value_dict in network_dict.items():
            if 'gateway' in value_dict:
                return value_dict['address']


def get_gateway_subnet(raise_flag=True):
    flag, content = execute.crudini_get_config('/etc/os-release', '', "ID")
    execute.completed(flag, 'read os ID')
    if flag != 0:
        return
    if content.lower() == 'debian':
        network_dict = analyse_debian_network_interfaces()
        for key, value_dict in network_dict.items():
            if 'gateway' in value_dict:
                address = value_dict['address']
                gateway = value_dict['gateway']
                subnet = ipaddress.IPv4Network(address, strict=False)
                return str(subnet)
