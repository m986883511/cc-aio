#!/usr/bin/env python
import os
import subprocess
import logging
import argparse
import ipaddress

LOG = logging.getLogger(__name__)
ALL_PHY_NICS = None


class BondMode:
    name = ['balance-rr','active-backup','balance-xor','broadcast','802.3ad','balance-tlb','balance-alb']

    @classmethod
    def get_mode_str(cls, number):
        number = number or 0
        number = int(number)
        return cls.name[number]
    
    @classmethod
    def get_mode_number(cls, mode_str):
        return cls.name.index(mode_str)


def execute_command(cmd: str, shell=True, encoding="utf-8", timeout=None, return_code_dict=None) -> (bool, str):
    try:
        logging.info("execute command: %s", cmd)
        tmp_cmd = cmd if shell else cmd.split()
        output = subprocess.check_output(tmp_cmd, stderr=subprocess.STDOUT, shell=shell, timeout=timeout)
        default_return = output.decode(encoding, errors='ignore').strip()
        if return_code_dict:
            default_return = return_code_dict.get('0') or default_return
        return 0, default_return
    except subprocess.TimeoutExpired as te:
        err_msg = f"timeout={timeout}, cmd='{cmd}'"
        logging.error(f"execute command timed out, {err_msg}")

        return -1, err_msg
    except subprocess.CalledProcessError as e:
        err_msg = f"cmd='{cmd}', err={e.output.decode(encoding, errors='ignore').strip()}"
        LOG.error(f"execute command failed, {err_msg}")
        return_code = e.returncode
        if return_code_dict:
            err_msg = return_code_dict.get(str(return_code)) or err_msg
        return return_code, err_msg
    except Exception as e:
        err_msg = f"cmd='{cmd}', err={e.output.decode(encoding, errors='ignore').strip()}"
        LOG.error(f"execute command failed, e_class={e.__class__}, {err_msg}")
        return_code = e.returncode
        if return_code_dict:
            err_msg = return_code_dict.get(str(return_code)) or err_msg
        return return_code, err_msg


def completed(flag, dec, err=None, raise_flag=True):
    if flag == 0:
        msg = f'{dec} success'
        LOG.info(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在cg_utils模块中公开引入任何第三方包
            click.secho(msg, fg='green')
        else:
            print(msg)
    else:
        msg = f'{dec} failed'
        if err:
            msg = f'{msg}, err: {err}'
        LOG.error(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在cg_utils模块中公开引入任何第三方包
            click.secho(msg, fg='red')
            if raise_flag:
                raise click.ClickException("")
        else:
            print(msg)
        if raise_flag:
            raise Exception(msg)


def get_string_split_list(string, split_flag=','):
    return [i.strip() for i in string.split(split_flag) if i.strip()]


def get_pyh_nics():
    cmd = 'find /sys/class/net -type l -not -lname "*virtual*" -printf "%f\n"'
    flag, content = execute_command(cmd)
    completed(flag, f'find physical nic in /sys/class/net', content)
    global ALL_PHY_NICS
    ALL_PHY_NICS = get_string_split_list(content, split_flag='\n')


def get_nmcli_connection(output_format='list'):
    cmd  = f"nmcli con"
    flag, content = execute_command(cmd)
    completed(flag, f'get nmcli connection', content)
    content_list = get_string_split_list(content, split_flag='\n')
    keys = None
    result = []
    for i, line in enumerate(content_list):
        if i == 0:
            keys = get_string_split_list(line, split_flag=' ')
            keys = [i.lower() for i in keys]
        else:
            values = get_string_split_list(line, split_flag=' ')
            length = len(values)
            new_values = [' '.join(values[:length-3])]
            new_values.extend(values[length-3:])
            result.append(dict(zip(keys, new_values)))
    if output_format == 'dict':
        return_dict = {i.get('name'):i for i in result}
        return return_dict
    return result


def _delete_nic_vlan(nic_evice):
    nmcli_cons = get_nmcli_connection()
    for con in nmcli_cons:
        device = con.get('device') or ''
        con_name = con.get('name') or ''
        con_type = con.get('type') or ''
        if con_type == 'vlan' and f"{nic_evice}." in device:
            cmd = f'nmcli c delete {con_name}'
            flag, content = execute_command(cmd)
            completed(flag, f'delete {nic_evice} vlan device={device}', content)


def _delete_nmcli_connection(con_name):
    nmcli_cons = get_nmcli_connection(output_format='dict')
    if con_name in nmcli_cons:
        cmd = f'nmcli c delete {con_name}'
        flag, content = execute_command(cmd)
        completed(flag, f'delete con_name={con_name}', content)


def _delete_nic_device(nic_evice):
    nmcli_cons = get_nmcli_connection()
    for con in nmcli_cons:
        con_device = con.get('device') or ''
        con_name = con.get('name') or ''
        con_id = con.get('uuid')
        if nic_evice == con_device or con_name == nic_evice:
            cmd = f'nmcli c delete {con_id}'
            flag, content = execute_command(cmd)
            completed(flag, f'delete con_name={con_name} device={nic_evice}', content)


def _delete_bond_eth(bond_device):
    nmcli_cons = get_nmcli_connection()
    bond_con = f'bond-{bond_device}'
    has_delete_con_list = []
    for con in nmcli_cons:
        con_name = con.get('name') or ''
        con_type = con.get('type') or ''
        con_device = con.get('device') or ''
        if bond_device in con_name and con_type == 'ethernet' and con_name not in has_delete_con_list:
            cmd = f'nmcli c delete {con_name}'
            flag, content = execute_command(cmd)
            completed(flag, f'delete bond_device={bond_device} eth={con_device}', content)
            has_delete_con_list.append(con_name)


def set_hostname(ip_mask):
    ip = get_string_split_list(ip_mask, split_flag='/')[0]
    endwith = get_string_split_list(ip, split_flag='.')[-1]
    endwith = int(endwith)
    hostname = f'host{endwith:03d}'
    cmd = f'hostnamectl set-hostname {hostname}'
    flag, content = execute_command(cmd)
    completed(flag, f'set hostname as {hostname}', content)


def config_manage(ip_mask, nic_list, bond_mode, vlan=None):
    for nic in nic_list:
        _delete_nic_vlan(nic)
        _delete_nic_device(nic)
    bond_name = 'mgtbond'
    bond_con_name = f'bond-{bond_name}'
    _delete_nic_vlan(bond_name)
    _delete_bond_eth(bond_name)
    _delete_nmcli_connection(bond_con_name)

    LOG.info(f'create bond={bond_name}')
    bond_mode_str = BondMode.get_mode_str(bond_mode)
    cmd = f'nmcli con add type bond ifname {bond_name} bond.options "mode={bond_mode_str}"'
    flag, content = execute_command(cmd)
    completed(flag, f'create bond_name={bond_name}, bond_con_name={bond_con_name}', content)
    for nic in nic_list:
        cmd = f'nmcli con add type ethernet con-name {bond_name}-{nic} ifname {nic} master {bond_name}'
        flag, content = execute_command(cmd)
        completed(flag, f'add eth={nic} to bond={bond_name}')
    if ip_mask:
        cmd = f'nmcli connection modify {bond_con_name} ipv4.method manual ipv6.method ignore ipv4.addresses {ip_mask} ipv4.gateway ""'
        flag, content = execute_command(cmd)
        completed(flag, f'set {bond_con_name} ip method as manual ip={ip_mask}', content)
    for nic in nic_list:
        cmd = f'nmcli con up {bond_name}-{nic}'
        flag, content = execute_command(cmd)
        completed(flag, f'up bond con={bond_name}-{nic}', content)
    cmd = f'nmcli con up {bond_con_name}'
    flag, content = execute_command(cmd)
    completed(flag, f'up bond con={bond_con_name}', content)
    set_hostname(ip_mask)


def validate_ip_mask(ip_mask):
    try:
        if '/' not in ip_mask:
            raise
        if not ip_mask.startswith('192.222.1.'):
            raise
        ipaddress.ip_network(ip_mask, strict=False)
    except:
        raise argparse.ArgumentTypeError(f"Invalid ip/mask address: {ip_mask}")
    ip = get_string_split_list(ip_mask, split_flag='/')[0]
    ip_end = get_string_split_list(ip, split_flag='.')[-1]
    if int(ip_end) < 1 or int(ip_end) > 240:
        raise argparse.ArgumentTypeError(f"Invalid ip/mask address: {ip_mask}, ip range is 1-240")
    return ip_mask


def validate_nics(nics):
    get_pyh_nics()
    nic_list = get_string_split_list(nics, split_flag=',')
    not_found_nics = [ nic for nic in nic_list if nic not in ALL_PHY_NICS]
    if not_found_nics:
        raise argparse.ArgumentTypeError(f"Invalid nics: {not_found_nics} not found in system")
    return nic_list


def validate_bond_mode(bond_mode):
    if not bond_mode.isdigit:
        raise argparse.ArgumentTypeError(f"Invalid bond_mode: {bond_mode} is not digit")
    temp = int(bond_mode)
    if temp < 0 or temp > 6:
        raise argparse.ArgumentTypeError(f"Invalid bond_mode: {bond_mode} should be 0-6")
    return bond_mode


def validate_vlan(vlan):
    if not vlan.isdigit:
        raise argparse.ArgumentTypeError(f"Invalid vlan: {vlan} is not digit")
    temp = int(vlan)
    if temp < 1 or temp > 4094:
        raise argparse.ArgumentTypeError(f"Invalid vlan: {vlan} should be 1-4094")
    return vlan


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('ip_mask', help='ip/mask address, like 192.222.1.155/24', type=validate_ip_mask)
    parser.add_argument('nics', help='NIC names, like eth0,eth1', type=validate_nics)
    # parser.add_argument('--vlan', help='VLAN ID 1-4094', type=validate_vlan)
    parser.add_argument('--mode', help='Bond mode 0-6', type=validate_bond_mode)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_arguments()
    print(args)
    # config_manage(args.ip_mask, args.nics, args.vlan, args.mode)
    config_manage(args.ip_mask, args.nics, args.mode)
