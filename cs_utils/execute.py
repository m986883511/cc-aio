import os
import subprocess
import logging

LOG = logging.getLogger(__name__)


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


def execute_command_in_popen(cmd: str, shell=True, output_func=None, encoding="utf-8") -> int:
    def func():
        for line in iter(proc.stdout.readline, ""):
            yield line

    def default_print(x):
        if os.environ.get('IN_CLICK'):
            import click
            click.secho(x.strip())
        else:
            print(x, end='')

    output_func = output_func or default_print
    logging.info(f"execute_command_in_popen cmd={cmd}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, universal_newlines=True)
    for line in func():
        output_func(line)
    proc.stdout.close()
    return_code = proc.wait()
    LOG.info(f'execute_command_in_popen end, return_code={return_code}')
    return return_code


def execute_command_on_host(cmd: str, shell=True, encoding="utf-8", timeout=None, return_code_dict=None) -> (bool, str):
    assert shell, f'execute_command_on_host shell param must be true'
    cmd = f"nsenter --mount=/host/proc/1/ns/mnt sh -c '{cmd}'"
    logging.info("execute command on host")
    return execute_command(cmd, shell=shell, encoding=encoding, timeout=timeout, return_code_dict=return_code_dict)


def crudini_set_config(ini_path: str, section:str, key: str, value: str) -> (int, str):
    assert os.path.exists(ini_path), f"{ini_path} is not exist"
    cmd = f'crudini --set {ini_path} {section} {key} {value}'
    flag, content = execute_command(cmd, shell=True)
    return flag, content


def crudini_set_config_on_host(ini_path: str, section:str, key: str, value: str) -> (int, str):
    if ini_path.startswith('/host'):
        ini_path = ini_path[5:]
    cmd = f'crudini --set {ini_path} {section} {key} {value}'
    cmd = f"nsenter --mount=/host/proc/1/ns/mnt sh -c \"{cmd}\""
    flag, content = execute_command(cmd, shell=True)
    return flag, content


def execute_ssh_command_via_id_rsa(command:str, key_path: str, host_or_ip: str, user='root', ssh_timeout=5) -> (bool):
    cmd = f'ssh -o PreferredAuthentications=publickey -o ConnectTimeout={ssh_timeout} -i {key_path} {user}@{host_or_ip} {command}'
    return_code, content = execute_command(cmd)

    return return_code, content


def execute_ssh_command_via_id_rsa_in_popen(command:str, key_path: str, host_or_ip: str, user='root', ssh_timeout=5, ssh_use_which_ip='') -> (bool):
    ssh_use_ip_str = f'-b {ssh_use_which_ip}' if ssh_use_which_ip else ''
    cmd = f'ssh {ssh_use_ip_str} -o PreferredAuthentications=publickey -o ConnectTimeout={ssh_timeout} -i {key_path} {user}@{host_or_ip} "{command}"'
    if os.environ.get('IN_CLICK'):
        import click
        click.secho(f'{cmd}')
    return_code = execute_command_in_popen(cmd)
    return return_code


def check_ssh_can_connect_via_id_rsa(key_path: str, host_or_ip: str, user='root', ssh_timeout=5) -> (bool):
    command = '/bin/true'
    return_code, err_msg = execute_ssh_command_via_id_rsa(command, key_path, host_or_ip)
    if return_code != 0:
        LOG.error(f"{host_or_ip} can't ssh via key={key_path}, err={err_msg}")
    return return_code == 0


def completed(flag, dec, err=None, raise_flag=True):
    if flag == 0:
        msg = f'{dec} success'
        LOG.info(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在astute_utils模块中公开引入任何第三方包
            click.secho(msg, fg='green')
        else:
            print(msg)
    else:
        msg = f'{dec} failed'
        if err:
            msg = f'{msg}, err: {err}'
        LOG.error(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在astute_utils模块中公开引入任何第三方包
            click.secho(msg, fg='red')
            if raise_flag:
                raise click.ClickException("")
        else:
            print(msg)
        if raise_flag:
            raise Exception(msg)


def use_crudini_save_CONF_to_path(path, group, key):
    from oslo_config import cfg
    from cs_utils import execute
    group_obj = getattr(cfg.CONF, group)
    value = getattr(group_obj, key)
    flag, content = execute.crudini_set_config(path, group, key, value)
    return flag, content
