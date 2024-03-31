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

from cs_utils import execute, func, file
from hostadmin.files import FilesDir

CONF = cfg.CONF
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
        self.modprobe_blacklist_file_path = '/etc/modprobe.d/blacklist.conf'
        self.apt_source_list_path = '/etc/apt/sources.list'
        self.public_ip_save_path = "/tmp/public_ip.txt"
        self.report_public_ip_script_name = 'report_public_ip_if_changed_robot.sh'

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
        flag = execute.execute_command_in_popen(f'bash /usr/local/cs/scripts/install_alist.sh install')
        execute.completed(flag, f"install alist")
        flag = execute.execute_command_in_popen(f'cd /opt/cs/alist && ./alist admin set {admin_password}')
        execute.completed(flag, f"modify alist admin password")
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

    def show_text_qrencode(self, ctxt, text):
        flag = execute.execute_command_in_popen(f'apt install qrencode -y')
        execute.completed(flag, f"apt install qrencode")
        flag = execute.execute_command_in_popen(f'qrencode -t ansiutf8 -l L {text}')
        execute.completed(flag, f"show qrencode")

    def start_or_stop_listen_public_ip_change_rebot(self, ctxt, start_or_stop):
        flag = start_or_stop in ['start', 'stop']
        execute.completed(not flag, f"check input param ipv4_or_ipv6")
        if start_or_stop == 'start':
            flag, content = execute.execute_command(f"rm -f /tmp/public_ip.txt")
            if flag == 0:
                execute.completed(flag, f"delete old record")
            flag = execute.execute_command_in_popen(f'bash /usr/local/cs/scripts/report_public_ip_if_changed_robot.sh')
            execute.completed(flag, f"start listen_public_ip_change_rebot")
            flag, content = execute.execute_command('systemctl restart cron', shell=False, timeout=10)
            execute.completed(flag, 'systemctl restart cron', content)
        else:
            flag, content = execute.execute_command(f"crontab -l")
            execute.completed(flag, 'crontab -l', content)
            LOG.error(content)
            if self.report_public_ip_script_name in content:
                cmd = f'crontab -l | grep -v {self.report_public_ip_script_name} | crontab -r'
                flag, content = execute.execute_command(cmd)
                execute.completed(flag, f'delete cron={self.report_public_ip_script_name}', content)
                flag, content = execute.execute_command('systemctl restart cron', shell=False, timeout=10)
                execute.completed(flag, 'systemctl restart cron', content)

    def delete_listen_public_ip_change_rebot(self, ctxt):
        pass
