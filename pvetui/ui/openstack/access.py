import urwid
import logging

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from pvetui import jm_data, exception
from hostadmin.rpc import rpc_client
from cs_utils import func, execute

LOG = logging.getLogger(__name__)


class AccessCephConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, ceph_admin_node: str):
        super().__init__(origin_view)
        self.selected_hostname = ceph_admin_node
        self.save_config()
        self.show()

    def save_config(self):
        CONF.openstack.ceph_admin_node = self.selected_hostname
        group, keys = 'openstack', ['ceph_admin_node']
        self.origin_view.save_CONF_group_keys(group, keys)

    def show(self):
        start_add_osd_view = [
            urwid.Text(f'开始对接Ceph分布式存储', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_add_osd_view))
        self.need_run_cmd_list.append(f'hostcli kolla access-ceph {self.selected_hostname}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class AccessCephNodeMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.ceph_admin_node = None
        self.show()

    def open_access_view(self, button: urwid.Button):
        AccessCephConsoleView(self, self.ceph_admin_node)
    
    def get_ceph_cluster_admin_node(self):
        try:
            current_host_name = func.get_current_node_hostname()
            ceph_nodes = rpc_client('get_ceph_nodes', hostname=current_host_name)
            for node in ceph_nodes:
                hostname = node['hostname']
                labels = node.get('labels') or []
                if '_admin' in labels:
                    LOG.info(f'ceph admin node is {hostname}')
                    return hostname
        except:
            pass
        LOG.error('not found ceph admin node, can not access ceph')

    def update_view(self):
        self.ceph_admin_node = self.get_ceph_cluster_admin_node()
        if self.ceph_admin_node:
            self.pile_view.widget_list = [urwid.Button('连接Ceph集群成功, 点击此按钮将开始对接', self.open_access_view, align="center")]
        else:
            self.pile_view.widget_list = [urwid.Text('连接Ceph集群失败, 请检查', align="center")]

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"检查Ceph分布式存储"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
