import logging
import string
import traceback

import urwid

from pvetui.config import CONF
from pvetui import ui, jm_data
from pvetui.ui import my_widget, base_view
from cs_utils import execute, func
from hostadmin.rpc import rpc_client
from hostadmin.business import Usage

LOG = logging.getLogger(__name__)


class SelectNodeView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.env_nodes_edit_obj = None
        self.current_hostname = func.get_current_node_hostname()
        self.show()

    def save_config(self, button):
        try:
            all_nodes_number = self.calc_env_nodes()
        except Exception as e:
            self.note_msg = f'保存失败, 请检查您的输入, {str(e)}'
            return
        hostnames = [f'host{i:03d}' for i in all_nodes_number]
        LOG.info(f'calc env hostnames={hostnames}')
        if not hostnames:
            self.note_msg = '必须选择节点才能继续操作'
            return
        if self.current_hostname not in hostnames:
            self.note_msg = f'已选择节点中必须包含当前节点({self.current_hostname}) 才能继续操作'
            return
        selected_name_list_str = ','.join(hostnames)
        CONF.base_env.all_nodes = selected_name_list_str
        CONF.base_env.all_nodes_edit_str = self.env_nodes_edit_obj.get_edit_text()
        installed_env_nodes = func.get_string_split_list(CONF.base_env.installed_nodes, split_flag=',')
        installed_env_nodes = [i for i in installed_env_nodes if i in hostnames]
        CONF.base_env.installed_nodes = ','.join(installed_env_nodes)
        group, keys = 'base_env', ['all_nodes', 'all_nodes_edit_str', 'installed_nodes']
        self.save_CONF_group_keys(group, keys)
        ui.return_last(button)

    def calc_env_nodes(self):
        text = self.env_nodes_edit_obj.get_edit_text()
        text_list = func.get_string_split_list(text, split_flag=',')
        all_nodes_number = []
        for i in text_list:
            if '-' in i:
                start_end = func.get_string_split_list(i, split_flag='-')
                if len(start_end) != 2:
                    raise Exception(f'"{i}" 的格式有误')
                start = int(start_end[0])
                end = int(start_end[1])
                if start < 1 or end > 240:
                    raise Exception(f'ip范围1-240')
                if not end > start:
                    raise Exception(f'"{i}" 的格式有误')
                all_nodes_number.extend(list(range(start, end+1)))
            else:
                if int(i) < 0 or int(i) > 240:
                    raise Exception(f'ip范围1-240')
                all_nodes_number.append(int(i))
        all_nodes_number = list(set(all_nodes_number))
        return all_nodes_number

    def _env_nodes_change_func(self, edit_obj: my_widget.TextEdit, current_value):
        current_value = current_value or ''
        available_acsii = string.digits + ',-'
        for i in current_value:
            if i not in available_acsii:
                edit_obj.set_caption(('header', [ ("white", edit_obj.origin_caption), f"存在非法字符{i}", ("white", " "), ]))
                return
        edit_obj.set_caption(edit_obj.origin_caption)

    def update_view(self):
        if not CONF.base_env.all_nodes_edit_str:
            CONF.base_env.all_nodes_edit_str = self.current_hostname[4:]
        self.env_nodes_edit_obj = my_widget.TextEdit(("white",'请输入节点编号: '), CONF.base_env.all_nodes_edit_str, self._env_nodes_change_func)
        self.pile_view.widget_list = [urwid.AttrMap(self.env_nodes_edit_obj, "editbx", "editfc")]

    def show(self):
        self.update_view()
        ii = urwid.Pile(
            [
                urwid.Text("安装基础软件包的节点列表"),
                urwid.Divider(),
                urwid.Text("说明:"),
                urwid.Text("    1. 编号范围是1-240"),
                urwid.Text("    2. 多个编号用英文逗号分隔, 用英文中划线表述一段编号"),
                urwid.Text("    3. 例如，001,002,003, 多个连续节点：011-020"),
                urwid.Divider(),
                self.pile_view,
                urwid.Divider(),
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.Button("确认并保存", self.save_config, align="center"), align="center", left=1, right=1),
                        urwid.Padding(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(ii, valign='top'))
