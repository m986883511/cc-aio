import time
import uuid
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class WireguardConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.ipv4_ipv6_choose_list = []
        self.ip_types = ['ipv4', 'ipv6']
        self.ip_type_radio_buttons = []
        self.show()

    def save_config(self, button):
        group, keys = 'wireguard', ['open_flag', 'listen_port']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)

    def open_flag_change(self, obj: urwid.CheckBox, value: bool):
        CONF.wireguard.open_flag = value
        self.update_view()

    def listen_port_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.wireguard.listen_port = ''
            return
        if not current_value.isdigit():
            edit_obj.set_caption(('header', [f"存在不是数字的字符", ("white", " "), ]))
        elif int(current_value) < 10000:
            edit_obj.set_caption(('header', [f"端口号不能小于10000", ("white", " "), ]))
        elif int(current_value) > 65535:
            edit_obj.set_caption(('header', [f"端口号不能大于65535", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessKeySecret = current_value

    def update_view(self):
        widget_list = []
        widget_list.append(urwid.Padding(urwid.CheckBox('是否开启内网穿透:', state=CONF.wireguard.open_flag, on_state_change=self.open_flag_change), left=4, right=4, min_width=10))
        if CONF.wireguard.open_flag:
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("监听端口:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.listen_port, self.listen_port_change), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ))
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
                        urwid.Padding(urwid.Button("确认并保存", self.save_config, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
