import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class UpdateOpenstackConfigConsole(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, button: urwid.Button):
        super().__init__(origin_view)
        self.button_label = button.label
        self.show()

    def get_all_nodes(self):
        controls = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        controls.sort()
        return controls

    def result_button_click(self, button):
        return ui.return_last(button)

    def show(self):
        view = [
            urwid.Text(f'开始{self.button_label}', align='center'),
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(view))
        self.need_run_cmd_list = self.origin_view.commands
        self.start_alarm()
        ui.top_layer.open_box(body)


class UpdateOpenstackConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.date = {
            '更新控制节点集群的vip地址': self.update_vip,
            '更新计算资源超分和保留配置': self.update_nova_compute,
            '更新业务和外部网络VLAN配置': self.update_vlan,
            '更新外部NTP时钟源的地址': self.update_ntp,
        }
        self.commands = ['ping localhost -c 2']
        self.control_nodes = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        self.compute_nodes = self.get_compute_nodes()
        self.kolla_generate_cmd = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && kolla-generate'
        self.show()
    
    def get_compute_nodes(self):
        pure_compute_nodes = func.get_string_split_list(CONF.openstack.pure_compute_nodes, split_flag=',')
        compute_nodes = list(set(self.control_nodes + pure_compute_nodes))
        return compute_nodes

    def update_vip(self, button):
        control_nodes_string = ','.join(self.control_nodes)
        cmd2 = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && kolla-ansible deploy -i {self.ansible_hosts} -t nova,cinder,neutron,glance,skyline'
        self.commands = [self.kolla_generate_cmd, cmd2]
        UpdateOpenstackConfigConsole(self, button)

    def update_nova_compute(self, button):
        cmd2 = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && kolla-ansible genconfig -i {self.ansible_hosts} --tags nova'
        self.commands = [self.kolla_generate_cmd, cmd2]
        for node in self.compute_nodes:
            self.commands.append(f'hostcli ssh ssh-run-on-remote {node} "docker restart nova_compute"')
        UpdateOpenstackConfigConsole(self, button)

    def update_vlan(self, button):
        cmd2 = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && kolla-ansible deploy -i {self.ansible_hosts} -t openvswitch'
        self.commands = [self.kolla_generate_cmd, cmd2]
        UpdateOpenstackConfigConsole(self, button)

    def update_ntp(self, button):
        cmd2 = f'eval "$(conda shell.bash hook)" && source {self.kolla_rc_path} && kolla-ansible deploy -i {self.ansible_hosts} -t common'
        cmd3 = '/usr/bin/python /usr/local/astute/scripts/set-ntp.py'
        self.commands = [self.kolla_generate_cmd, cmd2, cmd3]
        UpdateOpenstackConfigConsole(self, button)

    def update_view(self):
        buttons = [
            urwid.Padding(urwid.Button(key, align='center', on_press=value), align="center", left=1, right=1)
            for key, value in self.date.items()
        ]
        self.pile_view.widget_list = buttons

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"更新OpenStack配置"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
