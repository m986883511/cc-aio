import os
os.environ['IN_TUI'] = 'True'
import json
import logging

from cc_utils import execute, func, Author
from hostadmin.rpc import rpc_client

LOG = logging.getLogger(__name__)


def get_ipv6():
    network_dict = rpc_client('get_pve_main_bridge_nics')
    ipv6_list = network_dict.get('ipv6') or []
    ipv6s = [i.get('ip') for i in ipv6_list if 'ip' in i]
    public_ip = func.get_public_ipv6_from_list(ipv6s)
    if '/' in public_ip:
        public_ip = func.get_string_split_list(public_ip, split_flag='/')[0]
    local_ip = func.get_fe80_ipv6_from_list(ipv6s)
    if '/' in local_ip:
        local_ip = func.get_string_split_list(local_ip, split_flag='/')[0]
    res = local_ip, public_ip
    LOG.info(f'get ipv6 is {res}')
    return res


def set_ip6tables():
    local_ip, public_ip = get_ipv6()
    delete_cmds = [
        f'ip6tables -P INPUT ACCEPT',
        f'ip6tables -F INPUT',
    ]
    add_cmds = [
        f'ip6tables -A INPUT -d {public_ip} -j ACCEPT',
        f'ip6tables -A INPUT -d {local_ip} -j ACCEPT',
        f'ip6tables -A INPUT -p udp --sport 67:68 --dport 67:68 -j ACCEPT',
        f'ip6tables -A INPUT -p icmpv6 --icmpv6-type echo-request -j ACCEPT',
        f'ip6tables -A INPUT -j DROP',
    ]
    for cmd in delete_cmds:
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, cmd, content)
    for cmd in add_cmds:
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, cmd, content)


if __name__ == '__main__':
    func.set_simple_log(f'/var/log/{Author.name}/script.log')
    LOG.info('--------- set-ip6tables start ---------')
    set_ip6tables()
    LOG.info('--------- set-ip6tables end ---------')
