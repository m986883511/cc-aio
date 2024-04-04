import time
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func, network

LOG = logging.getLogger(__name__)


class NetworkConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_config_pve_network_view = [
            urwid.Text(f'开始配置网络', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_config_pve_network_view))
        self.need_run_cmd_list.append(f'cg-hostcli pve open-ipv6-support')
        self.need_run_cmd_list.append(f'cg-hostcli pve change-single-pve-node-network --ip_mask {CONF.network.ip_cidr} --gateway {CONF.network.gateway} --dns {CONF.network.dns}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class NetworkConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.show()

    def save_config(self, button):
        group, keys = 'network', ['gateway', 'dns', 'ip_cidr']
        self.save_CONF_group_keys(group, keys)
        NetworkConsoleView(self)

    def dns_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption('')
            CONF.network.dns = '8.8.8.8'
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif not func.ValidIpAddress.is_ip(current_value):
            edit_obj.set_caption(('header', [f"格式不是ip地址!", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.network.dns = current_value

    def hostname_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            ip = func.get_hostname_map_ip()
            hostname = func.get_ip_hostname_use_end_number(ip)
            edit_obj.set_caption(('header', [f"不填将使用{hostname}", ("white", " "), ]))
            CONF.network.hostname = hostname
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif len(current_value) < 4:
            edit_obj.set_caption(('header', [f"长度不能小于4", ("white", " "), ]))
        elif len(current_value) > 12:
            edit_obj.set_caption(('header', [f"长度不能大于12", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.network.hostname = current_value

    def gateway_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"必须输入ip地址", ("white", " "), ]))
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif not func.ValidIpAddress.is_ip(current_value):
            edit_obj.set_caption(('header', [f"格式不是ip地址!", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.network.gateway = current_value

    def ip_cidr_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"必须输入ip/mask", ("white", " "), ]))
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif not func.ValidIpAddress.is_cidr(current_value, strict=False):
            edit_obj.set_caption(('header', [f"格式不是ip/mask地址!", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.network.ip_cidr = current_value

    def update_view(self):
        widget_list = [
            urwid.Padding(urwid.Text('变更主机名将立即触发重启操作, 请知悉! !', align="left"), left=8, right=10),
            urwid.Padding(urwid.Text('重启后还需要手动执行 "cs-hostcli pve repair-modify-hostname" 迁移虚拟机配置文件!', align="left"), left=8, right=10),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("主机名:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.network.hostname, self.hostname_change_button_func), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Divider(),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("IP地址 (cidr格式 比如192.168.1.55/24):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.network.ip_cidr, self.ip_cidr_change_button_func), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("默认网关:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.network.gateway, self.gateway_change_button_func), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("DNS:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.network.dns, self.dns_change_button_func), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
        ]
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("编辑基础网络", align="center"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.Button("保存并配置服务", self.save_config, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
