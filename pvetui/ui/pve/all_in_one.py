import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func

from .services import samba, alist, public_ip, wireguard

LOG = logging.getLogger(__name__)

class PveAllInOneServicesView(base_view.BaseConfigView):
    def __init__(self, origin_view: base_view.BaseConfigView, button: urwid.Button):
        self.origin_view = origin_view
        self.selected_hostname = button.label
        super().__init__(button)
        self.menu_buttons = []
        self.services_dict = {
            'samba':{
                'text': 'samba (windows中的共享网络盘)',
                'view': samba.SambaConfigView,
            },
            'alist':{
                'text': 'alist (浏览器下载文件或者看视频)',
                'view': alist.AlistConfigView,
            },
            'public_ip':{
                'text': 'public_ip (运营商临时公网ip的获取方式)',
                'view': public_ip.PublicIpConfigView,
            },
            'wireguard':{
                'text': 'wireguard (内网穿透可以远程访问家里设备)',
                'view': wireguard.WireguardConfigView,
            },
        }
        self.show()

    def update_view(self):
        self.menu_buttons = []
        for key, value_dict in self.services_dict.items():
            text = value_dict['text']
            view = value_dict['view']
            self.menu_buttons.append(urwid.Button(text, view, align="center"))
        self.pile_view.widget_list = self.menu_buttons

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"在{self.origin_layout_button_label}配置服务"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))


class PveAllInOneView(base_view.BaseConfigView):
    def __init__(self, button: urwid.Button):
        super().__init__(button)
        self.need_install_env_buttons = []
        self.installed_env_hosts = []
        self.original_select_nodes = []
        self.show()

    def open_services_view(self, button: urwid.Button):
        PveAllInOneServicesView(self, button)

    def update_view(self):
        self.node_buttons = []
        hostnames = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        for host in hostnames:
            self.node_buttons.append(urwid.Button(host, self.open_services_view, align="center"))
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
