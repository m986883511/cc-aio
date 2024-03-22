import urwid
import threading

from pve_tui.config import CONF
from pve_tui import ui, utils
from pve_tui.ui import my_widget, base_view
from cs_utils import execute, func
from pve_admin.rpc import rpc_client


class DeployCephConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.selected_name_list = func.get_string_split_list(CONF.ceph.monitor_nodes, split_flag=',')
        self.installed_ceph_nodes = self.get_ceph_mon_nodes()
        self.selected_name_str = ','.join(self.selected_name_list)
        self.compute_nodes = self.get_compute_nodes()
        self.show()

    def get_compute_nodes(self):
        control_nodes = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        pure_compute_nodes = func.get_string_split_list(CONF.openstack.pure_compute_nodes, split_flag=',')
        compute_nodes = control_nodes + pure_compute_nodes
        return compute_nodes

    def get_ceph_mon_nodes(self, loop=None, user_data=None):
        mon_nodes = []
        try:
            current_host_name = func.get_current_node_hostname()
            ceph_nodes = rpc_client('get_ceph_orch_ls', hostname=current_host_name)
            for data in ceph_nodes:
                if 'mon' != data['service_name']:
                    continue
                mon_nodes = data['placement'].get('hosts') or []
        except:
            pass
        return mon_nodes

    def show(self):
        start_deploy_ceph_view = [
            urwid.Text(f'开始在{self.selected_name_str}部署Ceph集群', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_deploy_ceph_view))
        current_hostname = func.get_current_node_hostname()
        if not self.selected_name_list:
            self.need_run_cmd_list.append(f'echo "please save ceph config first!"')
            self.need_run_cmd_list.append(f'exit 1')
        self.need_run_cmd_list.append('pve_cli ceph run-ceph-registry')
        for i, node in enumerate(self.selected_name_list):
            self.need_run_cmd_list.append(f'pve_cli network check-network-connection {node}')
            self.need_run_cmd_list.append(f'pve_cli ssh check-ssh-passwordless {node}')
            self.need_run_cmd_list.append(f'pve_cli ceph check-ceph-node-network {node}')
            self.need_run_cmd_list.append(f'pve_cli ssh ssh-run-on-remote {node} "pve_cli ceph set-ceph-registry-url {current_hostname}"')
            self.need_run_cmd_list.append(f'pve_cli ssh ssh-run-on-remote {node} "pve_cli ceph pull-ceph-image"')
            if i == 0 and not self.installed_ceph_nodes:
                cmd = f'pve_cli ceph run-install-ceph-node {node} --osd_pool_default_size {CONF.ceph.osd_pool_default_size}'
                self.need_run_cmd_list.append(cmd)
                continue
            self.need_run_cmd_list.append(f'pve_cli ssh scp-dir-to-remote-host {node} /etc/ceph /etc')
            self.need_run_cmd_list.append(f'pve_cli ceph run-add-ceph-node {node}')
        for node in self.compute_nodes:
            if node == current_hostname:
                continue
            self.need_run_cmd_list.append(f'pve_cli ssh rsync-dir-to-remote-host {node} /etc/ceph')
        self.start_alarm()
        ui.top_layer.open_box(body)

