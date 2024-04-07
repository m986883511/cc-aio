import os
import base64
import socket
import logging

from oslo_config import cfg

CONF = cfg.CONF
# if in kolla container, KOLLA_BASE_ARCH is x86_64 or aarch64
AUTHOR_NAME="cc"
MOUNT_HOST = '/host' if os.getenv('KOLLA_BASE_ARCH') else ""
HOSTRPC_CONF_PATH = f'/etc/{AUTHOR_NAME}/hostrpc.conf'
AUTHOR_SCRIPTS_DIR = f'/usr/local/{AUTHOR_NAME}/scripts'

core_opts = [
    cfg.StrOpt('state_path',
               default='/var/lib/hostadmin',
               help="Top-level directory for maintaining cinder's state"),
    cfg.IntOpt('json_rpc_server_port',
               default=10004,
               help="json_rpc_port"),
    cfg.StrOpt('package_name',
               default='hostadmin',
               help="this package name"), ]

CONF.register_cli_opts(core_opts)

hostadmin_opts = [
    cfg.IntOpt('shutdown_delay',
               default=1,
               help="shutdown delay seconds"), ]

CONF.register_cli_opts(hostadmin_opts)


api_opts = [
    cfg.BoolOpt('api_rate_limit',
                default=True,
                help='Enables or disables rate limit of the API.'),
    cfg.StrOpt('group_api_class',
               default='cinder.group.api.API',
               help='The full class name of the group API class'),
    cfg.ListOpt('osapi_volume_ext_list',
                default=[],
                help='Specify list of extensions to load when using osapi_'
                     'volume_extension option with cinder.api.contrib.'
                     'select_extensions'),
    cfg.MultiStrOpt('osapi_volume_extension',
                    default=['cinder.api.contrib.standard_extensions'],
                    help='osapi volume extension to load'),
    cfg.StrOpt('volume_api_class',
               default='cinder.volume.api.API',
               help='The full class name of the volume API class to use'),
]

global_opts = [
    cfg.StrOpt('host',
               sample_default='localhost',
               default=socket.gethostname(),
               help='Name of this node.  This can be an opaque '
                    'identifier. It is not necessarily a host name, '
                    'FQDN, or IP address.'),
    # NOTE(vish): default to nova for compatibility with nova installs
    cfg.BoolOpt('monkey_patch',
                default=False,
                help='Enable monkey patching'),
    cfg.ListOpt('monkey_patch_modules',
                default=[],
                help='List of modules/decorators to monkey patch'),
    cfg.IntOpt('service_down_time',
               default=60,
               help='Maximum time since last check-in for a service to be '
                    'considered up'),
    cfg.BoolOpt('split_loggers',
                default=False,
                help='Log requests to multiple loggers.')
]

messages_opts = [
    cfg.IntOpt('message_ttl', default=2592000,
               help='message minimum life in seconds.'),
    cfg.IntOpt('message_reap_interval', default=86400,
               help='interval between periodic task runs to clean expired '
                    'messages in seconds.')
]


ssh_opts = [
    cfg.StrOpt('root_pwd', default=str(base64.b64decode('ZG9ub3R1c2Vyb290IQ=='), "utf-8"), help='root_pwd'),
]

CONF.register_opts(messages_opts)
CONF.register_opts(api_opts)
CONF.register_opts(core_opts)
CONF.register_opts(global_opts)
CONF.register_opts(ssh_opts, group='ssh')
