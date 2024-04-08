import time
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cc_utils import execute, func

LOG = logging.getLogger(__name__)


class AlistConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_install_alist_view = [
            urwid.Text(f'开始配置alist服务', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button_attrmap,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_alist_view))
        self.need_run_cmd_list.append(f'cc-hostcli service create-alist-service {CONF.alist.default_admin_password}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class AlistConfigView(base_view.BaseConfigView):
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
                            urwid.AttrMap(my_widget.TextEdit("", CONF.alist.default_admin_password, self.default_password_change_button_func), "bright", "buttn"),
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
                urwid.Text("编辑alist配置", align="center"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.AttrMap(urwid.Button("保存并配置服务", self.save_config, align="center"), None, focus_map='buttn'), align="center", left=1, right=1),
                        urwid.Padding(urwid.AttrMap(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), None, focus_map='buttn'), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
