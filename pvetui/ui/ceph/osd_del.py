import logging

import urwid

from pvetui.config import CONF
from pvetui import ui, jm_data, exception
from pvetui.ui import my_widget, base_view
from cg_utils import func
from hostadmin.rpc import rpc_client

LOG = logging.getLogger(__name__)


class DeleteOsdConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, selected_osd_name_list):
        super().__init__(origin_view)
        self.selected_hostname = self.origin_view.origin_layout_button_label
        self.selected_osd_name_list = selected_osd_name_list
        self.selected_osd_name_string = ','.join(self.selected_osd_name_list)
        self.show()
    
    def show(self):
        start_del_osd_view = [
            urwid.Text(f'开始在{self.selected_hostname}移除OSD={self.selected_osd_name_string}', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_del_osd_view))
        self.need_run_cmd_list.append(f'cg-hostcli network check-network-connection {self.selected_hostname}')
        self.need_run_cmd_list.append(f'cg-hostcli ssh check-ssh-passwordless {self.selected_hostname}')
        cmd = f'cg-hostcli ssh ssh-run-on-remote-via-popen {self.selected_hostname} "cg-hostcli disk remove-osds {self.selected_osd_name_string}"'
        self.need_run_cmd_list.append(cmd)
        self.start_alarm()
        ui.top_layer.open_box(body)


class DeleteOsdConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.need_del_osd_columns = []
        self.show()

    def get_osd_colume(self, **kwargs):
        size = str(kwargs.get('size') or 0)
        size = size if size == jm_data.hostcli_disk_osd_list_dec['size'] else func.convert_to_GT_str(int(size))
        osd = kwargs.get('osd') or ''
        return urwid.Columns(
            [
                urwid.CheckBox(osd) if kwargs.get('checkbox') else urwid.Text(osd),
                urwid.Text(kwargs.get('data_disk') or ''),
                urwid.Text(size),
                urwid.Text(kwargs.get('media') or ''),
                urwid.Text(kwargs.get('bcache_part') or ''),
                urwid.Text(kwargs.get('db_part') or ''),
                urwid.Text(kwargs.get('data_lv') or ''),
                urwid.Text(kwargs.get('db_lv') or ''),
            ]
        )

    def update_view(self):
        self.need_del_osd_columns = []
        hostcli_disk_osd_list = self.get_hostcli_disk_osd_list()
        for key, osd in hostcli_disk_osd_list.items():
            osd['osd'] = key
            column = self.get_osd_colume(checkbox=True, **osd)
            self.need_del_osd_columns.append(column)
        if self.need_del_osd_columns:
            self.pile_view.widget_list = [*self.need_del_osd_columns]
        else:
            self.pile_view.widget_list = [urwid.Divider()]

    def start_del_osd(self, button):
        osd_checkbox_list = [c.widget_list[0] for c in self.need_del_osd_columns]
        selected_osd_name_list = [i.label for i in osd_checkbox_list if i.state]
        if not selected_osd_name_list:
            self.note_msg = "必须选中一个OSD才能继续操作"
            return
        DeleteOsdConsoleView(self, selected_osd_name_list)

    def get_hostcli_disk_osd_list(self):
        hostname = self.origin_layout_button_label
        try:
            return rpc_client('list_osds', hostname=hostname)
        except Exception as e:
            self._note_alarm_time = 3600 * 24
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'获取{hostname}的所有osd信息')
            return []

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.AttrMap(urwid.Text("请选择OSD:", align="center"), "header"),
                urwid.Divider(),
                self.get_osd_colume(**jm_data.hostcli_disk_osd_list_dec),
                urwid.Divider("-"),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.AttrMap(
                    urwid.Columns(
                        [
                            urwid.Padding(urwid.Button("开始移除", self.start_del_osd, align="center"), align="center", left=1, right=1),
                            urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                        ]
                    ),
                    "footer"
                )
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))


class OsdDelNodeMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.node_buttons = []
        self.show()

    def open_network_view(self, button):
        DeleteOsdConfigView(button)
    
    def get_ceph_cluster_nodes(self):
        try:
            current_host_name = func.get_current_node_hostname()
            ceph_nodes = rpc_client('get_ceph_nodes', hostname=current_host_name)
            return [node['hostname'] for node in ceph_nodes]
        except:
            err_msg ='get ceph cluster nodes failed, err={str(e)}'
            LOG.error(err_msg)
            self._note_alarm_time = 3600 * 24
            self.note_msg = '连接Ceph集群失败, 请检查'
        return []

    def update_view(self):
        self.node_buttons = []
        hostnames = self.get_ceph_cluster_nodes()
        for host in hostnames:
            self.node_buttons.append(urwid.Button(host, self.open_network_view, align="center"))
        if self.node_buttons:
            self.pile_view.widget_list = self.node_buttons
        else:
            self.pile_view.widget_list = [urwid.Text(f"没有Ceph节点", align="center")]

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"选择节点"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
