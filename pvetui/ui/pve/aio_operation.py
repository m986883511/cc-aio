import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cc_utils import execute, func

from .config import disk, igd

LOG = logging.getLogger(__name__)

class PveAllInOneOperationView(base_view.BaseConfigView):
    def __init__(self, button: urwid.Button):
        super().__init__(button)
        self.menu_buttons = []
        self.services_dict = {
            'disk':{
                'text': 'disk (硬盘挂载/直通/格式化)',
                'view': disk.DiskConfigView,
            },
            'igd':{
                'text': 'igd (核显直通配置)',
                'view': igd.IgdConfigView,
            },
        }
        self.show()

    def update_view(self):
        self.menu_buttons = []
        for key, value_dict in self.services_dict.items():
            text = value_dict['text']
            view = value_dict['view']
            self.menu_buttons.append(urwid.AttrMap(urwid.Button(text, view, align="center"), None, focus_map='buttn'))
        self.pile_view.widget_list = self.menu_buttons

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text(f"{self.origin_layout_button_label}"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.AttrMap(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), None, focus_map='buttn')
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))