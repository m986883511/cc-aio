import time
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func, AUTHOR_NAME
from hostadmin.rpc import rpc_client

LOG = logging.getLogger(__name__)


class DiskOperationView(base_view.BaseConfigView):
    def __init__(self, origin_view, button):
        super().__init__(button)
        self.current_hostname = func.get_current_node_hostname()
        self.geshihua_flag = False
        self.geshihua_input_text = ""
        self.geshihua_confirm_text = '123'
        self.show()

    def get_not_root_disks(self):
        try:
            all_disk_list = rpc_client('get_all_disks', hostname=self.current_hostname)
            return all_disk_list
        except Exception as e:
            err = f'获取非系统盘失败, 联系开发者{AUTHOR_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return []

    def geshihua_disk_button(self, button):
        pass

    def geshihua_input_text_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption((''))
            return
        self.geshihua_input_text = current_value
        if current_value == self.geshihua_confirm_text:
            self.update_view()

    def geshihua_flag_change(self, obj: urwid.CheckBox, value: bool):
        self.geshihua_flag = value
        self.update_view()

    def update_view(self):
        widget_list = [
            urwid.Padding(urwid.CheckBox('格式化硬盘:', state=self.geshihua_flag, on_state_change=self.geshihua_flag_change), left=4, right=4, min_width=10)
        ]
        if self.geshihua_flag:
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text(f"若要格式化请输入({self.geshihua_confirm_text}):", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", self.geshihua_input_text, self.geshihua_input_text_change_button_func), "editbx", "editfc")
                        ]
                    ), align="left", left=8, right=4
                )
            )
            if self.geshihua_input_text == self.geshihua_confirm_text:
                widget_list.append(urwid.Padding(urwid.Button("点击此按钮将格式化此硬盘, 所有数据将丢失, 后果很严重想清楚再点!", self.geshihua_disk_button, align="center"), align="left", left=8, right=4))
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("非系统盘硬盘配置", align="center"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Divider(),
                urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=4, right=4),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))


class DiskConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.current_hostname = func.get_current_node_hostname()
        self.show()

    def disk_config(self, button):
        DiskOperationView(self, button)

    def get_not_root_disks(self):
        try:
            all_disk_list = rpc_client('get_all_disks', hostname=self.current_hostname)
            return all_disk_list
        except Exception as e:
            err = f'获取非系统盘失败, 联系开发者{AUTHOR_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return []

    def update_view(self):
        widget_list = [
            urwid.Padding(urwid.Text(f"当前机器的非系统物理硬盘有:", align="left"), left=4, right=10),
            urwid.Padding(urwid.Divider('-'), align="left", left=4, right=4,),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("ID", align="center"),
                        urwid.Columns([
                            urwid.Text("逻辑盘", align="center"),
                            urwid.Text("类型", align="center"),
                            urwid.Text("容量", align="center"), 
                        ]),
                    ]
                ),
            align="left", left=8, right=4,),
            urwid.Padding(urwid.Divider('-'), align="left", left=4, right=4,),
        ]
        all_disk_list = self.get_not_root_disks()
        for disk_dict in all_disk_list:
            size = disk_dict['size'] or 0
            size = func.convert_to_GT_str(int(disk_dict['size'])) or '--'
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Button(disk_dict['id'], self.disk_config, align="center"),
                            urwid.Columns([
                                urwid.Text(disk_dict['name'], align="center"),
                                urwid.Text(disk_dict['media'], align="center"),
                                urwid.Text(size, align="center"), 
                            ]),
                        ]
                    ),
                align="left", left=4, right=4,)
            )
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("选择一个物理硬盘", align="left"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Divider(),
                urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=4, right=4),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
