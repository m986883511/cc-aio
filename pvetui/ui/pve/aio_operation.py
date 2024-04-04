import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from cg_utils import execute, func

from .config import disk, igd

LOG = logging.getLogger(__name__)

class PveAllInOneOperationView(base_view.BaseConfigView):
    def __init__(self, button: urwid.Button):
        super().__init__(button)
        self.menu_buttons = []
        self.services_dict = {
            'igd':{
                'text': 'igd (核显直通)',
                'view': igd.IgdConfigView,
            },
            'disk':{
                'text': 'disk (挂载到samba)',
                'view': disk.DiskConfigView,
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
                urwid.Text(f"{self.origin_layout_button_label}"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Button(CONF.return_last_string, ui.return_last, align="center"),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))