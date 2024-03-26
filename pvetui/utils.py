import os
import logging

from cs_utils import file, func, execute
from pvetui.config import CONF, PVE_TUI_CONF_PATH

LOG = logging.getLogger(__name__)

def get_astute_version():
    flag, content = execute.execute_command('pip show astute')
    if flag == 0:
        content_list = func.get_string_split_list(content, split_flag='\n')
        for i in content_list:
            if 'version:' in i.lower():
                version =  func.get_string_split_list(i, split_flag=':')[-1]
                return version


def install_new_master_astute_package(auto_install_flag=False):
    version = get_astute_version()
    branch='.'.join(version.split('.')[0:2])
    branch = 'master' if branch == '4.999' else 'v' + branch
    url = f'http://192.222.1.150:8082/fileserver/jenkins/jenkins1/production-zed/zed-astute/{branch}/latest'
    file_url = func.get_http_server_one_file_download_url(url, startswith='astute', endswith=".tar.gz")
    file_name = func.get_string_split_list(file_url, split_flag='/')[-1]
    print(f'current version is {version}, are you sure install {file_name}?')
    if auto_install_flag:
        name = 'yes'
    else:
        name = input("if need install, please input yes: ")
    if name == 'yes':
        flag = execute.execute_command_in_popen(f'pip install {file_url}')
        execute.completed(flag, 'install astute package')
        flag = execute.execute_command_in_popen(f'systemctl restart hostrpc')
        execute.completed(flag, 'restart hostrpc')
    else:
        print(f'input is {name}, install canceled')


def show_astute_commit_msg():
    file_path = '/usr/local/astute/doc/ChangeLog'
    cmd = f'openssl enc -d -aes-256-cbc -in {file_path} -pass pass:astute -md sha256'
    if os.path.exists(file_path):
        flag = execute.execute_command_in_popen(cmd)
        print('')
        execute.completed(flag, 'show commit msg')
    else:
        print(f'{file_path} not exists')


def custom_cmd(sys_argv: list):
    cmd = sys_argv[1]
    if cmd == '--version':
        version = get_astute_version()
        print(version)
        exit()
    elif cmd == '--update':
        auto_install_flag = '-y' in sys_argv[1:]
        install_new_master_astute_package(auto_install_flag)
        exit()
    elif cmd == '--commit':
        show_astute_commit_msg()
        exit()


def get_other_nodes_ntp_server_config():
    LOG.info('reload pvetui config')
    CONF(default_config_files = [PVE_TUI_CONF_PATH])
    CONF.reload_config_files()
    installed_base_env_nodes = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
    control_nodes = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
    pure_compute_nodes = func.get_string_split_list(CONF.openstack.pure_compute_nodes, split_flag=',')
    control_nodes_ntp_server = CONF.openstack.control_nodes_ntp_server
    mgt_vip = CONF.openstack.mgt_vip
    if len(control_nodes) <= 1:
        other_node_ntp_server_ip = func.get_hostname_222_ip()
    else:
        other_node_ntp_server_ip = mgt_vip
    nodes_but_not_openstack_node = []
    for node in installed_base_env_nodes:
        if node in control_nodes:
            continue
        elif node in pure_compute_nodes:
            continue
        nodes_but_not_openstack_node.append(node)
    config = {
        'ntp_server_ip': other_node_ntp_server_ip,
        'nodes': nodes_but_not_openstack_node
    }
    LOG.info(f'other_nodes_ntp_server_config is {config}')
    return config