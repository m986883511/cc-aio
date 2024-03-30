import os
import socket
import logging

from oslo_config import cfg

from cs_utils import func

CONF = cfg.CONF
PVE_TUI_CONF_PATH = '/etc/cs/pvetui.conf'

default_opts = [
    cfg.StrOpt('return_last_string', default='返回上一层|ESC', help="conf_path"),
    cfg.StrOpt('pvetui_title', default='PVE TUI v1.0', help="pve tui title"),
    cfg.IntOpt('console_max_item_number', default=20, help="console_max_item_number"),
]

ceph_opts = [
    cfg.IntOpt('osd_pool_default_min_size', default=1, help="osd_pool_default_min_size"),
    cfg.IntOpt('osd_pool_default_size', default=3, help="osd_pool_default_size"),
    cfg.IntOpt('max_backends_per_cache', default=5, help="max_backends_per_cache"),
    cfg.IntOpt('db_size', default=40, help="db_size"),
    cfg.IntOpt('bcache_size', default=140, help="bcache_size"),
    cfg.BoolOpt('enable_bcache', default=False, help="enable_bcache"),
    cfg.IntOpt('bcache_size_minimum', default=50, help="bcache_size_minimum"),
    cfg.IntOpt('db_size_minimum', default=20, help="db_size_minimum"),
    cfg.IntOpt('max_backends_per_cache_minimum', default=1, help="max_backends_per_cache_minimum"),
    cfg.IntOpt('monitor_nodes_maximum', default=3, help="monitor_nodes_maximum"),
    cfg.StrOpt('monitor_nodes', default="", help="monitor_nodes"),
    cfg.BoolOpt('allow_hdd_as_osd', default=False, help='allow_hdd_as_osd'),
    cfg.BoolOpt('current_node_installed_ceph', default=False, help='current_node_installed_ceph'),
]

network_opts = [
    cfg.IntOpt('bond_mode', default=0, help="bond_mode"),
    cfg.IntOpt('vlan', default=1, help="vlan"),
    cfg.IntOpt('delay_update_view_time', default=1, help="delay_update_view_time"),
    cfg.IntOpt('vmbond_vlan', default=1, help="vmbond_vlan"),
    cfg.IntOpt('extbond_vlan', default=1, help="extbond_vlan"),
]

base_env_opts = [
    cfg.IntOpt('root_min_space', default=20, help="root_min_space"),
    cfg.StrOpt('all_nodes', default='', help="all_nodes"),
    cfg.StrOpt('all_nodes_edit_str', default='', help="all_nodes_edit_str"),
    cfg.StrOpt('installed_nodes', default='', help="installed_nodes"),
]

samba_opts = [
    cfg.StrOpt('samba_default_user', default='samba', help="samba_default_user"),
    cfg.StrOpt('samba_default_password', default='samba', help="samba_default_password"),
    cfg.StrOpt('default_share_path', default='/smb', help="default_share_path"),
]

alist_opts = [
    cfg.StrOpt('default_admin_password', default='password', help="default_admin_password"),
]

public_ip_opts = [
    cfg.StrOpt('ipv4_or_ipv6', default='ipv4', help="use ipv4 or ipv6 public ip"),
    cfg.BoolOpt('use_ddns', default=False, help="use ddns or not"),
    cfg.StrOpt('accessKeyId', default='', help="aliyun ddns accessKeyId"),
    cfg.StrOpt('accessSecret', default='', help="aliyun ddns accessSecret"),
    cfg.BoolOpt('use_check_robot', default=False, help="use check public robot or not"),
    cfg.StrOpt('feishu_webhook_uuid', default='', help="feishu webhook uuid"),
    cfg.IntOpt('check_interval', default=5, help="check public ip every x mintues"),
    cfg.IntOpt('simple_http_server_port', default=8888, help="simple_http_server_port"),
]

wireguard_opts = [
    cfg.BoolOpt('open_flag', default=False, help="open wireguard falg"),
    cfg.StrOpt('listen_port', default='12001', help="listen_port"),
]

openstack_opts = [
    cfg.StrOpt('control_nodes', default='', help="control_nodes"),
    cfg.StrOpt('pure_compute_nodes', default='', help="pure_compute_nodes"),
    cfg.StrOpt('mgt_vip', default='192.222.1.252', help="default_mgt_vip"),
    cfg.StrOpt('access_vip', default='', help="default_access_vip"),
    # cfg.StrOpt('option', default='gnocchi,ceilometer,heat', help="openstack option"),
    cfg.StrOpt('option', default='', help="openstack option"),
    cfg.IntOpt('cpu_allocation_ratio', default=8, help="cpu_allocation_ratio"),
    cfg.IntOpt('ram_allocation_ratio', default=1, help="ram_allocation_ratio"),
    cfg.IntOpt('reserved_host_cpus', default=4, help="reserved_host_cpus"),
    cfg.IntOpt('reserved_host_memory_gb', default=16, help="reserved_host_memory_gb"),
    cfg.IntOpt('reserved_host_memory_mb', default=16*1024, help="reserved_host_memory_mb"),
    cfg.StrOpt('enable_cinder_backend_nfs', default='no', help="enable_cinder_backend_nfs"),
    cfg.StrOpt('ceph_admin_node', default='', help="ceph_admin_node"),
    cfg.BoolOpt('rsync_config_to_other_control_nodes', default=True, help='rsync_config_to_other_control_nodes'),
    cfg.StrOpt('control_nodes_ntp_server', default=func.get_hostname_map_ip(), help='control_nodes_ntp_server'),
    cfg.StrOpt('enable_cinder', default='yes', help='enable_cinder'),
]

CONF.register_cli_opts(default_opts)
CONF.register_cli_opts(ceph_opts, group='ceph')
CONF.register_cli_opts(samba_opts, group='samba')
CONF.register_cli_opts(alist_opts, group='alist')
CONF.register_cli_opts(public_ip_opts, group='public_ip')
CONF.register_cli_opts(wireguard_opts, group='wireguard')
CONF.register_cli_opts(network_opts, group='network')
CONF.register_cli_opts(base_env_opts, group='base_env')
CONF.register_cli_opts(openstack_opts, group='openstack')
