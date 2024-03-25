from __future__ import annotations
import os
import sys
import logging

import urwid

from cs_utils import func, execute
from pvetui import ui, utils
from pvetui.ui import ceph, network, base_env, openstack
from pvetui.config import CONF, PVE_TUI_CONF_PATH


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
        # elif key == 'esc' and self.box_level == 1:
        #     raise urwid.ExitMainLoop()
        else:
            return super().keypress(size, key)

    def return_fn(self):
        self.original_widget = self.original_widget[0]
        self.box_level -= 1


def get_pip_install_truseted_host():
    cmd = 'crudini --get /root/.config/pip/pip.conf install trusted-host'
    flag, content = execute.execute_command(cmd)
    if flag == 0:
        if content not in ['localhost', '127.0.0.1']:
            print(f'please goto {content} run acd, current node no config history!')
            exit()


def run_depend_tasks():
    func.set_simple_log('/var/log/astute/pvetui.log')
    if len(sys.argv) != 1:
        utils.custom_cmd(sys.argv)
    get_pip_install_truseted_host()
    func.create_conf_file(PVE_TUI_CONF_PATH)
    CONF(default_config_files = [PVE_TUI_CONF_PATH])


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
    menu_top = menu(CONF.pvetui_title, [
        sub_menu('安装基础环境', [
            menu_button('编辑节点列表', base_env.SelectNodeView),
            menu_button('选择节点并安装', base_env.InstallBaseEnvView),
            urwid.Divider(),
            urwid.Button(CONF.return_last_string, ui.return_last, align='center')
        ]),
        menu_button('配置物理网络', network.NetworkNodeMenu),
        sub_menu('安装Ceph分布式存储', [
            menu_button('编辑默认配置', ceph.CephClusterConfigView),
            menu_button('部署Ceph集群', ceph.DeployCephConsoleView),
            menu_button('添加OSD', ceph.OsdAddNodeMenu),
            menu_button('移除OSD', ceph.OsdDelNodeMenu),
            urwid.Divider(),
            menu_button(CONF.return_last_string, ui.return_last),
        ]),
        sub_menu('安装OpenStack云计算平台', [
            menu_button('编辑默认配置', openstack.OpenstackClusterConfigView),
            menu_button('部署OpenStack集群', openstack.OpenstackDeployConsole),
            menu_button('更新OpenStack配置', openstack.UpdateOpenstackConfigView),
            menu_button('添加计算节点', openstack.AddComputeNodeMenu),
            menu_button('对接Ceph分布式存储', openstack.AccessCephNodeMenu),
            urwid.Divider(),
            menu_button(CONF.return_last_string, ui.return_last),
        ]),
        urwid.Divider(),
        menu_button('退出', ui.exit_program),
    ])
    ui.top_layer = CascadingBoxes(menu_top)
    ui.top_loop = urwid.MainLoop(ui.top_layer, palette=palette)
    ui.top_loop.run()


if __name__ == '__main__':
    main()
