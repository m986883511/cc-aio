import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from pvetui.utils import get_other_nodes_ntp_server_config
from cg_utils import execute, func

LOG = logging.getLogger(__name__)


class InstallBaseEnvConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_install_base_env_view = [
            urwid.Text(f'开始安装', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_base_env_view))
        current_hostname = func.get_current_node_hostname()
        self.need_run_cmd_list.append(f'cg-hostcli host install-base-env --host {current_hostname}')
        self.need_run_cmd_list.append(f'cg-hostcli pve open-ipv6-support')
        if CONF.base_env.need_reboot_flag:
            self.need_run_cmd_list.append(f'echo "立即重启中!!!"')
        # ntp config
        self.start_alarm()
        ui.top_layer.open_box(body)

    def task_success_callback(self):
        origin_need_reboot_flag = CONF.base_env.need_reboot_flag
        CONF.base_env.installed_flag = True
        CONF.base_env.need_reboot_flag = False
        group, keys = 'base_env', ['installed_flag', 'need_reboot_flag']
        self.origin_view.save_CONF_group_keys(group, keys)
        if origin_need_reboot_flag:
            execute.execute_command('reboot -f')


class InstallBaseEnvView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.text_list = [
            "使用超哥提供本地APT源",
            "使用超哥提供本地PIP源",
            '安装基础依赖包',
            '开启IPv6支持',
            '开启cg-hostrpc主机管理服务',
        ]
        self.show()

    def start_install_env(self, button: urwid.Button):
        group, keys = 'base_env', ['installed_flag', 'root_min_space', 'need_reboot_flag']
        self.save_CONF_group_keys(group, keys)
        InstallBaseEnvConsoleView(self)
    
    def reboot_flag_change(self, obj: urwid.CheckBox, value: bool):
        CONF.base_env.need_reboot_flag = value

    def update_view(self):
        widget_list = []
        widget_list.append(urwid.Padding(urwid.Text(f'将安装以下内容:', align="left"), left=4, right=8))
        for i, text in enumerate(self.text_list):
            widget_list.append(urwid.Padding(urwid.Text(f'{i+1}. {text}', align="left"), left=8, right=8))
        widget_list.append(urwid.Divider())
        widget_list.append(urwid.Padding(urwid.CheckBox('安装成功后立即重启', state=CONF.base_env.need_reboot_flag, on_state_change=self.reboot_flag_change), left=4, right=4, min_width=10))
        widget_list.append(urwid.Divider())
        self.pile_view.widget_list = [*widget_list]

    def show(self):
        self.update_view()
        installed_str = " (已安装)" if CONF.base_env.installed_flag else "" 
        ii = urwid.Pile(
            [
                urwid.Text(self.origin_layout_button_label),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.Button(f"保存配置并开始安装{installed_str}", self.start_install_env, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                )
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
