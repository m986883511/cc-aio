import urwid
import traceback
import logging

from pve_tui.config import CONF
from pve_tui import ui
from pve_tui.ui import my_widget, base_view
from pve_tui import jm_data, exception
from pve_admin.rpc import rpc_client
from cs_utils import func

LOG = logging.getLogger(__name__)


class AddOsdConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView, add_osd_config: dict):
        super().__init__(origin_view)
        self.selected_hostname = self.origin_view.origin_layout_button_label
        self.add_osd_config = add_osd_config
        self.osd_disks = ','.join(self.add_osd_config.get('osd')) or ''
        self.show()
    
    def get_cache_disk_config_string(self):
        # CACHE_DISK: name=sdd,bcache_size=140,db_size=40,max_backends=5
        cache_config = self.add_osd_config.get('cache')
        if not cache_config:
            return ""
        cache_disk = cache_config[0]
        return f'name={cache_disk},bcache_size={CONF.ceph.bcache_size},db_size={CONF.ceph.db_size},max_backends={CONF.ceph.max_backends_per_cache}'
    
    def get_ceph_cluster_nodes(self):
        try:
            current_host_name = func.get_current_node_hostname()
            ceph_nodes = rpc_client('get_ceph_nodes', hostname=current_host_name)
            return [i['hostname'] for i in ceph_nodes]
        except Exception as e:
            return []

    def show(self):
        start_add_osd_view = [
            urwid.Text(f'开始在{self.selected_hostname}添加OSD={self.osd_disks}', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_add_osd_view))
        ceph_cluster_nodes = self.get_ceph_cluster_nodes()
        self.need_run_cmd_list.append(f'pve_cli network check-network-connection {self.selected_hostname}')
        self.need_run_cmd_list.append(f'pve_cli ssh check-ssh-passwordless {self.selected_hostname}')
        self.need_run_cmd_list.append(f'pve_cli ceph check-ceph-node-network {self.selected_hostname}')
        if self.selected_hostname not in ceph_cluster_nodes:
            current_hostname = func.get_current_node_hostname()
            self.need_run_cmd_list.append(f'pve_cli ssh ssh-run-on-remote {self.selected_hostname} "pve_cli ceph set-ceph-registry-url {current_hostname}"')
            self.need_run_cmd_list.append(f'pve_cli ssh ssh-run-on-remote {self.selected_hostname} "pve_cli ceph pull-ceph-image"')
            self.need_run_cmd_list.append(f'pve_cli ssh scp-dir-to-remote-host {self.selected_hostname} /etc/ceph /etc')
            ceph_public_ip = f'192.222.13.{int(self.selected_hostname[4:])}'
            self.need_run_cmd_list.append(f"ceph orch host add {self.selected_hostname} {ceph_public_ip}")
        cache_disk = self.get_cache_disk_config_string()
        allow_hdd_as_osd_string = f'--allow_hdd_as_osd' if CONF.ceph.allow_hdd_as_osd else ''
        cmd = f'pve_cli ssh ssh-run-on-remote-via-popen {self.selected_hostname} "pve_cli disk add-osds {allow_hdd_as_osd_string} {self.osd_disks} \'{cache_disk}\'"'
        self.need_run_cmd_list.append(cmd)
        self.start_alarm()
        ui.top_layer.open_box(body)


class AddOsdConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.need_install_bcache_columns = []
        self.need_install_bcache_group = []
        self.need_install_osd_columns = []
        self.pile_bcache_view = urwid.Pile([urwid.Divider()])
        self.show()

    def start_add_osd(self, button):
        first_widget_list = [c.widget_list[0] for c in self.need_install_osd_columns]
        osd_checkbox_list = [c for c in first_widget_list if isinstance(c, urwid.CheckBox)]
        selected_osd_name_list = [i.label for i in osd_checkbox_list if i.state]
        if not selected_osd_name_list:
            self.note_msg = "必须选中一个数据盘才能继续操作"
            return
        temp_result = {'osd': selected_osd_name_list}
        if CONF.ceph.enable_bcache:
            selected_cache_name_list = [i.label for i in self.need_install_bcache_group if i.state]
            same_disk = list(set(selected_osd_name_list) & set(selected_cache_name_list))
            if same_disk:
                self.note_msg = f"{same_disk[0]}无法同时作为数据盘和缓存盘"
                return
            temp_result['cache'] = selected_cache_name_list
        AddOsdConsoleView(self, temp_result)

    def get_osd_colume(self, **kwargs):
        size = str(kwargs.get('size') or 0)
        size = size if size == jm_data.hostcli_disk_device_list_dec['size'] else func.convert_to_GT_str(int(size))
        osd = kwargs.get('osd') or ''
        if not osd and kwargs.get('checkbox'):
            _name = urwid.CheckBox(kwargs.get('name') or '') 
        else:
            _name = urwid.Text('    ' + kwargs.get('name') or '')
        return urwid.Columns(
            [
                _name,
                urwid.Text(size),
                urwid.Text(kwargs.get('media') or ''),
                urwid.Text(kwargs.get('model') or ''),
                urwid.Text(kwargs.get('rate') or '-'),
                urwid.Text(kwargs.get('form') or '-'),
                urwid.Text(osd),
            ]
        )

    def get_bcache_colume(self, **kwargs):
        size = str(kwargs.get('size') or 0)
        size = size if size == jm_data.hostcli_disk_cache_list_dec['size'] else func.convert_to_GT_str(int(size))
        backends = kwargs.get('backends')
        backends_detail = kwargs.get('backends_detail') if 'backends_detail' in kwargs else ' '.join(backends.keys())
        backends = backends if isinstance(backends, str) else str(len(backends) or '')
        return urwid.Columns(
            [
                urwid.RadioButton(self.need_install_bcache_group, kwargs.get('name')) if kwargs.get('radiobutton') else urwid.Text(kwargs.get('name')),
                urwid.Text(size),
                urwid.Text(kwargs.get('media')),
                urwid.Text(kwargs.get('model')),
                urwid.Text(backends),
                urwid.Text(backends_detail),
            ]
        )

    def get_bcache_config(self):
        config_list = [
            urwid.Divider(),
            urwid.AttrMap(urwid.Text("请选择缓存盘(bcache+db)", align="center"), "header"),
            urwid.Divider(),
            self.get_bcache_colume(**jm_data.hostcli_disk_cache_list_dec),
            urwid.Divider("-"),
        ]
        if self.need_install_bcache_columns:
            config_list.extend([urwid.Pile([*self.need_install_bcache_columns])])
        return config_list

    def get_hostcli_disk_device_list(self):
        hostname = self.origin_layout_button_label
        try:
            return rpc_client('list_data_disks', hostname=hostname)
        except Exception as e:
            self._note_alarm_time = 3600 * 24
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'获取{hostname}的所有数据盘信息')
            return []

    def get_hostcli_disk_cache_list(self):
        hostname = self.origin_layout_button_label
        try:
            return rpc_client('list_cache_disks', hostname=hostname)
        except Exception as e:
            self._note_alarm_time = 3600 * 24
            LOG.error(traceback.format_exc())
            self.note_msg = exception.get_hostrpc_what_error(str(e), f'获取{hostname}的所有缓存盘信息')
            return []

    def update_view(self):
        self.need_install_bcache_columns = []
        self.need_install_osd_columns = []
        hostcli_disk_device_list = self.get_hostcli_disk_device_list()

        for device in hostcli_disk_device_list:
            colume = self.get_osd_colume(checkbox=True, **device)
            self.need_install_osd_columns.append(colume)
        if self.need_install_osd_columns:
            self.pile_view.widget_list = [*self.need_install_osd_columns]
        else:
            self.pile_view.widget_list = [urwid.Divider()]

        if CONF.ceph.enable_bcache:
            hostcli_disk_cache_list = self.get_hostcli_disk_cache_list()
            for device in hostcli_disk_cache_list:
                colume = self.get_bcache_colume(radiobutton=True, **device)
                self.need_install_bcache_columns.append(colume)
            config_list = self.get_bcache_config()
            self.pile_bcache_view.widget_list = config_list
        else:
            self.pile_bcache_view.widget_list = [urwid.Divider()]

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.AttrMap(urwid.Text("请选择数据盘(osd)", align="center"), "header"),
                urwid.Divider(),
                self.get_osd_colume(**jm_data.hostcli_disk_device_list_dec),
                urwid.Divider("-"),
                self.pile_view,
                self.pile_bcache_view,
                urwid.Divider(),
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.Button("开始添加", self.start_add_osd, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))


class OsdAddNodeMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.node_buttons = []
        self.show()

    def open_network_view(self, button):
        AddOsdConfigView(button)
    
    def update_view(self):
        self.node_buttons = []
        hostnames = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        for host in hostnames:
            self.node_buttons.append(urwid.Button(host, self.open_network_view, align="center"))
        if self.node_buttons:
            self.pile_view.widget_list = self.node_buttons
        else:
            self.pile_view.widget_list = [urwid.Text(f"没有已安装基础环境的节点", align="center")]

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
