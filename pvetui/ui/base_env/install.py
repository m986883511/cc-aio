import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from pvetui.utils import get_other_nodes_ntp_server_config
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class InstallBaseEnvConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, selected_hostname: str):
        super().__init__(origin_view)
        self.selected_hostname = selected_hostname[:7]
        self.show()

    def show(self):
        start_install_base_env_view = [
            urwid.Text(f'开始在{self.selected_hostname}安装基础环境', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_base_env_view))
        self.need_run_cmd_list.append(f'hostcli network check-network-connection {self.selected_hostname}')
        self.need_run_cmd_list.append(f'hostcli ssh ssh-passwordless-to-host {self.selected_hostname}')
        self.need_run_cmd_list.append(f'hostcli host install-base-env --host {self.selected_hostname}')
        if self.selected_hostname not in CONF.base_env.installed_nodes:
            other_node_ntp_server_config = get_other_nodes_ntp_server_config()
            other_node_ntp_server_ip = other_node_ntp_server_config['ntp_server_ip']
            self.need_run_cmd_list.append(f'hostcli ssh ssh-run-on-remote {self.selected_hostname} "hostcli host set-ntp-server {other_node_ntp_server_ip}"')
        self.start_alarm()
        ui.top_layer.open_box(body)
    
    def task_success_callback(self):
        hostnames = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        if self.selected_hostname not in hostnames:
            hostnames.append(self.selected_hostname)
            hostnames_str = ','.join(hostnames)
            CONF.base_env.installed_nodes = hostnames_str
            group, keys = 'base_env', ['installed_nodes']
            self.origin_view.save_CONF_group_keys(group, keys)


class InstallBaseEnvView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.need_install_env_buttons = []
        self.installed_env_hosts = []
        self.original_select_nodes = []
        self.show()

    def start_install_env(self, button: urwid.Button):
        InstallBaseEnvConsoleView(self, button.label)

    def update_view(self):
        self.need_install_env_buttons = []
        original_select_nodes = CONF.base_env.all_nodes.split(',')
        original_select_nodes.sort()
        installed_env_nodes = CONF.base_env.installed_nodes.split(',')
        current_host_name = func.get_current_node_hostname()
        if current_host_name not in original_select_nodes:
            original_select_nodes = [current_host_name]
        for host in original_select_nodes:
            text = f'{host} (已安装)' if host in installed_env_nodes else host
            self.need_install_env_buttons.append(urwid.Button(text, self.start_install_env, align="center"))
        self.pile_view.widget_list = [*self.need_install_env_buttons]

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text("选择单个节点进行安装"),
                urwid.Divider(),
                urwid.Text("请选择节点"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1)
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
