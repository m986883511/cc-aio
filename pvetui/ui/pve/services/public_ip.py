import time
import uuid
import logging

import urwid

from pvetui.config import CONF
from pvetui import ui
from pvetui.ui import my_widget, base_view
from hostadmin.rpc import rpc_client
from cc_utils import execute, func, AUTHOR_NAME, AUTHOR_ZH_NAME

LOG = logging.getLogger(__name__)


class PublicIpTestConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.public_ip_simple_http_server_url = self.get_test_http_server_url()
        self.show()

    def get_test_http_server_url(self):
        if CONF.public_ip.ipv4_or_ipv6 == 'ipv4':
            url = f'http://{self.origin_view.public_ipv4}:{CONF.public_ip.simple_http_server_port}'
        else:
            url = f'http://[{self.origin_view.public_ipv6}]:{CONF.public_ip.simple_http_server_port}'
        return url

    def task_success_callback(self):
        self.received_output('\n 你刚刚使用手机的流量, 访问到了你家里的局域网! 所以!!!')
        self.received_output('\n 恭喜! 你的环境可以使用wireguard搭建虚拟专用网络! 在外面就像回家一下!'*3 + '\n')

    def show(self):
        start_install_alist_view = [
            urwid.Text(f'开始测试公网IP是否可用', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button_attrmap,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_alist_view))
        self.need_run_cmd_list.append(f'cc-hostcli service show-qrencode --text {self.public_ip_simple_http_server_url}')
        self.need_run_cmd_list.append(f'echo -e 请关闭手机无线网, 使用相机扫码打开网址, 能打开网址说明公网IP测试成功!')
        self.need_run_cmd_list.append(f'cc-hostcli service create-block-simple-api-service {CONF.public_ip.simple_http_server_port}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class PublicIpConfigConsoleView(base_view.BaseConsoleView):
    def __init__(self, origin_view: base_view.BaseConfigView):
        super().__init__(origin_view)
        self.show()

    def show(self):
        start_install_alist_view = [
            urwid.Text(f'配置public_ip相关服务', align='center'), 
            urwid.Divider(), 
            self.output_widget,
            self.result_button_attrmap,
        ]
        body = urwid.ListBox(urwid.SimpleFocusListWalker(start_install_alist_view))
        start_or_stop = 'start' if CONF.public_ip.use_check_robot else 'stop'
        self.need_run_cmd_list.append(f'cc-hostcli service start-or-stop-listen-public-ip-change-rebot {start_or_stop}')
        start_or_stop = 'start' if CONF.public_ip.use_ddns else 'stop'
        self.need_run_cmd_list.append(f'cc-hostcli service start-or-stop-aliyun-ddns {start_or_stop}')
        self.start_alarm()
        ui.top_layer.open_box(body)


class PublicIpConfigView(base_view.BaseConfigView):
    def __init__(self, button):
        super().__init__(button)
        self.pve_ip = func.get_hostname_map_ip()
        self.ipv4_ipv6_choose_list = []
        self.ip_types = ['ipv4', 'ipv6']
        self.ip_type_radio_buttons = []
        self.public_ipv4 = ''
        self.public_ipv6 = ''
        self.show()

    def save_config(self, button):
        group, keys = 'public_ip', [
            'ipv4_or_ipv6', 'use_ddns', 'use_check_robot', 'accessKeyId', 'accessKeySecret', 'rr',
            'simple_http_server_port', 'feishu_webhook_uuid', 'regionId', 'domain', 'public_ip_txt_path'
        ]
        self.save_CONF_group_keys(group, keys)
        # ui.return_last(button)
        PublicIpConfigConsoleView(self)
    
    def ipv4_or_ipv6_button_change(self, obj: urwid.RadioButton, value: bool):
        if obj.label == 'ipv6':
            CONF.public_ip.ipv4_or_ipv6 = 'ipv6' if value else 'ipv4'
            self.update_view()
        
    def use_ddns_change(self, obj: urwid.CheckBox, value: bool):
        CONF.public_ip.use_ddns = value
        self.update_view()

    def use_check_robot_change(self, obj: urwid.CheckBox, value: bool):
        CONF.public_ip.use_check_robot = value
        self.update_view()

    def access_key_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessKeyId = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessKeyId = current_value

    def access_secret_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.accessKeySecret = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.accessKeySecret = current_value
    
    def domain_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.domain = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.domain = current_value

    def rr_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.rr = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.rr = current_value

    def region_id_change(self, edit_obj: urwid.Edit, current_value: str):
        if not current_value:
            edit_obj.set_caption(('header', [f"请输入", ("white", " "), ]))
            CONF.public_ip.regionId = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.regionId = current_value
    
    def feishu_webhook_uuid_change(self, edit_obj: urwid.Edit, current_value: str):
        def is_valid_uuid(text):
            try:
                uuid_obj = uuid.UUID(text)
                return str(uuid_obj) == text
            except ValueError:
                return False
        if not current_value:
            CONF.public_ip.feishu_webhook_uuid = ''
            return
        if not current_value.isascii():
            edit_obj.set_caption(('header', [f"存在不是acsii的字符", ("white", " "), ]))
        elif not is_valid_uuid(current_value):
            edit_obj.set_caption(('header', [f"输入的还不是uuid", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            CONF.public_ip.feishu_webhook_uuid = current_value
    
    def get_public_ipv6(self):
        try:
            network_dict = rpc_client('get_pve_main_bridge_nics')
        except Exception as e:
            err = f'读取pve的vmbr0网络配置, 请联系开发者{AUTHOR_ZH_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return
        ipv6_list = network_dict.get('ipv6') or []
        ipv6s = [i.get('ip') for i in ipv6_list if 'ip' in i]
        ipv6 = func.get_public_ipv6_from_list(ipv6s)
        if '/' in ipv6:
            ipv6 = func.get_string_split_list(ipv6, split_flag='/')[0]
        return ipv6
    
    def get_public_ipv4(self):
        try:
            public_ip = func.get_public_ipv4(timeout=3)
        except Exception as e:
            err = f'读取public_ipv4失败, 请联系开发者{AUTHOR_ZH_NAME}, err={str(e)}'
            LOG.error(err)
            self.note_msg = err
            return
        return public_ip

    def update_view(self):
        widget_list = []
        self.ip_type_radio_buttons = []
        self.ipv4_ipv6_choose_list = []
        for item in self.ip_types:
            flag = item == CONF.public_ip.ipv4_or_ipv6
            self.ip_type_radio_buttons.append(urwid.AttrMap(urwid.RadioButton(self.ipv4_ipv6_choose_list, item, state=flag, on_state_change=self.ipv4_or_ipv6_button_change), None, focus_map='buttn'))
        ip_type_column = urwid.Columns([
            urwid.Padding(urwid.Text("选择一种公网ip方式:", align="left"), left=4, right=4, min_width=10),
            *self.ip_type_radio_buttons
        ])
        widget_list.append(ip_type_column)
        if CONF.public_ip.ipv4_or_ipv6 == 'ipv4':
            if self.public_ipv4:
                public_ip = self.public_ipv4
            else:
                public_ip = self.get_public_ipv4()
                if public_ip:
                    self.public_ipv4 = public_ip
                else:
                    public_ip = "获取公网ipv4地址失败! 你真的联网了吗?"
            widget_list.append(urwid.Padding(urwid.Text(f"公网IPv4地址为: {public_ip}", align="left"), left=8, right=4, min_width=10))
            widget_list.append(urwid.Padding(urwid.Text(f"PVE的内网IPv4为: {self.pve_ip}", align="left"), left=8, right=4, min_width=10))
        else:
            if self.public_ipv6:
                public_ip = self.public_ipv6
            else:
                public_ip = self.get_public_ipv6()
                if public_ip:
                    self.public_ipv6 = public_ip
                else:
                    public_ip = "获取公网ipv6地址失败! 你真的联网了吗? 你的光猫开IPv6了吗?"
            widget_list.append(urwid.Padding(urwid.Text(f"PVE的公网IPv6为: {public_ip}", align="left"), left=8, right=4, min_width=10))
        if (CONF.public_ip.ipv4_or_ipv6 == 'ipv4' and self.public_ipv4) or (CONF.public_ip.ipv4_or_ipv6 == 'ipv6' and self.public_ipv6):
            if CONF.public_ip.ipv4_or_ipv6 == 'ipv4':
                tishi = f"请用普通用户登录光猫, 做端口映射, 光猫端口{CONF.public_ip.simple_http_server_port}->{self.pve_ip}:{CONF.public_ip.simple_http_server_port}"
            else:
                tishi = f"请用超级管理员用户登录光猫, 将防火墙等级改为低"
            widget_list.append(urwid.Padding(urwid.AttrMap(urwid.Button(f"运行自建的API服务来测试公网IP是否可用 ({tishi})", self.start_public_ip_test, align="left", wrap='clip'), None, focus_map='buttn'), align="left", left=8, right=1),)
        widget_list.append(urwid.Divider())
        widget_list.append(urwid.Padding(urwid.AttrMap(urwid.CheckBox('是否开启公网IP变更检查服务(每分钟查一次)(推荐开):', state=CONF.public_ip.use_check_robot, on_state_change=self.use_check_robot_change), None, focus_map='buttn'), left=4, right=4, min_width=10))
        if CONF.public_ip.use_check_robot:
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("飞书WebHook UUID (若配置将上报变化的公网IP地址):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.feishu_webhook_uuid, self.feishu_webhook_uuid_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
        widget_list.append(urwid.Divider())
        widget_list.append(urwid.Padding(urwid.AttrMap(urwid.CheckBox('是否使用阿里云ddns (依赖公网IP变更检查服务):', state=CONF.public_ip.use_ddns, on_state_change=self.use_ddns_change), None, focus_map='buttn'), left=4, right=4, min_width=10))
        if CONF.public_ip.use_ddns:
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名rr (域名前缀, 就像www):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.rr, self.rr_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名domain (没有前缀, 就像baidu.com):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.domain, self.domain_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名regionId (看帮助文档查一下):", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.regionId, self.region_id_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名accessKeyId:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.accessKeyId, self.access_key_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
            widget_list.append(urwid.Padding(
                urwid.Columns(
                    [
                        urwid.Text("域名accessKeySecret:", align="left"),
                        urwid.AttrMap(my_widget.TextEdit("", CONF.public_ip.accessKeySecret, self.access_secret_change), "bright", "buttn"),
                    ]
                ), left=8, right=10
            ))
        self.pile_view.widget_list = widget_list

    def start_public_ip_test(self, button):
        PublicIpTestConsoleView(self)

    def show(self):
        self.update_view()
        body = urwid.Pile(
            [
                urwid.Text("编辑公网ip配置", align="center"),
                urwid.Divider(),
                self.pile_view,
                self.note_text,
                urwid.Columns(
                    [
                        urwid.Padding(urwid.AttrMap(urwid.Button("保存并配置服务", self.save_config, align="center"), None, focus_map='buttn'), align="center", left=1, right=1),
                        urwid.Padding(urwid.AttrMap(urwid.Button(CONF.return_last_string, ui.return_last, align="center"), None, focus_map='buttn'), align="center", left=1, right=1),
                    ]
                ),
            ]
        )
        ui.top_layer.open_box(urwid.Filler(body, valign='top'))
