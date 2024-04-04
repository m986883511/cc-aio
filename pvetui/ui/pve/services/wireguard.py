import os
import time
import uuid
import logging
import ipaddress

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func, file

LOG = logging.getLogger(__name__)

class WireguardConfigConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_install_wireguard_view = [
            urwid.Text('开始配置wireguard服务', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_wireguard_view))
        start_or_stop = 'start' if CONF.wireguard.open_flag else 'stop'
        self.need_run_cmd_list.append(f'cg-hostcli service start-or-stop-wireguard {start_or_stop}')
        if start_or_stop == 'start':
            self.need_run_cmd_list.append(f'cg-hostcli service update-wireguard-service')
        self.start_alarm()
        ui.top_layer.open_box(body)


class RunCmdConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, des='开始执行', cmd=None, cmds=None):
        super().__init__(origin_view)
        self.des = des
        self.cmds = []
        if cmd:
            self.cmds.append(cmd)
        if cmds:
            self.cmds.extend(cmds)
        self.show()

    def show(self):
        start_install_alist_view = [
            urwid.Text(self.des, align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_alist_view))
        self.need_run_cmd_list.extend(self.cmds)
        self.start_alarm()
        ui.top_layer.open_box(body)


class WireguardConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.ipv4_ipv6_choose_list = []
        self.ip_types = ['ipv4', 'ipv6']
        self.ip_type_radio_buttons = []
        self.wireguard_conf_path = '/etc/wireguard/wg0.conf'
        self.added_clients = self.get_added_clients()
        self.new_client_name = ""
        self.show()

    def save_config(self, button):
        group, keys = 'wireguard', ['open_flag', 'server_port', 'subnet']
        self.save_CONF_group_keys(group, keys)
        # ui.return_last(button)
        WireguardConfigConsoleView(self)

    def open_flag_change(self, obj: urwid.CheckBox, value: bool):
        CONF.wireguard.open_flag = value
        self.update_view()

    def new_client_text_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            self.new_client_name = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        elif len(current_value) > 15:
            edit_obj.set_caption(('header', [f"最大长度不能超过15", ("white", " "), ]))
        elif current_value in self.added_clients:
            edit_obj.set_caption(('header', [f"与已有clients重复了", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            self.new_client_name = current_value

    def server_port_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.wireguard.server_port = ''
            return
        if not current_value.isdigit():
            edit_obj.set_caption(('header', [f"存在不是数字的字符", ("white", " "), ]))
        elif int(current_value) < 10000:
            edit_obj.set_caption(('header', [f"端口号不能小于10000", ("white", " "), ]))
        elif int(current_value) > 65535:
            edit_obj.set_caption(('header', [f"端口号不能大于65535", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.wireguard.server_port = current_value

    def subnet_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.wireguard.subnet = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        elif not func.ValidIpAddress.is_cidr(current_value, strict=False):
            edit_obj.set_caption(('header', [f"不是cidr格式", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            subnet = ipaddress.IPv4Network(current_value, strict=False)
            CONF.wireguard.subnet = str(subnet)

    def get_added_clients(self):
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
    
    def delete_cilent(self, button: urwid.Button, client_name):
        RunCmdConsoleView(self, des='删除客户端', cmd=f'cg-hostcli service add-or-remove-wireguard-client remove {client_name}')

    def show_cilent(self, button, client_name):
        path = f'/etc/cg/wireguard/wg0-client-{client_name}.conf'
        RunCmdConsoleView(self, '显示客户端', cmd=f'cg-hostcli service show-qrencode --path {path}')

    def new_client_click(self, button):
        if not self.new_client_name:
             self.note_msg = '请输入新的客户端名称再添加'
             return
        client_name = self.new_client_name
        self.new_client_name= ''
        RunCmdConsoleView(self, des='创建新的客户端连接', cmd=f'cg-hostcli service add-or-remove-wireguard-client add {client_name}')

    def update_view(self):
        widget_list = []
        widget_list.append(urwid.Padding(urwid.CheckBox('是否开启内网穿透:', state=CONF.wireguard.open_flag, on_state_change=self.open_flag_change), left=4, right=4, min_width=10))
        if CONF.wireguard.open_flag:
            widget_list.append(urwid.Divider())
            widget_list.append(urwid.Padding(
                urwid.Columns([
                        urwid.Text("服务监听端口:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.server_port, self.server_port_change), "editbx", "editfc"),
                ]), left=4, right=10))
            widget_list.append(urwid.Padding(
                urwid.Columns([
                        urwid.Text("客户端默认允许访问的网络(cidr格式):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.subnet, self.subnet_change), "editbx", "editfc"),
                ]), left=4, right=10))
            widget_list.append(urwid.Divider())
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("添加新的客户端:", align="left"),
                        urwid.Columns([
                            urwid.AttrMap(my_widget.TextEdit("", self.new_client_name, self.new_client_text_change), "editbx", "editfc"),
                            urwid.Button("开始添加", self.new_client_click, align="center"), 
                        ])
                    ]
                ), left=4, right=10
            ))
            widget_list.append(urwid.Divider())
            widget_list.append(urwid.Padding(urwid.Text("已添加的客户端:", align="left"), left=4, right=4, min_width=10))
            self.added_clients = self.get_added_clients()
            LOG.info(f'self.added_clients={self.added_clients}')
            for client in self.added_clients:
                widget_list.append(urwid.Padding(
                    urwid.GridFlow([
                            urwid.Text(f"名称: {client}", align="left"), 
                            urwid.Button("显示", self.show_cilent, align="center", user_data=client), 
                            urwid.Button("刪除", self.delete_cilent, align="center", user_data=client),
                            urwid.Divider()
                    ], 20,3,1,"left"), left=8, right=10, min_width=10))
        else:
            widget_list.append(urwid.Padding(urwid.Text("不开启就是卸载wireguard服务, 所有已创建的客户端链接将丢失!", align="left"), left=4, right=10, min_width=10))
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("编辑内网穿透配置", align="center"),
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
