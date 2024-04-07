from __future__ import annotations
import os
os.environ['IN_TUI'] = 'True'
import sys
import logging

import urwid

from cc_utils import func, execute, AUTHOR_NAME
func.set_simple_log(f'/var/log/{AUTHOR_NAME}/aio.log')
from pvetui import ui, utils
from pvetui.ui import network, base_env, pve
from pvetui.config import CONF, AIO_CONF_PATH


LOG = logging.getLogger(__name__)


def menu_button(caption, callback):
    button = urwid.Button(caption, align='center')
    urwid.connect_signal(button, 'click', callback)
    return urwid.AttrMap(button, None, focus_map='reversed')


def sub_menu(caption, choices):
    contents = menu(caption, choices)
    def open_menu(button):
        return ui.top_layer.open_box(contents)
    return menu_button(caption, open_menu)


def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    body.extend(choices)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


class CascadingBoxes(urwid.WidgetPlaceholder):
    max_box_levels = 5

    def __init__(self, box):
        super().__init__(urwid.SolidFill(' '))
        self.box_level = 0
        self.open_box(box)

    def open_box(self, box):
        self.original_widget = urwid.Overlay(urwid.LineBox(box),
            self.original_widget,
            align='center', width=(urwid.WHSettings.RELATIVE, 95),
            valign='middle', height=(urwid.WHSettings.RELATIVE, 95),
            min_width=24, min_height=8,
            left=self.box_level * 1,
            right=(self.max_box_levels - self.box_level - 1) * 1,
            top=self.box_level * 2,
            bottom=(self.max_box_levels - self.box_level - 1) * 1)
        self.box_level += 1

    def keypress(self, size, key):
        if key == 'esc' and self.box_level > 1:
            self.original_widget = self.original_widget[0]
            self.box_level -= 1
        elif key == 'esc' and self.box_level == 1:
            raise urwid.ExitMainLoop()
        else:
            return super().keypress(size, key)

    def return_fn(self):
        self.original_widget = self.original_widget[0]
        self.box_level -= 1


def get_pip_install_truseted_host():
    flag, content = execute.crudini_get_config(
        '/root/.config/pip/pip.conf', 
        'install', 
        'trusted-host',
        check_file_exist=False)
    if flag == 0:
        if content not in ['localhost', '127.0.0.1']:
            print(f'please goto {content} run acd, current node no config history!')
            exit()


def run_depend_tasks():
    if len(sys.argv) != 1:
        utils.custom_cmd(sys.argv)
    # get_pip_install_truseted_host()
    func.create_conf_file(AIO_CONF_PATH)
    CONF(default_config_files = [AIO_CONF_PATH])


def main():
    run_depend_tasks()
    palette = [
        ("body", "black", "light gray", "standout"),
        ("reverse", "light gray", "black"),
        ("header", "white", "dark red", "bold"),
        ("important", "dark blue", "light gray", ("standout", "underline")),
        ("editfc", "white", "dark blue", "bold"),
        ("editbx", "light gray", "dark blue"),
        ("editcp", "black", "light gray", "standout"),
        ("bright", "dark gray", "light gray", ("bold", "standout")),
        ("buttn", "black", "dark cyan"),
        ("buttnf", "white", "dark blue", "bold"),
    ]
    menu_top = menu(CONF.tui_title, [
        menu_button('配置物理网络', pve.NetworkConfigView),
        menu_button('安装基础包和配置', base_env.InstallBaseEnvView),
        menu_button('安装ALL-IN-ONE服务', pve.PveAllInOneServicesView),
        menu_button('操作ALL-IN-ONE设备', pve.PveAllInOneOperationView),
        urwid.Divider(),
        menu_button(CONF.return_last_string, ui.exit_program),
    ])
    ui.top_layer = CascadingBoxes(menu_top)
    ui.top_loop = urwid.MainLoop(ui.top_layer, palette=palette)
    ui.top_loop.run()


if __name__ == '__main__':
    main()
