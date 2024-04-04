import time
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class DiskConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.show()

    def save_config(self, button):
        group, keys = 'alist', ['default_admin_password']
        self.save_CONF_group_keys(group, keys)
        # ui.return_last(button)
        AlistConsoleView(self)
    
    def default_password_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入密码", ("white", " "), ]))
            CONF.alist.default_admin_password = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        elif len(current_value) < 4:
            edit_obj.set_caption(('header', [f"密码太短", ("white", " "), ]))
        elif len(current_value) > 20:
            edit_obj.set_caption(('header', [f"密码太长", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.alist.default_admin_password = current_value

    def update_view(self):
        widget_list = [
            urwid.Padding(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("admin用户的管理员密码", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", CONF.alist.default_admin_password, self.default_password_change_button_func), "editbx", "editfc"),
                        ]
                    ), left=8, right=10
                ),
            ),
        ]
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("额外硬盘配置", align="center"),
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
