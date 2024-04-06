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
    def __init__(self, origin_view, button, disk_name):
        super().__init__(button)
        self.disk_name = disk_name
        self.origin_view = origin_view
        self.current_hostname = func.get_current_node_hostname()
        self.geshihua_flag, self.mount_flag = False, False
        self.geshihua_input_text, self.mount_input_text = "", ""
        self.geshihua_confirm_text, self.mount_confirm_text = 'yes-i-really-really-format-it', 'yes-i-really-really-mount-it'
        self.geshihua_confirm_text_correct_flag, self.mount_confirm_text_correct_flag = False, False
        self.show()

    def geshihua_disk_button(self, button):
        self.geshihua_input_text = ""
        base_view.RunCmdConsoleView(self, des=f'格式化{self.disk_name}硬盘', cmd=f'cg-hostcli disk format-disk-and-create-one-primary /dev/{self.disk_name} {self.geshihua_confirm_text}')

    def mount_disk_button(self, button, new_mount_path):
        self.mount_input_text = ""
        base_view.RunCmdConsoleView(self, des=f'{self.disk_name}硬盘挂载配置', cmd=f'cg-hostcli disk umount-disk-and-mount-new /dev/{self.disk_name} {new_mount_path} {self.mount_confirm_text}')

    def geshihua_input_text_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption((''))
            return
        self.geshihua_input_text = current_value
        if current_value == self.geshihua_confirm_text:
            self.geshihua_confirm_text_correct_flag = True
            self.update_view()
        else:
            if self.geshihua_confirm_text_correct_flag:
                self.geshihua_confirm_text_correct_flag = False
            self.update_view()
    
    def mount_input_text_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption((''))
            return
        self.mount_input_text = current_value
        if current_value == self.mount_confirm_text:
            self.mount_confirm_text_correct_flag = True
            self.update_view()
        else:
            if self.mount_confirm_text_correct_flag:
                self.mount_confirm_text_correct_flag = False
            self.update_view()

    def mount_flag_change(self, obj: urwid.CheckBox, value: bool):
        self.mount_flag = value
        self.update_view()

    def geshihua_flag_change(self, obj: urwid.CheckBox, value: bool):
        self.geshihua_flag = value
        self.update_view()

    def get_disk_mount_path(self):
        all_disk_list = self.origin_view.get_not_root_disks()
        for value in all_disk_list:
            if value['name'] == self.disk_name:
                return value['mount'] or []
        return []
    
    def get_disk_block(self):
        all_disk_list = self.origin_view.get_not_root_disks()
        for value in all_disk_list:
            if value['name'] == self.disk_name:
                return value['block'] or []
        return []

    def update_view(self):
        widget_list = [
            urwid.Padding(urwid.CheckBox('格式化硬盘:', state=self.geshihua_flag, on_state_change=self.geshihua_flag_change), left=4, right=4, min_width=10)
        ]
        if self.geshihua_flag:
            block_list = self.get_disk_block()
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text(f"{self.disk_name}当前已有分区:", align="left"),
                            urwid.Text(' '.join(block_list), align="left"),
                        ]
                    ), align="left", left=8, right=4
                )
            )
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text(f"二次确认, 若要格式化请输入({self.geshihua_confirm_text}), 才会显示操作按钮:", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", self.geshihua_input_text, self.geshihua_input_text_change_button_func), "editbx", "editfc")
                        ]
                    ), align="left", left=8, right=4
                )
            )
            if self.geshihua_input_text == self.geshihua_confirm_text:
                widget_list.append(urwid.Padding(urwid.Button("点击此按钮将格式化此硬盘, 所有数据将丢失, 后果很严重想清楚再点!", self.geshihua_disk_button, align="center"), align="left", left=8, right=4))
        widget_list.append(urwid.Divider())
        widget_list.append(urwid.Padding(urwid.CheckBox('挂载硬盘到samba共享存储:', state=self.mount_flag, on_state_change=self.mount_flag_change), left=4, right=4, min_width=10))
        if self.mount_flag:
            mount_list = self.get_disk_mount_path()
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text(f"{self.disk_name}当前已挂载:", align="left"),
                            urwid.Text(' '.join(mount_list), align="left"),
                        ]
                    ), align="left", left=8, right=4
                )
            )
            widget_list.append(
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text(f"二次确认, 若要挂载请输入({self.mount_confirm_text}), 才会显示操作按钮:", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", self.mount_input_text, self.mount_input_text_change_button_func), "editbx", "editfc")
                        ]
                    ), align="left", left=8, right=4
                )
            )
            if self.mount_input_text == self.mount_confirm_text:
                new_mount_path = f'{CONF.samba.default_share_path}/{self.origin_layout_button_label}'
                widget_list.append(urwid.Padding(urwid.Button(f"点击此按钮将解除{self.disk_name}硬盘所有挂载, 并将其挂载到{new_mount_path}", self.mount_disk_button, user_data=new_mount_path, align="center"), align="left", left=8, right=4))
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text(f"{self.disk_name}硬盘配置", align="center"),
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

    def disk_config(self, button, disk_name):
        DiskOperationView(self, button, disk_name)

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
                            urwid.Button(disk_dict['id'], self.disk_config, user_data=disk_dict['name'], align="center"),
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
