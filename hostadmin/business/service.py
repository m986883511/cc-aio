import os
import re
import json
import time
import logging
import traceback
import urllib
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

from oslo_config import cfg
from crontab import CronTab

from cc_utils import execute, func, file, AIO_CONF_NAME, network, Author
from hostadmin.files import FilesDir
from hostadmin.config import AUTHOR_SCRIPTS_DIR, CONF

LOG = logging.getLogger(__name__)


class HTTPServerV6(HTTPServer):
    address_family = socket.AF_INET6


class TestPublicIpHttpHandler(BaseHTTPRequestHandler):
    def _response(self, path, args):
        code=200
        value = '访问成功! 测试成功! 服务立即退出!\n'*10
        self.send_response(code)
        self.send_header('Content-type', 'text/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(value.encode())
        exit(0)
    
    def do_GET(self):
        path, args=urllib.parse.splitquery(self.path)
        self._response(path, args)

    def do_POST(self):
        args = self.rfile.read(int(self.headers['content-length'])).decode("utf-8")
        self._response(self.path, args)


class ServiceEndPoint(object):
    def __init__(self):
        self.support_pci_types = ['gpu', 'vgpu', 'other']
        self.pci_device_set_vfio_driver_file_path = '/etc/modprobe.d/vfio-pci.conf'
        self.module_load_vfio_pci_file_path = '/etc/modules-load.d/vfio-pci.conf'
        self.apt_source_list_path = '/etc/apt/sources.list'
        self.public_ip_save_path = "/tmp/public_ip.txt"
        self.report_public_ip_script_name = 'report_public_ip_if_changed_robot.sh'
        self.aliyun_ddns_script = 'aliyun-ddns.py'
        self.wireguard_script = 'wireguard.sh'
        self.wireguard_conf_path = '/etc/wireguard/wg0.conf'
        self.wireguard_script_path = os.path.join(AUTHOR_SCRIPTS_DIR, self.wireguard_script)
        self.wireguard_params_path = '/etc/wireguard/params'
        self.cc_doc_path = f'/usr/local/{Author.name}/doc'
        self.pvetui_conf_path = f'/etc/{Author.name}/{AIO_CONF_NAME}'
        self.create_local_alist_storage_py = 'create-local-alist-storage.py'

    def install_alist(self, ctxt):
        return_code, content = execute.execute_command(f'atlicense -m')
        LOG.info(f'HostEndPoint get_machine_code return_code={return_code}, content={content}')
        if return_code != 0:
            raise Exception(content)
        hostname = func.get_current_node_hostname()
        return {'machine_code': content, 'hostname': hostname}
    
    def create_samba_service(self, ctxt, share_path, samba_user_password):
        flag = execute.execute_command_in_popen(f'apt install samba samba-common -y')
        execute.completed(flag, f"apt install samba")
        # create linux samba user
        flag, content = execute.execute_command(f'cat /etc/group')
        execute.completed(flag, f"cat /etc/group")
        if 'sambashare:' in content:
            execute.completed(0, f"already created sambashare linux group")
        else:
            flag, content = execute.execute_command(f'groupadd sambashare')
            execute.completed(flag, f"groupadd sambashare")
        flag, content = execute.execute_command(f'cat /etc/passwd')
        execute.completed(flag, f"cat /etc/passwd")
        if 'samba:' in content:
            execute.completed(0, f"already create samba linux user")
        else:
            flag, content = execute.execute_command(f'useradd -g sambashare -M samba')
            execute.completed(flag, f"create samba linux user")
        flag, content = execute.execute_command(f'mkdir -p {share_path}')
        execute.completed(flag, f"mkdir smb share path={share_path}")
        flag, content = execute.execute_command(f'chown -R samba:sambashare {share_path}')
        execute.completed(flag, f"chown share_path={share_path}")
        # create samba service samba user
        flag, content = execute.execute_command(f'pdbedit -L')
        execute.completed(flag, f"list samba service users")
        if 'samba:' in content:
            execute.completed(0, f"samba service already have samba user")
            flag, content = execute.execute_command(f'smbpasswd -x samba')
            execute.completed(flag, f"delete old samba service samba user")
        flag, content = execute.execute_command(f'(echo {samba_user_password}; echo {samba_user_password}) | smbpasswd -s -a samba')
        execute.completed(flag, f"create samba service user=samba")
        flag, content = execute.execute_command(f'cp -r /opt/{Author.name}/{Author.name}-aio/gift/* {share_path}')
        execute.completed(flag, f"copy chaochao gift")
        md_file_names = [file_name for file_name in os.listdir(self.cc_doc_path) if '.md' in file_name]
        pve_ip_cidr = network.get_main_ip_address()
        pve_ip = func.get_string_split_list(pve_ip_cidr, split_flag='/')[0]
        for md_name in md_file_names:
            content = file.read_file_content(os.path.join(self.cc_doc_path, md_name), mode='r')
            content = content.replace("YOUR_PVE_ADDRESS", pve_ip)
            file.write_file_content(f'{share_path}/{Author.gift_name}/{md_name}', content)
        flag, content = execute.execute_command(f'chown -R samba:sambashare {share_path}')
        execute.completed(flag, f"chown share_path={share_path}")
        # 生效配置文件 重启smbd服务
        smb_conf_path = '/etc/samba/smb.conf'
        smb_conf_content = file.read_file_content(FilesDir.Host.smb_conf, mode='r')
        smb_conf_content = smb_conf_content.replace('SMB_SHARE_PATH', share_path)
        smb_conf_content = smb_conf_content.replace('PVE_HOSTNAME', func.get_current_node_hostname())
        file.write_file_content(smb_conf_path, smb_conf_content, mode='w')
        flag, content = execute.execute_command('systemctl restart smbd', shell=False, timeout=10)
        execute.completed(flag, 'restart smbd service', content)
        flag, content = execute.execute_command('systemctl enable smbd', shell=False, timeout=10)
        execute.completed(flag, 'systemctl enable smbd', content)

    def create_alist_service(self, ctxt, admin_password):
        flag = execute.execute_command_in_popen(f'apt install net-tools -y')
        execute.completed(flag, f"apt install net-tools")
        flag = execute.execute_command_in_popen(f'bash /usr/local/{Author.name}/scripts/install_alist.sh install')
        execute.completed(flag, f"install alist")
        flag, content = execute.execute_command(f'sleep 2')
        execute.completed(flag, f"wait 2 seconds", content)
        flag = execute.execute_command_in_popen(f'cd /opt/{Author.name}/alist && ./alist admin set {admin_password}')
        execute.completed(flag, f"modify alist admin password")
        path = os.path.join(AUTHOR_SCRIPTS_DIR, self.create_local_alist_storage_py)
        flag, content = execute.execute_command(f'sleep 2')
        execute.completed(flag, f"wait 2 seconds", content)
        flag = execute.execute_command_in_popen(f'python3 {path}')
        execute.completed(flag, 'create-local-alist-storage')
        flag, content = execute.execute_command(f'sleep 1')
        execute.completed(flag, f"wait 1 second", content)
        flag, content = execute.execute_command('systemctl restart alist', shell=False, timeout=10)
        execute.completed(flag, 'restart alist service', content)
        flag, content = execute.execute_command('systemctl enable alist', shell=False, timeout=10)
        execute.completed(flag, 'systemctl enable alist', content)

    def get_hostname(self, ctxt):
        hostname = func.get_current_node_hostname()
        return hostname

    def create_block_simple_api_service(self, ctxt, bind_port):
        start_time= time.perf_counter()
        httpd = HTTPServerV6(('::', bind_port), TestPublicIpHttpHandler)
        httpd.serve_forever()
        end_time = time.perf_counter()
        if end_time - start_time < 1:
            execute.completed(1, f"run too short! create block simple api service")

    def show_qrencode(self, ctxt, text, path):
        flag = execute.execute_command_in_popen(f'apt install qrencode -y')
        execute.completed(flag, f"apt install qrencode")
        if text:
            flag = execute.execute_command_in_popen(f'qrencode -t ansiutf8 -l L {text}')
            execute.completed(flag, f"show text={text} qrencode")
        if path:
            flag = os.path.isfile(path)
            execute.completed(not flag, f"check path={path} isfile")
            flag = execute.execute_command_in_popen(f'qrencode -t ansiutf8 -l L < {path}')
            execute.completed(flag, f"show path={path} qrencode")

    def start_or_stop_listen_public_ip_change_rebot(self, ctxt, start_or_stop):
        flag = start_or_stop in ['start', 'stop']
        execute.completed(not flag, f"check input param ipv4_or_ipv6")
        my_cron = CronTab(user='root')
        exist_task = False
        exist_job = None
        for job in my_cron:
            if self.report_public_ip_script_name in job.command:
                exist_job = job
                exist_task = True
        if start_or_stop == 'start':
            flag, content = execute.execute_command(f"rm -f /tmp/public_ip.txt")
            if flag == 0:
                execute.completed(flag, f"delete old record")
            flag, content = execute.execute_command(f'bash /usr/local/{Author.name}/scripts/report_public_ip_if_changed_robot.sh')
            execute.completed(flag, f"start listen_public_ip_change_rebot", content)
            flag, content = execute.execute_command('systemctl restart cron', shell=False, timeout=10)
            execute.completed(flag, 'systemctl restart cron', content)
        else:
            if exist_job:
                my_cron.remove(exist_job)
                my_cron.write()
                execute.completed(0, 'remove listen_public_ip_robot task')
            else:
                execute.completed(0, 'already no listen_public_ip_robot task, stop')

    def start_or_stop_aliyun_ddns(self, ctxt, start_or_stop):
        flag = start_or_stop in ['start', 'stop']
        execute.completed(not flag, f"check input param ipv4_or_ipv6")
        my_cron = CronTab(user='root')
        path = os.path.join(AUTHOR_SCRIPTS_DIR, self.aliyun_ddns_script)
        command = f'python3 {path}'
        exist_task = False
        exist_job = None
        for job in my_cron:
            if job.command == command:
                exist_job = job
                exist_task = True
        if start_or_stop == 'start':
            if not exist_task:
                job = my_cron.new(command=command)
                job.minute.every(1)
                my_cron.write()
        else:
            if exist_job:
                my_cron.remove(exist_job)
                my_cron.write()
                execute.completed(0, 'remove ddns task')
            else:
                execute.completed(0, 'already no ddns task, stop')

    def start_or_stop_wireguard(self, ctxt, start_or_stop):
        flag = start_or_stop in ['start', 'stop']
        execute.completed(not flag, f"check input param ipv4_or_ipv6")
        flag = os.path.exists(self.wireguard_script_path)
        execute.completed(not flag, f"check script_path={self.wireguard_script_path} exist")
        if start_or_stop == 'start':
            if os.path.exists(self.wireguard_params_path):
                execute.completed(0, 'installed wireguard')
            else:
                flag = execute.execute_command_in_popen(f'bash {self.wireguard_script_path}')
                execute.completed(flag, 'install wireguard')
        else:
            if os.path.exists(self.wireguard_params_path):
                cmd = f"export MENU_OPTION=4 && export REMOVE=y && bash {self.wireguard_script_path}"
                flag = execute.execute_command_in_popen(cmd)
                execute.completed(flag, 'uninstall wireguard')
    
    def get_wireguard_added_clients(self) -> list:
        clients = []
        if os.path.exists(self.wireguard_conf_path):
            content = file.read_file_content(self.wireguard_conf_path, mode='r')
            content_list = func.get_string_split_list(content, split_flag='\n')
            for i in content_list:
                if i.startswith('### Client'):
                    LOG.info(f'i={i}')
                    name = i[10:].strip()
                    if name:
                        clients.append(name)
        return clients

    def add_or_remove_wireguard_client(self, ctxt, add_or_remove, client_name):
        flag = add_or_remove in ['add', 'remove']
        execute.completed(not flag, f"check input param add_or_remove")
        if not os.path.exists(self.wireguard_params_path):
            execute.completed(1, 'check wireguard need installed')
            return
        added_clients = self.get_wireguard_added_clients()
        if add_or_remove == 'add':
            flag = client_name in added_clients
            execute.completed(flag, f"client_name={client_name} already exist, can not add!")
            cmd = f"export MENU_OPTION=1 && export CLIENT_NAME={client_name} && bash {self.wireguard_script_path}"
            flag = execute.execute_command_in_popen(cmd)
            execute.completed(flag, f'add wireguard client={client_name}')
        else:
            flag = client_name not in added_clients
            execute.completed(flag, f"client_name={client_name} not exist, can not remove!")
            index = added_clients.index(client_name) + 1
            cmd = f"export MENU_OPTION=3 && export CLIENT_NUMBER={index} && bash {self.wireguard_script_path}"
            flag = execute.execute_command_in_popen(cmd)
            execute.completed(flag, f'remove wireguard client={client_name}')

    def update_wireguard_service(self, ctxt):
        if not os.path.exists(self.wireguard_params_path):
            execute.completed(0, 'wireguard not installed, no need update')
            return
        pve_conf_dict = file.ini_file_to_dict(self.pvetui_conf_path)
        use_ddns = pve_conf_dict.get('public_ip', {}).get('use_ddns') or ''
        use_ddns = use_ddns.lower() == 'true'
        if use_ddns:
            domain = pve_conf_dict.get('public_ip', {}).get('domain') or ''
            rr = pve_conf_dict.get('public_ip', {}).get('rr') or ''
            public_ip = f'{rr}.{domain}'
        else:
            public_ip = file.read_file_content(self.public_ip_save_path, mode='r')
            public_ip = public_ip.strip()
        server_port = pve_conf_dict.get('wireguard', {}).get('server_port') or ''
        if not public_ip:
            execute.completed(1, 'get public_ip')
        if not server_port:
            execute.completed(1, 'get server_port')
        flag, param_public_ip = execute.crudini_get_config(self.wireguard_params_path, '', 'SERVER_PUB_IP')
        execute.completed(flag, 'read param_public_ip')
        flag, param_server_port = execute.crudini_get_config(self.wireguard_params_path, '', 'SERVER_PORT')
        execute.completed(flag, 'read param_server_port')
        change_flag = False
        if param_public_ip != public_ip:
            flag, content = execute.crudini_set_config(self.wireguard_params_path, '', 'SERVER_PUB_IP', public_ip)
            execute.completed(flag, f'set SERVER_PUB_IP from {param_public_ip} to {public_ip}')
            change_flag = True
        if param_server_port != server_port:
            flag, content = execute.crudini_set_config(self.wireguard_params_path, '', 'SERVER_PORT', server_port)
            execute.completed(flag, f'set params SERVER_PORT from {param_server_port} to {server_port}')
            flag, content = execute.crudini_set_config(self.wireguard_conf_path, 'Interface', 'ListenPort', server_port)
            execute.completed(flag, f'set wg0.conf SERVER_PORT from {param_server_port} to {server_port}')
            change_flag = True
        if change_flag:
            flag, content = execute.execute_command('systemctl restart wg-quick@wg0.service')
            execute.completed(flag, f'systemctl restart wg-quick@wg0.service')
