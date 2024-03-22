import time
import logging

import urwid

from pve_tui.config import CONF
from pve_tui import ui
from pve_tui.ui import my_widget, base_view
from cs_utils import execute, func

LOG = logging.getLogger(__name__)


class CephClusterConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.bcache_config_list= self.get_bcache_config_list()
        self.bcache_config = None
        self.installed_env_buttons = []
        self.installed_env_hosts = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        self.original_select_nodes = func.get_string_split_list(CONF.ceph.monitor_nodes, split_flag=',')
        self.installed_ceph_nodes = []
        self.show()
    
    def on_enable_bcache_change(self, obj, value):
        # obj   : <CheckBox selectable flow widget '是否启用bcache' state=False>
        # value : no value(bool)
        if value:
            self.bcache_config.widget_list = self.bcache_config_list
        else:
            self.bcache_config.widget_list = [urwid.Divider()]
        CONF.ceph.enable_bcache = value
    
    def get_bcache_config_list(self):
        config_list = [
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("bcache分区大小(GB)", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('bcache_size', CONF_group_name='ceph', my_max=CONF.ceph.bcache_size_minimum*100, my_min=CONF.ceph.bcache_size_minimum), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("db分区大小(GB)", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('db_size', CONF_group_name='ceph', my_max=CONF.ceph.db_size_minimum*100, my_min=CONF.ceph.db_size_minimum), "editbx", "editfc"),
                    ]
                ), left=8, right=10
            ),
            urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("缓存盘与数据盘的数量配比", align="left"),
                        urwid.AttrMap(my_widget.IntEdit('max_backends_per_cache', CONF_group_name='ceph', my_max=CONF.ceph.max_backends_per_cache_minimum*100, my_min=CONF.ceph.max_backends_per_cache_minimum), "editbx", "editfc"),
                    ]
                ),left=8, right=10
            ),
        ]
        return config_list
    
    def update_view(self):
        self.installed_env_buttons = []
        self.installed_env_hosts.sort()
        for name in self.installed_env_hosts:
            rb = urwid.Text(f'{name} (已安装)') if name in self.installed_ceph_nodes else name
            rb = my_widget.MyCheckBox(name, state=name in self.original_select_nodes)
            self.installed_env_buttons.append(rb)
        if self.installed_env_buttons:
            self.pile_view.widget_list = [urwid.GridFlow([*self.installed_env_buttons],20,3,1,"left")]
        else:
            self.pile_view.widget_list = [urwid.Text(f"没有已安装基础环境的节点", align="center")]

    def get_ceph_mon_nodes(self, loop=None, user_data=None):
        mon_nodes = []
        try:
            current_host_name = func.get_current_node_hostname()
            ceph_nodes = rpc_client('get_ceph_orch_ls', hostname=current_host_name)
            for data in ceph_nodes:
                if 'mon' != data['service_name']:
                    continue
                mon_nodes = data['placement'].get('hosts') or []
        except:
            pass
        self.installed_ceph_nodes = mon_nodes
        self.update_view()

    def save_config(self, button):
        check_boxs = [i for i in self.installed_env_buttons if isinstance(i, urwid.CheckBox)]
        selected_name_list = [i.get_label()[:7] for i in check_boxs if i.state]
        if not selected_name_list:
            self.note_msg = '必须选择节点才能继续操作'
            return
        if len(selected_name_list) + len(self.installed_ceph_nodes) > 3:
            self.note_msg = '节点不能超过3个'
            return
        LOG.info(f'ceph monitor_nodes selected_name_list={selected_name_list}')
        CONF.ceph.monitor_nodes = ','.join(selected_name_list)
        group, keys = 'ceph', ['osd_pool_default_size', 'monitor_nodes', 'enable_bcache', 'bcache_size', 'db_size', 'max_backends_per_cache']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)

    def show(self):
        self.update_view()
        if CONF.ceph.enable_bcache:
            self.bcache_config = urwid.Pile(self.bcache_config_list)
        else:
            self.bcache_config = urwid.Pile([urwid.Divider()])
        body = urwid.Pile(
            [
                urwid.Text("编辑默认配置", align="center"),
                urwid.Divider(),
                urwid.Padding(urwid.Text("请选择MON节点, 1个或3个:"), left=4, right=4, min_width=10),
                urwid.Padding(self.pile_view, left=4, right=4, min_width=10),
                urwid.Divider(),
                urwid.Padding(
                    urwid.Columns(
                        [
                            urwid.Text("pool副本数", align="left"),
                            urwid.AttrMap(my_widget.IntEdit('osd_pool_default_size', CONF_group_name='ceph', my_max=CONF.ceph.osd_pool_default_min_size*3, my_min=CONF.ceph.osd_pool_default_min_size), "editbx", "editfc"),
                        ]
                    ), left=4, right=10
                ),
                # urwid.Divider('-'),
                urwid.Padding(urwid.CheckBox('是否启用bcache（全闪无需启用）', state=CONF.ceph.enable_bcache, on_state_change=self.on_enable_bcache_change), left=4, right=4, min_width=10),
                self.bcache_config,
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
        ui.top_loop.set_alarm_in(1, self.get_ceph_mon_nodes)
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
