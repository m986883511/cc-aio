import time
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
        self.show()

    def save_config(self, button):
        group, keys = 'wireguard', ['default_share_path', 'default_user', 'default_password']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)
    
    def default_share_path_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入路径", ("white", " "), ]))
            CONF.wireguard.default_share_path = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif not os.path.isabs(current_value):
            edit_obj.set_caption(('header', [f"不是绝对地址", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.wireguard.default_share_path = current_value

    def default_user_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入用户", ("white", " "), ]))
            CONF.wireguard.default_user = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif len(current_value) < 2:
            edit_obj.set_caption(('header', [f"用户名太短", ("white", " "), ]))
        elif len(current_value) > 10:
            edit_obj.set_caption(('header', [f"用户名太长", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.wireguard.default_user = current_value
    
    def default_password_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入密码", ("white", " "), ]))
            CONF.wireguard.default_password = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif len(current_value) < 4:
            edit_obj.set_caption(('header', [f"密码太短", ("white", " "), ]))
        elif len(current_value) > 20:
            edit_obj.set_caption(('header', [f"密码太长", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.wireguard.default_password = current_value

    def show(self):
        body = urwid.Pile(
            [
                urwid.Text("编辑smaba配置", align="center"),
                urwid.Divider(),
                urwid.Padding(
                    urwid.Padding(
                        urwid.Columns(
                            [
                                urwid.Text("共享目录", align="left"),
                                urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.default_share_path, self.default_share_path_change_button_func), "editbx", "editfc"),
                            ]
                        ), left=8, right=10
                    ),
                ),
                urwid.Padding(
                    urwid.Padding(
                        urwid.Columns(
                            [
                                urwid.Text("samba服务用户", align="left"),
                                urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.default_user, self.default_user_change_button_func), "editbx", "editfc"),
                            ]
                        ), left=8, right=10
                    ),
                ),
                urwid.Padding(
                    urwid.Padding(
                        urwid.Columns(
                            [
                                urwid.Text("samba服务密码", align="left"),
                                urwid.AttrMap(my_widget.TextEdit("", CONF.wireguard.default_password, self.default_password_change_button_func), "editbx", "editfc"),
                            ]
                        ), left=8, right=10
                    ),
                ),
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
