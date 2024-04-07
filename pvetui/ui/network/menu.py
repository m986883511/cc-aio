import logging

import urwid

from pvetui.config import CONF
from pvetui import ui, jm_data
from pvetui.ui import my_widget, base_view
from cc_utils import func
from .config import NetworkConfigView

LOG = logging.getLogger(__name__)


class NetworkMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.network_menu_buttons = []
        self.show()

    def open_config_network_view(self, button):
        NetworkConfigView(self, button)

    def update_view(self):
        self.network_menu_buttons = []
        for key, value in jm_data.network_config_menu.items():
            self.network_menu_buttons.append(urwid.Button(key, self.open_config_network_view, align="center"))
        self.pile_view.widget_list = self.network_menu_buttons

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"选择{self.origin_layout_button_label}网络"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))


class NetworkNodeMenu(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.node_buttons = []
        self.show()

    def open_network_view(self, button):
        NetworkMenu(button)
    
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
