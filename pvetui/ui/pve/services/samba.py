import time
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cc_utils import execute, func

LOG = logging.getLogger(__name__)


class SambaConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_install_samba_view = [
            urwid.Text(f'开始配置samba服务', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_samba_view))
        self.need_run_cmd_list.append(f'cc-hostcli service create-samba-service {CONF.samba.default_share_path} {CONF.samba.samba_default_password}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class SambaConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.show()

    def save_config(self, button):
        group, keys = 'samba', ['default_share_path', 'samba_default_user', 'samba_default_password']
        self.save_CONF_group_keys(group, keys)
        # ui.return_last(button)
        SambaConsoleView(self)
    
    def default_share_path_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入路径", ("white", " "), ]))
            CONF.samba.default_share_path = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif not os.path.isabs(current_value):
            edit_obj.set_caption(('header', [f"不是绝对地址", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.samba.default_share_path = current_value
    
    def default_password_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入密码", ("white", " "), ]))
            CONF.samba.samba_default_password = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii字符", ("white", " "), ]))
        elif len(current_value) < 4:
            edit_obj.set_caption(('header', [f"密码太短", ("white", " "), ]))
        elif len(current_value) > 20:
            edit_obj.set_caption(('header', [f"密码太长", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.samba.samba_default_password = current_value

    def update_view(self):
        widget_list = [
            urwid.Padding(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("共享目录", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", CONF.samba.default_share_path, self.default_share_path_change_button_func), "editbx", "editfc"),
                        ]
                    ), left=8, right=10
                ),
            ),
            urwid.Padding(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("samba用户密码", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", CONF.samba.samba_default_password, self.default_password_change_button_func), "editbx", "editfc"),
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
                urwid.Text("编辑smaba配置", align="center"),
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
