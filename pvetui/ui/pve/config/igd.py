import os
import time
import shutil
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from hostadmin.rpc import rpc_client
from cc_utils import execute, func, AUTHOR_NAME, AUTHOR_ZH_NAME
from cc_driver.pve import pvesh

LOG = logging.getLogger(__name__)


class IgdConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.current_hostname = func.get_current_node_hostname()
        self.my_igd_rom_name = 'my-igd.rom'
        self.my_audio_rom_name = 'my-audio.rom'
        self.cpu_model = self.get_cpu_model()
        self.find_igd_flag = False
        self.pvesh_qemu_list = {}
        self.get_igd_device()
        self.show()

    def get_cpu_model(self):
        try:
            cpu_model = rpc_client('get_cpu_model', hostname=self.current_hostname)
            return cpu_model
        except Exception as e:
            err = f'读取cpu型号失败, 请联系开发者{AUTHOR_ZH_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return err
    
    def get_igd_device(self):
        try:
            igd_device = rpc_client('get_node_igd_device', hostname=self.current_hostname)
        except Exception as e:
            err = f'读取支持的gpu型号失败, 请联系开发者{AUTHOR_ZH_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return err
        self.find_igd_flag = False
        if not igd_device:
            return
        self.igd_full_pci_id = igd_device['full_pci_id']
        self.igd_name = igd_device['name']
        self.igd_main_vendor = igd_device['main_vendor']
        self.audio_rom = igd_device.get('audio_rom')
        self.igd_rom = igd_device.get('rom')
        self.find_igd_rom_path()
        self.find_audio_rom_path()
        self.find_igd_flag = True

    def find_igd_rom_path(self):
        if CONF.igd.igd_rom_path:
            return
        # 先检查用户自己传的
        flag, content = execute.execute_command(f'find {CONF.samba.default_share_path}/{AUTHOR_ZH_NAME}的赠礼 -name {self.my_igd_rom_name}')
        if flag == 0:
            content_list = func.get_string_split_list(content, split_flag='\n')
            if content_list:
                CONF.igd.igd_rom_path = content_list[0]
                return
        if self.igd_rom:
            # 再检查版本自带的
            flag, content = execute.execute_command(f'find /opt/{AUTHOR_NAME} -name {self.igd_rom}')
            if flag == 0:
                content_list = func.get_string_split_list(content, split_flag='\n')
                if content_list:
                    CONF.igd.igd_rom_path = content_list[0]
                    return
        else:
            # 尝试自己生成
            try:
                vbios_path = rpc_client('create_vbios_file')
            except Exception as e:
                err = f'尝试自己生成vbios失败, err={str(e)}'
                LOG.error(err)
                self.note_msg = err
                return
            CONF.igd.igd_rom_path = vbios_path

    def find_audio_rom_path(self):
        if CONF.igd.audio_rom_path:
            return
        # 先检查用户自己传的
        flag, content = execute.execute_command(f'find {CONF.samba.default_share_path}/{AUTHOR_ZH_NAME}的赠礼 -name {self.my_audio_rom_name}')
        if flag == 0:
            content_list = func.get_string_split_list(content, split_flag='\n')
            if content_list:
                CONF.igd.audio_rom_path = content_list[0]
                return
        if self.audio_rom:
            # 再检查版本自带的
            flag, content = execute.execute_command(f'find /opt/{AUTHOR_NAME} -name {self.audio_rom}')
            if flag == 0:
                content_list = func.get_string_split_list(content, split_flag='\n')
                if content_list:
                    CONF.igd.audio_rom_path = content_list[0]
                    return

    def get_who_use_igd(self):
        vmids = []
        for qemu_dict in self.pvesh_qemu_list:
            # if qemu_dict['status'] != 'running':
            #     continue
            vmid = qemu_dict['vmid']
            node_config = pvesh.Nodes().get_node_config(vmid)
            for key, value in node_config.items():
                if key.startswith('hostpci'):
                    if self.igd_full_pci_id in value:
                        vmids.append(qemu_dict['vmid'])
        return vmids

    def set_igd_passthrough(self, button: urwid.Button, vmid):
        self.save_config()
        cmds = [
            f'cc-hostcli pve set-vm-igd-paththrough {vmid} {CONF.igd.igd_rom_path} {CONF.igd.audio_rom_path}'
        ]
        base_view.RunCmdConsoleView(self, cmds=cmds, des=f'开始设置vmid={vmid}')

    def del_igd_passthrough(self, button: urwid.Button, vmid):
        self.save_config()
        cmds = [
            f'cc-hostcli pve del-vm-hostpci-config {vmid}',
            f'pvesh create /nodes/localhost/qemu/{vmid}/config --delete vga'
        ]
        base_view.RunCmdConsoleView(self, cmds=cmds, des=f'开始设置vmid={vmid}')

    def save_config(self):
        group, keys = 'igd', ['audio_rom_path', 'igd_rom_path']
        self.save_CONF_group_keys(group, keys)

    def audio_rom_path_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.igd.audio_rom_path = ''
            return
        if not os.path.isfile(current_value):
            edit_obj.set_caption(('header', [f"文件不存在", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.igd.audio_rom_path = current_value
    
    def igd_rom_path_change(self, edit_obj: my_widget.TextEdit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.igd.igd_rom_path = ''
            return
        if not os.path.isfile(current_value):
            edit_obj.set_caption(('header', [f"文件不存在", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.igd.igd_rom_path = current_value

    def update_view(self):
        widget_list = [
            urwid.Padding(urwid.Text(f"读取CPU信息:", align="left"), left=4, right=10),
            urwid.Padding(urwid.Text(f"你的CPU型号是: {self.cpu_model}", align="left"), left=8, right=10),
        ]
        if self.find_igd_flag:
            widget_list.append(urwid.Padding(urwid.Text(f"你的核显型号是: {self.igd_name}", align="left"), left=8, right=10),)
            widget_list.append(urwid.Padding(urwid.Text(f"你的核显vendor是: {self.igd_main_vendor}", align="left"), left=8, right=10),)
            widget_list.append(urwid.Padding(urwid.Text(f"你的核显full_pci_id是: {self.igd_full_pci_id}", align="left"), left=8, right=10),)
        else:
            widget_list.append(urwid.Padding(urwid.Text(f"没有找到核显, 如果你确定真的有, 清联系开发者{AUTHOR_ZH_NAME}, 很快就能加一下.", align="left"), left=8, right=10),)
        widget_list.append(urwid.Divider())
        if self.find_igd_flag:
            widget_list.append(urwid.Padding(urwid.Text(f"直通核显给哪台qemu虚拟机呢?", align="left"), left=4, right=10),)
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text(f"核显的vbios rom文件绝对路径(优先在{AUTHOR_ZH_NAME}的赠礼中查找{self.my_igd_rom_name}):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.igd.igd_rom_path, self.igd_rom_path_change), "bright", "buttn"),
                    ]
                ),
                align="left", left=8, right=10,),
            )
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text(f"HDMI的音频rom文件绝对路径(优先在{AUTHOR_ZH_NAME}的赠礼中查找{self.my_audio_rom_name}):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.igd.audio_rom_path, self.audio_rom_path_change), "bright", "buttn"),
                    ]
                ),
                align="left", left=8, right=10,),
            )
            self.pvesh_qemu_list = pvesh.Nodes().qemu_list()
            self.pvesh_qemu_list.sort(key=lambda x: x['vmid'])
            use_igd_vmids = self.get_who_use_igd()
            conlumn_table = [
                urwid.Padding(urwid.Divider('-'), align="left", left=8, right=10,),
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("名称", align="center"),
                            urwid.Text("ID", align="center"),
                            urwid.Text("状态", align="center"),
                            urwid.Text("操作", align="center"), 
                        ]
                    ),
                align="left", left=8, right=10,),
                urwid.Padding(urwid.Divider('-'), align="left", left=8, right=10,)
            ]
            widget_list.extend(conlumn_table)
            for qemu_dict in self.pvesh_qemu_list:
                vm_status = qemu_dict['status']
                if qemu_dict['vmid'] in use_igd_vmids:
                    if vm_status == 'stopped':
                        operation_button = urwid.Padding(urwid.AttrMap(urwid.Button(f"删除直通配置", user_data=qemu_dict['vmid'], on_press=self.del_igd_passthrough, align="center"), None, focus_map='buttn'), align="center", left=1, right=1)
                    else:
                        operation_button = urwid.Padding(urwid.Text(f"停止后才能删除配置", align="center"), align="center", left=1, right=1)
                else:
                    if vm_status == 'stopped':
                        operation_button = urwid.Padding(urwid.AttrMap(urwid.Button(f"配置直通", user_data=qemu_dict['vmid'], on_press=self.set_igd_passthrough, align="center"), None, focus_map='buttn'), align="center", left=1, right=1)
                    else:
                        operation_button = urwid.Padding(urwid.Text(f"停止后才能配置直通", align="center"), align="center", left=1, right=1)
                widget_list.append(
                    urwid.Padding(
                        urwid.Columns(
                            [
                                urwid.Padding(urwid.Text(f"{qemu_dict['name']}", align="center"), align="center", left=1, right=1),
                                urwid.Padding(urwid.Text(f"{qemu_dict['vmid']}", align="center"), align="center", left=1, right=1),
                                urwid.Padding(urwid.Text(vm_status, align="center"), align="center", left=1, right=1),
                                operation_button
                            ]
                        )
                    , left=8, right=10)
                )
        self.pile_view.widget_list = widget_list

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text(self.origin_layout_button_label, align="left"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Divider(),
                urwid.Padding(urwid.AttrMap(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), None, focus_map='buttn'), align="center", left=1, right=1)
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
