import logging

import urwid

from pve_tui.config import CONF
from pve_tui import ui, jm_data
from pve_tui.ui import my_widget, base_view
from cs_utils import func

LOG = logging.getLogger(__name__)


class OpenstackDeployConsole(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.all_nodes = self.get_all_nodes()
        self.current_hostname = func.get_current_node_hostname()
        self.default_version_path = '/opt/astute/jmversion'
        self.show()

    def get_all_nodes(self):
        controls = func.get_string_split_list(CONF.openstack.control_nodes, split_flag=',')
        controls.sort()
        return controls

    def result_button_click(self, button):
        return ui.return_last(button)

    def show(self):
        start_del_osd_view = [
            urwid.Text(f'开始部署OpenStack集群', align='center'),
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_del_osd_view))
        if not self.all_nodes:
            self.need_run_cmd_list.append(f'echo "please save openstack config first!"')
            self.need_run_cmd_list.append(f'exit 1')
        for hostname in self.all_nodes:
            self.need_run_cmd_list.append(f'pve_cli network check-network-connection {hostname}')
            self.need_run_cmd_list.append(f'pve_cli ssh check-ssh-passwordless {hostname}')
            self.need_run_cmd_list.append(f'pve_cli network check-kolla-interface-exist {hostname}')
        self.need_run_cmd_list.append(f'pve_cli kolla install-kolla-ansible')
        for hostname in self.all_nodes:
            if hostname != self.current_hostname:
                self.need_run_cmd_list.append(f'pve_cli ssh rsync-dir-to-remote-host {hostname} {self.default_version_path} --progress')
                self.need_run_cmd_list.append(f'pve_cli ssh ssh-run-on-remote-via-popen {hostname} "pve_cli kolla install-kolla-ansible"')
        self.need_run_cmd_list.append(f'pve_cli kolla deploy')
        self.start_alarm()
        ui.top_layer.open_box(body)
