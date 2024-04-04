import copy
import logging
import traceback

import urwid

from pvetui.config import CONF
from pvetui import ui, utils, jm_data, exception
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func
from hostadmin.rpc import rpc_client
from hostadmin.business import Usage, Bond

LOG = logging.getLogger(__name__)


class NetworkConfigView(base_view.BaseConfigView):
    def __init__(self, origin_view: base_view.BaseConfigView, origin_button:urwid.Button):
        super().__init__(origin_button)
        self.origin_view = origin_view
        self.network_column_list = []
        self.bond_view_list = []
        self.selected_usage = jm_data.network_config_menu.get(self.origin_layout_button_label)
        self.selected_hostname = self.origin_view.origin_layout_button_label
        self.bond_pile = urwid.Pile([urwid.Divider()])
        self.button_pile = urwid.Pile([urwid.Divider()])
        self.access_ip_mask_edit_obj: urwid.Edit = None
        self.access_default_gateway_edit_obj: urwid.Edit = None
        self.bond_mode_edit_obj: urwid.Edit = None
        self._delay_update_view_alarm = None
        self.single_vm_network_action = None
        self.single_vm_flag = None
        self.show()
    
    def _start_delay_update_view_alarm(self, loop=None, user_data=None):
        if self._delay_update_view_alarm:
            ui.top_loop.remove_alarm(self._delay_update_view_alarm)
            self._delay_update_view_alarm = None
            self.update_view()
        else:
            self._delay_update_view_alarm = ui.top_loop.set_alarm_in(CONF.network.delay_update_view_time, self._start_delay_update_view_alarm)
    
    def _on_state_change(self, obj: urwid.CheckBox, value):
        if self.selected_usage not in [Usage.ceph_cluster, Usage.ceph_public]:
            return
        first_widget_list = [c.widget_list[0] for c in self.network_column_list]
        nic_checkbox_list = [c for c in first_widget_list if isinstance(c, urwid.CheckBox)]
        selected_nic_name_list = [i.label for i in nic_checkbox_list if i.state]
        temp = copy.deepcopy(selected_nic_name_list)
        if value:
            if obj.label in temp:
                pass
            else:
                temp.append(obj.label)
        else:
            if obj.label in temp:
                temp.remove(obj.label)
            else:
                pass
        if len(temp) > 1:
            self.bond_pile.widget_list = self.bond_view_list
        else:
            self.bond_pile.widget_list = [urwid.Divider()]

    def get_network_colume(self, **kwargs):
        _usage = kwargs.get('usage') or []
        _name_str = kwargs.get('name') or ''
        if self.selected_usage == Usage.mgt:
            _name = urwid.Text(_name_str)
        else:
            if kwargs.get('checkbox'):
                if not _usage:
                    _name = my_widget.MyCheckBox(_name_str, on_state_change=self._on_state_change)
                else:
                    _name = urwid.Text('    ' + _name_str)
            else:
                _name = urwid.Text(_name_str)
        _bond = kwargs.get('bond') or '-'
        _join = ', ' if _bond == Bond.ext else '\n'
        _usage = _join.join(_usage) if isinstance(_usage, list) else _usage or '-'
        _ip = kwargs.get('ip')
        _ip = '\n'.join(_ip) if isinstance(_ip, list) else _ip or '-'
        return urwid.Columns(
            [
                _name,
                urwid.Text(kwargs.get('driver') or '-'),
                urwid.Text(kwargs.get('speed') or '-'),
                urwid.Text(kwargs.get('link') or '-'),
                urwid.Text(_ip),
                urwid.Text(_bond),
                urwid.Text(kwargs.get('bond_mode') or '-'),
                urwid.Text(_usage)
            ]
        )

    def return_button_click(self, button):
        self.origin_view.update_view()
        return ui.return_last(button)

    def get_hostcli_network_list(self):
        try:
            # jm_data.hostcli_network_list
            return rpc_client('get_all_physical_nics', hostname=self.selected_hostname)
        except Exception as e:
            self._note_alarm_time = 3600 * 24
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'获取{self.selected_hostname}的所有物理网卡信息')
            return []

    def _access_default_gw_change_func(self, edit_obj: urwid.Edit, current_value):
        if func.ValidIpAddress.is_ip(current_value):
            edit_obj.set_caption('')
        else:
            edit_obj.set_caption(('header', [f"格式不是ip地址!", ("white", " "), ]))

    def _access_ip_mask_change_func(self, edit_obj: urwid.Edit, current_value):
        if func.ValidIpAddress.is_cidr(current_value, strict=False):
            ip = func.get_string_split_list(current_value, split_flag='/')[0]
            if not func.check_access_ip_not_reserved(ip):
                edit_obj.set_caption(('header', [f"地址可能和其他网络段冲突!", ("white", " "), ]))
            else:
                edit_obj.set_caption('')
        else:
            edit_obj.set_caption(('header', [f"格式不是ip/mask地址!", ("white", " "), ]))

    def _bond_mode_change_func(self, edit_obj: urwid.Edit, current_value:str):
        if current_value.isdigit():
            value = int(current_value)
            if value > 6 or value < 0:
                edit_obj.set_caption(('header', [f"Bond模式的范围0-6!", ("white", " "), ]))
            else:
                edit_obj.set_caption('')
        else:
            if current_value == '':
                edit_obj.set_caption('')
            else:
                edit_obj.set_caption(('header', [f"必须输入数字!", ("white", " "), ]))

    def on_enable_vm_checkbox_change(self, obj, value):
        self.single_vm_network_action = value
        self.update_view()
    
    def update_view(self):
        self.network_column_list = []
        hostcli_netowrk_list = self.get_hostcli_network_list()
        all_bond = [value.get('bond') for value in hostcli_netowrk_list if value.get('bond')]
        self.single_vm_flag = self.single_vm_network_action if self.single_vm_network_action != None else Bond.vm in all_bond
        if self.selected_usage != Usage.access:
            if self.selected_usage == Usage.vm:
                self.network_column_list.append(urwid.Text("说明：业务网络如果不配置，将和外部网络合一", align="left"))
                self.network_column_list.append(urwid.Padding(urwid.CheckBox('启用独立的业务网络', state=self.single_vm_flag, on_state_change=self.on_enable_vm_checkbox_change), left=4, right=4, min_width=10))
                self.network_column_list.append(urwid.Divider())
            if self.selected_usage != Usage.vm or self.selected_usage == Usage.vm and self.single_vm_flag:
                self.network_column_list.append(self.get_network_colume(**jm_data.hostcli_network_list_dec))
                for network in hostcli_netowrk_list:
                    column = self.get_network_colume(checkbox=True, **network)
                    self.network_column_list.append(column)
        else:
            access_ip_mask = ''
            access_default_gateway = ''
            for network in hostcli_netowrk_list:
                if self.selected_usage in network.get('usage') or []:
                    manage_ip = func.get_hostname_map_ip(self.selected_hostname)
                    for ip in network.get('ip') or []:
                        if not ip.startswith(manage_ip):
                            access_ip_mask = ip
                            access_default_gateway = network.get('default_gateway') or ''
            self.access_ip_mask_edit_obj = my_widget.TextEdit('', access_ip_mask, self._access_ip_mask_change_func)
            self.access_default_gateway_edit_obj = my_widget.TextEdit('', access_default_gateway, self._access_default_gw_change_func)
            self.network_column_list = [
                urwid.Text("说明：接入网络的IP地址，将配置在管理网口上，用于云平台的API和Dashboard访问", align="left"),
                urwid.Divider(),
                urwid.Columns(
                    [
                        urwid.Text("IP地址/掩码", align="left"),
                        urwid.AttrMap(self.access_ip_mask_edit_obj, "editbx", "editfc"),
                    ]
                ),
                urwid.Columns(
                    [
                        urwid.Text("默认网关", align="left"),
                        urwid.AttrMap(self.access_default_gateway_edit_obj, "editbx", "editfc"),
                    ]
                )
            ]
        if self.network_column_list:
            self.pile_view.widget_list = [*self.network_column_list]
        else:
            self.pile_view.widget_list = [urwid.Divider()]

        bond_mode = bond_name = ""
        if self.selected_usage not in  [Usage.mgt, Usage.access]:
            for network in hostcli_netowrk_list:
                if self.selected_usage in network.get('usage') or []:
                    bond_mode = network.get('bond_mode') or ''
                    bond_name = network.get('bond') or ''
            self.bond_view_list = self.get_bond_view(bond_mode, bond_name)
        else:
            self.bond_view_list = [urwid.Divider()]
        # 如果是vm合一不显示bond_view
        if self.selected_usage == Usage.vm and not self.single_vm_flag:
            self.bond_view_list = [urwid.Divider()]
        # 给ceph的bond网络配置添加动态效果
        if self.selected_usage in [Usage.ceph_cluster, Usage.ceph_public] and not bond_name:
            self.bond_pile.widget_list = [urwid.Divider()]
        else:
            self.bond_pile.widget_list = self.bond_view_list

        if Usage.mgt == self.selected_usage:
            self.button_pile.widget_list = [
                urwid.Button(CONF.return_last_string, self.return_button_click, align="center"),
            ]
        elif Usage.vm == self.selected_usage and not self.single_vm_flag:
            self.button_pile.widget_list = [
                urwid.Padding(urwid.Button(CONF.return_last_string, self.return_button_click, align="center"),left=3, right=3)
            ]
        else:
            self.button_pile.widget_list =  [
                    urwid.Columns(
                        [
                            urwid.Padding(urwid.Button("开始配置", self.start_config, align="center"), align="center", left=1, right=1),
                            urwid.Padding(urwid.Button("清除配置", self.clear_config, align="center"), align="center", left=1, right=1),
                            urwid.Padding(urwid.Button(CONF.return_last_string, self.return_button_click, align="center"), align="center", left=1, right=1),
                        ]
                    )
            ]

    def _check_input_access_network(self, ip_mask, gw):
        if not func.ValidIpAddress.is_cidr(ip_mask, strict=False):
            self.note_msg = f'接入地址 {ip_mask} 格式有误，正确格式为: x.x.x.x/xx'
            return False
        if not func.ValidIpAddress.is_ip(gw):
            self.note_msg = f'默认网关 {gw} 不是一个合法的IP地址!'
            return False
        ip = func.get_string_split_list(ip_mask, split_flag='/')[0]
        if not func.check_access_ip_not_reserved(ip):
            self.note_msg = f'接入地址 {ip}, 与系统保留网段冲突!'
            return False
        if not func.ValidIpAddress.ip_in_cidr(gw, ip_mask):
            self.note_msg = f'默认网关 {gw} 与接入地址 {ip_mask} 不在同一个网段!'
            return False
        return True

    def get_bond_view(self, bond_mode, bond_name):
        self.bond_mode_edit_obj = my_widget.TextEdit('', bond_mode, self._bond_mode_change_func, align='left')
        config_list = [
            urwid.Divider(),
            urwid.Divider('-'),
            urwid.Divider(),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("Bond模式(不填默认为模式0, 即balance-rr)", align="left"),
                        urwid.AttrMap(self.bond_mode_edit_obj, "editbx", "editfc")
                    ]
                ), left=8, right=10
            ),
        ]
        return config_list

    def start_config(self, button):
        if self.selected_usage != Usage.access:
            first_widget_list = [c.widget_list[0] for c in self.network_column_list if isinstance(c, urwid.Columns)]
            nic_checkbox_list = [c for c in first_widget_list if isinstance(c, urwid.CheckBox)]
            selected_nic_name_list = [i.label for i in nic_checkbox_list if i.state]
            if not selected_nic_name_list:
                self.note_msg = f'必须选择网卡,才能继续操作'
                return
            selected_nic_name_str = ','.join(selected_nic_name_list)
        else:
            selected_nic_name_str = ''
        try:
            bond_mode = self.bond_mode_edit_obj.get_edit_text() if self.bond_mode_edit_obj else None
            input_ip = self.access_ip_mask_edit_obj.get_edit_text() if self.access_ip_mask_edit_obj else None
            input_gateway = self.access_default_gateway_edit_obj.get_edit_text() if self.access_default_gateway_edit_obj else None
            if self.selected_usage == Usage.access:
                LOG.info(f'input_ip={input_ip}, input_gateway={input_gateway}')
                if not self._check_input_access_network(input_ip, input_gateway):
                    return
            rpc_client(
                'set_usage_network', 
                hostname=self.selected_hostname, 
                usage=self.selected_usage, 
                nic=selected_nic_name_str,
                bond_mode=bond_mode, 
                input_ip=input_ip, 
                input_gateway=input_gateway
            )
            self.note_msg = f'配置 {self.selected_usage} 网络成功'
            self._start_delay_update_view_alarm()
        except Exception as e:
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'在{self.selected_hostname}上配置{self.selected_usage}网络')
        self.update_view()

    def clear_config(self, button):
        try:
            rpc_client('clear_usage_network', hostname=self.selected_hostname, usage=self.selected_usage)
            self.note_msg = f'清除 {self.selected_usage} 网络成功'
            self._start_delay_update_view_alarm()
        except Exception as e:
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'在{self.selected_hostname}上清除{self.selected_usage}网络')
        self.update_view()

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(self.origin_layout_button_label),
                urwid.Divider(),
                self.pile_view,
                self.bond_pile,
                self.note_text,
                self.button_pile
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
