import os
import time
import shutil
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from hostadmin.rpc import rpc_client
from cc_utils import execute, func, AUTHOR_NAME
from cc_driver.pve import pvesh

LOG = logging.getLogger(__name__)


class IgdConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.current_hostname = func.get_current_node_hostname()
        self.cpu_model = self.get_cpu_model()
        self.find_igd_flag = False
        self.pvesh_qemu_list = {}
        self.get_igd_devices()
        self.show()

    def find_igd_devices(self):
        self.find_igd_flag = False
        if not self.igd_devices:
            return
        igd_pci_full_ids = list(self.igd_devices.keys())
        if len(igd_pci_full_ids) != 1:
            err_msg = f'读取到多个核显设备，不正常啊! keys={igd_pci_full_ids}'
            LOG.error(err_msg)
            self.note_msg = err_msg
        igd_full_pci_id = igd_pci_full_ids[0]
        self.igd_full_pci_id = igd_full_pci_id
        self.igd_name = self.igd_devices[igd_full_pci_id]['name']
        self.igd_main_vendor = self.igd_devices[igd_full_pci_id]['main_vendor']
        self.find_igd_flag = True

    def get_cpu_model(self):
        try:
            cpu_model = rpc_client('get_cpu_model', hostname=self.current_hostname)
            return cpu_model
        except Exception as e:
            err = f'读取cpu型号失败, 联系开发者{AUTHOR_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return err
    
    def get_igd_devices(self):
        try:
            pci_devices = rpc_client('get_support_pci_devices', hostname=self.current_hostname)
            self.igd_devices = pci_devices.get('igd')
            self.find_igd_devices()
        except Exception as e:
            err = f'读取支持的gpu型号失败, 联系开发者{AUTHOR_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return err

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
        try:
            vbios_path = rpc_client('create_vbios_file', hostname=self.current_hostname)
        except Exception as e:
            err = f'创建vbios文件失败, 联系开发者{AUTHOR_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return err
        file_name = os.path.basename(vbios_path)
        dst_path = os.path.join('/usr/share/kvm', file_name)
        if not os.path.isfile(dst_path):
            shutil.copy(vbios_path, '/usr/share/kvm')
        value = f'{self.igd_full_pci_id},pcie=1,x-vga=1,romfile={file_name}'
        pvesh.Nodes().set_node_config(vmid, 'hostpci', value)
        self.update_view()

    def del_igd_passthrough(self, button: urwid.Button, vmid):
        config_dict = pvesh.Nodes().get_node_config(vmid)
        for key, value in config_dict.items():
            if isinstance(value, str):
                if self.igd_full_pci_id in value:
                    pvesh.Nodes().set_node_config(vmid, key, "")
                    break
        self.update_view()

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
            widget_list.append(urwid.Padding(urwid.Text(f"没有找到核显, 如果你确定真的有, 清联系开发者{AUTHOR_NAME}, 很快就能加一下.", align="left"), left=8, right=10),)
        widget_list.append(urwid.Divider())
        if self.find_igd_flag:
            widget_list.append(urwid.Padding(urwid.Text(f"直通核显给哪台qemu虚拟机呢?", align="left"), left=4, right=10),)
            self.pvesh_qemu_list = pvesh.Nodes().qemu_list()
            self.pvesh_qemu_list.sort(key=lambda x: x['vmid'])
            use_igd_vmids = self.get_who_use_igd()
            for qemu_dict in self.pvesh_qemu_list:
                vm_status = qemu_dict['status']
                if qemu_dict['vmid'] in use_igd_vmids:
                    if vm_status == 'stopped':
                        operation_button = urwid.Padding(urwid.Button(f"删除直通配置", user_data=qemu_dict['vmid'], on_press=self.del_igd_passthrough, align="center"), align="center", left=1, right=1)
                    else:
                        operation_button = urwid.Padding(urwid.Text(f"停止后才能删除配置", align="center"), align="center", left=1, right=1)
                else:
                    if vm_status == 'stopped':
                        operation_button = urwid.Padding(urwid.Button(f"配置直通", user_data=qemu_dict['vmid'], on_press=self.set_igd_passthrough, align="center"), align="center", left=1, right=1)
                    else:
                        operation_button = urwid.Padding(urwid.Text(f"停止后才能配置直通", align="center"), align="center", left=1, right=1)
                widget_list.append(
                    urwid.Padding(
                        urwid.Columns(
                            [
                                urwid.Padding(urwid.Text(f"{qemu_dict['name']}", align="left"), align="center", left=1, right=1),
                                urwid.Padding(urwid.Text(f"{qemu_dict['vmid']}", align="left"), align="center", left=1, right=1),
                                urwid.Padding(urwid.Text(vm_status, align="left"), align="center", left=1, right=1),
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
                urwid.Text(self.origin_layout_button_label, align="center"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Divider(),
                urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1)
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
