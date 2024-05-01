import os
import logging

from cc_utils import execute, func, AUTHOR_NAME
from pvetui.utils import get_other_nodes_ntp_server_config

LOG = logging.getLogger(__name__)

class SetNtpTask:
    def __init__(self):
        self.other_nodes_ntp_server_config = get_other_nodes_ntp_server_config()
        self.other_node_ntp_server_ip = self.other_nodes_ntp_server_config['ntp_server_ip']
        self.nodes_but_not_openstack_node = self.other_nodes_ntp_server_config['nodes']

    def print_and_log_info(self, msg):
        print(msg)
        LOG.info(msg)

    def check_ntp_ip_ping(self):
        flag, content = execute.execute_command(f'ping {self.other_node_ntp_server_ip} -c 1 -w 1')
        execute.completed(flag, f'ping other_node_ntp_server_ip={self.other_node_ntp_server_ip}', content, raise_flag=False)
        self.print_and_log_info(f'ping other_node_ntp_server_ip={self.other_node_ntp_server_ip} ok')

    def check_network_connection(self):
        for node in self.nodes_but_not_openstack_node:
            flag, content = execute.execute_command(f'cc-hostcli network check-network-connection {node}')
            execute.completed(flag, f'check {node} network connection', content)
            flag, content = execute.execute_command(f'cc-hostcli ssh check-ssh-passwordless {node}')
            execute.completed(flag, f'check {node} ssh passwordless', content)
        self.print_and_log_info(f'check nodes_but_not_openstack_node network connection ok')

    def set_ntp(self):
        for node in self.nodes_but_not_openstack_node:
            flag, content = execute.execute_command(f'cc-hostcli ssh ssh-run-on-remote {node} "cc-hostcli host set-ntp-server {self.other_node_ntp_server_ip}"')
            execute.completed(flag, f'set {node} ntp_server={self.other_node_ntp_server_ip}', content)
        self.print_and_log_info(f'set nodes_but_not_openstack_node network ntp ok')

    def run(self):
        self.check_ntp_ip_ping()
        self.check_network_connection()
        self.set_ntp()


if __name__ == "__main__":
    os.environ['IN_CLICK'] = 'True'
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/script.log')
    LOG.info('--------- set_ntp start ---------')
    SetNtpTask().run()
    LOG.info('--------- set_ntp end ---------')
