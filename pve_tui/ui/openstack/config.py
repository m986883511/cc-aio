import logging

import urwid

from pve_tui.config import CONF
from pve_tui import ui
from pve_tui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class OpenstackClusterConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.control_nodes_checkbox = []
        self.control_node_pile_view = urwid.Pile([urwid.Divider()])
        self.show()

    def mgt_vip_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption('')
            CONF.openstack.mgt_vip = ''
            return
        if func.ValidIpAddress.is_ip(current_value):
            if not current_value.startswith('192.222.1.'):
                edit_obj.set_caption(('header', [f"必须是192.222.1.xx", ("white", " "), ]))
            else:
                edit_obj.set_caption('')
                CONF.openstack.mgt_vip = current_value
        else:
            edit_obj.set_caption(('header', [f"不是ip地址", ("white", " "), ]))
    
    def access_vip_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption('')
            CONF.openstack.access_vip = ''
            return
        if func.ValidIpAddress.is_ip(current_value):
            if func.check_access_ip_not_reserved(current_value):
                edit_obj.set_caption('')
                CONF.openstack.access_vip = current_value
            else:
                edit_obj.set_caption(('header', [f"不能是192.222.1.xx", ("white", " "), ]))
        else:
            edit_obj.set_caption(('header', [f"不是ip地址", ("white", " "), ]))

    def ntp_server_change_button_func(self, edit_obj: urwid.Edit, current_value):
        if not current_value:
            edit_obj.set_caption('')
            CONF.openstack.control_nodes_ntp_server = ''
            return
        if func.ValidIpAddress.is_ip(current_value):
            edit_obj.set_caption('')
            CONF.openstack.control_nodes_ntp_server = current_value
        else:
            edit_obj.set_caption(('header', [f"不是ip地址", ("white", " "), ]))

    def _control_checkbox_callback(self, obj, value):
        state_is_true_hosts = [i.label for i in self.control_nodes_checkbox if i.state]
        if value:
            if obj.label not in state_is_true_hosts:
                state_is_true_hosts.append(obj.label)
        else:
           if obj.label in state_is_true_hosts:
                state_is_true_hosts.remove(obj.label)
        state_is_true_hosts_str = ','.join(state_is_true_hosts)
        CONF.openstack.control_nodes = state_is_true_hosts_str
        self.update_view()
    
    def update_view(self):
        installed_env_nodes = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        openstack_control_nodes = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        self.control_nodes_checkbox = []
        for hostname in installed_env_nodes:
            self.control_nodes_checkbox.append(my_widget.MyCheckBox(hostname, state=hostname in openstack_control_nodes, on_state_change=self._control_checkbox_callback))
        widget_list = [urwid.Text(f"请选择控制节点:")]
        
        if self.control_nodes_checkbox:
            widget_list.append(urwid.GridFlow([*self.control_nodes_checkbox],13,3,1,"left"))
        else:
            widget_list.append(urwid.Text(f"没有已安装基础环境的节点"))

        if len(openstack_control_nodes) > 1:
            mgt_vip = CONF.openstack.mgt_vip
            access_vip = CONF.openstack.access_vip
            widget_list.extend([
                urwid.Divider(),
                urwid.Text(f"配置控制节点HA集群vip"),
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("管理网络vip", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", mgt_vip, self.mgt_vip_change_button_func), "editbx", "editfc"),
                        ]
                    ), left=8, right=10
                ),
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("接入网络vip", align="left"),
                            urwid.AttrMap(my_widget.TextEdit("", access_vip, self.access_vip_change_button_func), "editbx", "editfc"),
                        ]
                    ), left=8, right=10
                ),
            ])
        widget_list.extend([
            urwid.Divider(),
            urwid.Text(f"请配置系统参数"),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("CPU超分系数:", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('cpu_allocation_ratio', CONF_group_name='openstack', my_max=32, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("内存超分系数:", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('ram_allocation_ratio', CONF_group_name='openstack', my_max=8, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("保留的CPU核心数:", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('reserved_host_cpus', CONF_group_name='openstack', my_max=256, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("保留的内存容量(GB):", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('reserved_host_memory_gb', CONF_group_name='openstack', my_max=256, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("业务网络VLAN号:", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('vmbond_vlan', CONF_group_name='network', my_max=4094, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("外部网络VLAN号:", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('extbond_vlan', CONF_group_name='network', my_max=4094, my_min=1), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("外部NTP时钟地址:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit('', CONF.openstack.control_nodes_ntp_server, self.ntp_server_change_button_func), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
        ])
        self.pile_view.widget_list = widget_list
    
    def save_config(self, button):
        state_is_true_control_hosts = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        if not state_is_true_control_hosts:
            self.note_msg = f'保存失败, 未选择控制节点'
            return
        current_hostname = func.get_current_node_hostname()
        if current_hostname not in CONF.openstack.control_nodes:
            self.note_msg = f'保存失败, 控制节点必须包含当前节点({current_hostname})'
            return
        control_nodes_len = len(state_is_true_control_hosts)
        if control_nodes_len != 1 and control_nodes_len != 3:
            self.note_msg = f'保存失败, 控制节点数量必须是1个或者3个'
            return
        flag, content = execute.execute_command(f'ping {CONF.openstack.control_nodes_ntp_server} -c 1 -w 1')
        execute.completed(flag, f'ping通外部NTP时钟地址={CONF.openstack.control_nodes_ntp_server}', content, raise_flag=False)
        CONF.openstack.reserved_host_memory_mb = int(CONF.openstack.reserved_host_memory_gb) * 1024
        group, keys = 'openstack', [
            'control_nodes', 'pure_compute_nodes', 'mgt_vip', 'access_vip', 'option', 'enable_cinder_backend_nfs', 'cpu_allocation_ratio', 'enable_cinder',
            'ram_allocation_ratio', 'reserved_host_cpus', 'reserved_host_memory_gb', 'reserved_host_memory_mb', 'control_nodes_ntp_server']
        self.save_CONF_group_keys(group, keys)
        group, keys = 'network', ['vmbond_vlan', 'extbond_vlan']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"OpenStack集群配置"),
                urwid.Divider(),
                urwid.Text(f"说明:"),
                urwid.Text(f"    1. 建议选择3个控制节点，或者在单节点环境选择1个控制节点"),
                urwid.Text(f"    2. 控制节点默认部署为计算节点"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.Button("确认并保存", self.save_config, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
