import time
import uuid
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class PublicIpConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.ipv4_ipv6_choose_list = []
        self.ip_types = ['ipv4', 'ipv6']
        self.ip_type_radio_buttons = []
        self.show()

    def save_config(self, button):
        group, keys = 'public_ip', ['ipv4_or_ipv6', 'use_ddns', 'accessKeyId', 'accessSecret']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)
    
    def ipv4_or_ipv6_button_change(self, obj: urwid.RadioButton, value: bool):
        if obj.label == 'ipv6':
            CONF.public_ip.ipv4_or_ipv6 = 'ipv6' if value else 'ipv4'
            self.update_view()
        
    def use_ddns_change(self, obj: urwid.CheckBox, value: bool):
        CONF.public_ip.use_ddns = value
        self.update_view()

    def use_check_robot_change(self, obj: urwid.CheckBox, value: bool):
        CONF.public_ip.use_check_robot = value
        self.update_view()

    def access_key_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessKeyId = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessKeyId = current_value

    def access_secret_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessSecret = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessSecret = current_value
    
    def feishu_webhook_uuid_change(self, edit_obj: urwid.Edit, current_value: str):
        def is_valid_uuid(text):
            try:
                uuid_obj = uuid.UUID(text)
                return str(uuid_obj) == text
            except ValueError:
                return False
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessSecret = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        elif not is_valid_uuid(current_value):
            edit_obj.set_caption(('header', [f"输入的还不是uuid", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessSecret = current_value
    
    def check_interval_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessSecret = ''
            return
        if not current_value.isdigit():
            edit_obj.set_caption(('header', [f"存在不是数字的字符", ("white", " "), ]))
        elif int(current_value) < 1:
            edit_obj.set_caption(('header', [f"输入数字不能小于1", ("white", " "), ]))
        elif int(current_value) > 60:
            edit_obj.set_caption(('header', [f"输入数字不能大于60", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessSecret = current_value

    def update_view(self):
        widget_list = []
        self.ip_type_radio_buttons = []
        self.ipv4_ipv6_choose_list = []
        for item in self.ip_types:
            flag = item == CONF.public_ip.ipv4_or_ipv6
            self.ip_type_radio_buttons.append(urwid.RadioButton(self.ipv4_ipv6_choose_list, item, state=flag, on_state_change=self.ipv4_or_ipv6_button_change))
        ip_type_column = urwid.Columns([
            urwid.Padding(urwid.Text("选择一种公网ip方式:", align="left"), left=4, right=4, min_width=10),
            *self.ip_type_radio_buttons
        ])
        widget_list.append(ip_type_column)
        widget_list.append(urwid.Padding(urwid.CheckBox('是否使用阿里云ddns:', state=CONF.public_ip.use_ddns, on_state_change=self.use_ddns_change), left=4, right=4, min_width=10))
        
        if CONF.public_ip.use_ddns:
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名accessKeyId:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.accessKeyId, self.access_key_change), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名accessSecret:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.accessSecret, self.access_secret_change), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ))
        
        widget_list.append(urwid.Padding(urwid.CheckBox('是否开启公网IP变更通知机器人:', state=CONF.public_ip.use_check_robot, on_state_change=self.use_check_robot_change), left=4, right=4, min_width=10))
        if CONF.public_ip.use_check_robot:
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("飞书WebHook UUID:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.feishu_webhook_uuid, self.feishu_webhook_uuid_change), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("检查频率(分钟):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.check_interval, self.check_interval_change), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ))
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("编辑公网ip配置", align="center"),
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
