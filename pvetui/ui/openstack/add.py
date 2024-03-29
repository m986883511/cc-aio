import os
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from pvetui import jm_data, exception
from hostadmin.rpc import rpc_client
from cs_utils import func, execute

LOG = logging.getLogger(__name__)


class AddComputeConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, button: urwid.Button):
        super().__init__(origin_view)
        self.selected_hostname = button.label[:7]
        self.ceph_config_dir = '/etc/ceph'
        self.show()

    def show(self):
        start_add_osd_view = [
            urwid.Text(f'开始将{self.selected_hostname}添加为计算节点', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_add_osd_view))
        self.need_run_cmd_list.append(f'cs-hostcli network check-network-connection {self.selected_hostname}')
        self.need_run_cmd_list.append(f'cs-hostcli ssh check-ssh-passwordless {self.selected_hostname}')
        self.need_run_cmd_list.append(f'cs-hostcli network check-kolla-interface-exist {self.selected_hostname}')
        self.need_run_cmd_list.append(f'cs-hostcli kolla add-compute-node {self.selected_hostname}')
        if os.path.exists(self.ceph_config_dir):
            self.need_run_cmd_list.append(f'cs-hostcli ssh rsync-dir-to-remote-host {self.selected_hostname} {self.ceph_config_dir}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class AddComputeNodeMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.node_buttons = []
        self.installed_nova_compute_hosts = []
        self.show()

    def open_add_view(self, button: urwid.Button):
        hostname = button.label
        pure_compute_nodes = func.get_string_split_list(CONF.openstack.pure_compute_nodes, split_flag=',')
        if hostname not in pure_compute_nodes:
            pure_compute_nodes.append(hostname)
            CONF.openstack.pure_compute_nodes = ','.join(pure_compute_nodes)
            self.save_config()
        AddComputeConsoleView(self, button)

    def save_config(self):
        group, keys = 'openstack', ['pure_compute_nodes']
        self.save_CONF_group_keys(group, keys)

    def get_installed_compute_node(self, loop=None, user_data=None):
        cmd = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && openstack compute service list -f value -c Host -c Binary'
        flag, content = execute.execute_command(cmd)
        if flag != 0:
            LOG.warning(f'get get_installed_compute_node failed, err={content}')
            return
        LOG.info(content)
        content_list = func.get_string_split_list(content, split_flag='\n')
        value = [func.get_string_split_list(i, split_flag=' ')[-1] for i in content_list if 'nova-compute' in i]
        self.installed_nova_compute_hosts = value
        LOG.info(f'installed_nova_compute_hosts={value}')
        self.update_view()

    def update_view(self, loop=None, user_data=None):
        self.node_buttons = []
        hostnames = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        control_nodes = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        hostnames.sort()
        for host in hostnames:
            if host in control_nodes:
                continue
            button_label = f'{host}'
            if host in self.installed_nova_compute_hosts:
                button_label += " (已安装)"
            self.node_buttons.append(urwid.Button(button_label, self.open_add_view, align="center"))
        if not self.node_buttons:
            self.node_buttons = [urwid.Text(f"没有已安装基础环境但不是控制节点的节点", align="center")]
        self.pile_view.widget_list = self.node_buttons

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"选择节点并添加"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_loop.set_alarm_in(1, self.get_installed_compute_node)
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
