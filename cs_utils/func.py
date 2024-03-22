import os
import ipaddress
import socket
import inspect
import logging
import urllib.request
import re

LOG = logging.getLogger(__name__)


def get_current_node_hostname():
    return socket.gethostname()


def get_dict_dict_value(value: dict, key1: str, key2: str):
    assert isinstance(value, dict), 'get_dict_dict_value input is not dict'
    if key1 in value:
        dict1 = value.get(key1)
        assert isinstance(dict1, dict), f'get_dict_dict_value key={key1} value is not dict'
    else:
        dict1 = {}
        LOG.warning(f'get_dict_dict_value key={key1} not in input dict')
    value = dict1.get(key2)
    return value


def get_string_split_list(string, split_flag=','):
    return [i.strip() for i in string.split(split_flag) if i.strip()]


def get_all_class_variables(class_obj):
    members = [attr for attr in dir(class_obj) if not callable(getattr(class_obj, attr)) and not attr.startswith("__")]
    return members


def get_basemodel_class_variable_names(class_obj) -> list:
    from pydantic import BaseModel
    if not issubclass(class_obj, BaseModel):
        raise Exception(f'{class_obj} type is not BaseModel, it is {type(class_obj)}')
    return list(vars(class_obj).get('__fields__', {}).keys())


def get_home_dir():
    return os.path.expanduser('~')


def get_user_config_dir(user_config_dir_name):
    home_dir = get_home_dir()
    user_config_dir = os.path.join(home_dir, user_config_dir_name)
    os.makedirs(user_config_dir, exist_ok=True)
    return user_config_dir


def get_python_path():
    return sys.executable


def get_current_python_share_path():
    python_path = get_python_path()
    share_path = os.path.join(python_path, '../share')
    return share_path


def get_current_system_platform():
    """
    return linux or windows
    :return:
    """
    current_platform = platform.system().lower()
    return current_platform


def check_require_pip_package(package_name, package_install_name=None):
    module = importlib.util.find_spec(package_name)
    if not module:
        package_install_name = package_install_name or package_name
        LOG.error(f"no {package_name} installed, you can use bellow install it")
        LOG.error(f"pip install {package_install_name}")
        exit(1)
    return importlib.import_module(package_name)


def get_recommended_log_path(package_name):
    platform_name = get_current_system_platform()
    if platform_name == support.Platform.linux.name:
        return f'/var/log/{package_name}.log'
    elif platform_name == support.Platform.windows.name:
        return os.path.join(get_user_config_dir(package_name), f"{package_name}.log")
    else:
        raise Exception(f'not support platform={platform_name}')


def get_tool_platform_script_path():
    current_filepath = os.path.abspath(__file__)
    platform_name = get_current_system_platform()
    debug_platform_dir = os.path.abspath(os.path.join(current_filepath, f"../../../tools/{platform_name}"))
    installed_platform_scripts_dir = os.path.join(get_current_python_share_path(), f"tools/{platform_name}")
    if os.path.isdir(debug_platform_dir):
        return debug_platform_dir
    else:
        return os.path.abspath(installed_platform_scripts_dir)


def _(s):
    return s


def get_conf_group_value(cfg_name, group_name=None):
    from oslo_config import cfg
    CONF = cfg.CONF 
    if group_name:
        value = getattr(getattr(CONF, group_name), cfg_name)
    else:
        value = getattr(CONF, cfg_name)
    return value


def set_conf_group_value(value, cfg_name, group_name=None):
    from oslo_config import cfg
    CONF = cfg.CONF 
    if group_name:
        group = getattr(CONF, group_name)
        setattr(group, cfg_name, value)
    else:
        setattr(CONF, cfg_name, value)


class FixedSizeList:
    def __init__(self, max_size):
        self.max_size = max_size
        self.items = []

    def append(self, item):
        self.items.append(item)
        if len(self.items) > self.max_size:
            self.items.pop(0)

    def __str__(self):
        return ''.join(self.items)


def get_hostname_222_ip(hostname=None):
    hostname = hostname or get_current_node_hostname()
    if '192.222.1.' in hostname:
        return hostname
    else:
        # assert len(hostname)==7, f'hostname={hostname} length is not 7'
        # assert 'host' in hostname, f'hostname={hostname} not format like hostxxx'
        # hostname_number = hostname[4:]
        # assert hostname_number.isdigit(), f'hostname={hostname} last 3 works is not digit, it is {hostname_number}'
        # ip = f'192.222.1.{int(hostname_number)}'
        # return ip
        assert re.match(r'host\d{3}$', hostname)
        n = int(hostname[4:])
        assert 1 <= n and n <= 240
        return f'192.222.1.{n}'


def get_222_ip_hostname(ip: str):
    if not ip.startswith('192.222.1.'):
        return
    ip_endwith = get_string_split_list(ip, split_flag='.')[-1]
    ip_endwith = int(ip_endwith)
    hostname = f'host{ip_endwith:03d}'
    return hostname


def find_class_functions_with_param(cls, param) -> list:
    # 获取类中所有的成员名称
    members = inspect.getmembers(cls)
    # 遍历类中的成员
    result = []
    for name, member in members:
        # 检查成员是否为函数
        if inspect.isfunction(member):
            # 获取函数的参数列表
            parameters = inspect.signature(member).parameters
            # 检查参数列表中是否包含 'ctxt' 参数
            if param in parameters:
                result.append(name)
    return result


def virsh_dump_vnc_url_to_dict(string: str):
    match = re.search(r":(\w+)@", string)
    password = match.group(1)
    match = re.search(r"@([\d.]+):", string)
    server_ip = match.group(1)
    match = re.search(r":(\d+)$", string)
    port = int(match.group(1))
    port_5900 = 5900 + int(port)
    return dict(server=server_ip, port=port_5900, password=password)


def set_simple_log(log_path):
    dirname = os.path.dirname(log_path)
    os.makedirs(dirname, exist_ok=True)
    logging.basicConfig(
        filename=log_path,  # 日志文件名
        level=logging.INFO,  # 日志级别
        format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
    )
    LOG = logging.getLogger(__name__)
    LOG.info(f'set_simple_log={log_path} ok')


def create_conf_file(file_path):
    dirname = os.path.dirname(file_path)
    os.makedirs(dirname, exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            pass
        LOG.info(f'conf_file={file_path} has create')


def convert_to_GT_str(value_in_bytes):
    giga = round(value_in_bytes / (1024 ** 3), 1)  # 转换为 G，并保留一位小数
    tera = round(value_in_bytes / (1024 ** 4), 1)  # 转换为 T，并保留一位小数
    if tera > 1:
        return f'{tera}T'
    else:
        return f'{giga}G'


class ValidIpAddress:

    @staticmethod
    def is_ip(input):
        try:
            ipaddress.ip_address(input)
            return True
        except:
            return False

    @staticmethod
    def is_cidr(input, strict=True):
        try:
            if '/' not in input:
                raise Exception(f'not / in {input}')
            ipaddress.ip_network(input, strict=strict)
            return True
        except:
            return False
    
    @staticmethod
    def ip_in_cidr(ip, cidr):
        try:
            ip = ipaddress.IPv4Address(ip)
            subnet = ipaddress.IPv4Network(cidr, strict=False)
            return ip in subnet
        except:
            return False


def get_class_var_values(class_obj):
    members = vars(class_obj)
    values = [value for key, value in members.items() if not key.startswith('__')]
    return values


def check_access_ip_not_reserved(ip: str):
    # 192.222.1.x manage
    # 192.222.12.x ceph-cluster
    # 192.222.13.x ceph-public
    # 192.222.22.x vm
    failed_start = ['192.222.1.', '192.222.12.', '192.222.13.', '192.222.22.']
    for start in failed_start:
        if ip.startswith(start):
            return False
    return True


def get_http_server_files(url):
    """
    返回http文件服务器给定下载url下的文件列表
    """
    response = urllib.request.urlopen(url)
    html = response.read().decode('utf-8')
    
    file_list = []
    lines = html.splitlines()
    for line in lines:
        if '<a href="' in line:
            start_index = line.index('<a href="') + len('<a href="')
            end_index = line.index('">', start_index)
            file_name = line[start_index:end_index]
            if not file_name.endswith('/'):
                file_list.append(file_name)
    
    return file_list


def get_http_server_one_file_download_url(url, startswith:str, endswith:str):
    file_list = get_http_server_files(url)
    files = [ 
        i for i in file_list
        if i.startswith(startswith) and i.endswith(endswith)
    ]
    if len(files) == 0:
        raise Exception(f"not find file like {startswith}*{endswith} in {url}")
    if len(files) >1:
        raise Exception(f"find multi files like {startswith}*{endswith} in {url}")
    file_url = f'{url}/{files[0]}'
    return file_url
