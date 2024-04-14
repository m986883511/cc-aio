#!/usr/bin/env python
import argparse
import os
import copy
import json
import subprocess
import logging
from urllib import request, parse

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


def completed(flag, dec, err=None, raise_flag=True):
    if flag == 0:
        msg = f'{dec} success'
        LOG.info(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在cs_utils模块中公开引入任何第三方包
            click.secho(msg, fg='green')
        else:
            print(msg)
    else:
        msg = f'{dec} failed'
        if err:
            msg = f'{msg}, err: {err}'
        LOG.error(msg)
        if os.environ.get('IN_CLICK'):
            import click # 不要在cs_utils模块中公开引入任何第三方包
            click.secho(msg, fg='red')
            if raise_flag:
                raise click.ClickException("")
        else:
            print(msg)
        if raise_flag:
            raise Exception(msg)

def set_simple_log(log_path):
    dirname = os.path.dirname(log_path)
    os.makedirs(dirname, exist_ok=True)
    logging.basicConfig(
        filename=log_path,  # 日志文件名
        level=logging.INFO,  # 日志级别
        format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
    )
    LOG = logging.getLogger(__name__)
    LOG.info(f'set_simple_log={log_path} ok')


def get_string_split_list(string, split_flag=','):
    return [i.strip() for i in string.split(split_flag) if i.strip()]


def get_url_ip_port(url):
    item_list = get_string_split_list(url, split_flag='/')
    item_list2 = get_string_split_list(url, split_flag='//')
    if len(item_list2) != 2:
        raise Exception(f'invalid url={url}')
    ip_port_and_string = item_list2[1]
    for item in item_list:
        if ip_port_and_string.startswith(item):
            return item
    else:
        raise Exception(f'invalid url={url}')


def get_url_ip_port(url):
    item_list = get_string_split_list(url, split_flag='/')
    item_list2 = get_string_split_list(url, split_flag='//')
    if len(item_list2) != 2:
        raise Exception(f'invalid url={url}')
    ip_port_and_string = item_list2[1]
    for item in item_list:
        if ip_port_and_string.startswith(item):
            return item
    else:
        raise Exception(f'invalid url={url}')


def validate_alist_url(alist_url):
    try:
        ip_port = get_url_ip_port(alist_url)
    except:
        raise argparse.ArgumentTypeError(f"invalid alist url: {alist_url}")
    try:
        alist_public_settings_url = f'http://{ip_port}/api/public/settings'
        response = request.urlopen(alist_public_settings_url)
        code = response.code
        if code // 100 != 2:
            raise Exception(f'response.code is {code}')
    except Exception as e:
        raise argparse.ArgumentTypeError(f"communicate with alist failed, url={alist_public_settings_url}, err={str(e)}")
    return alist_url


def check_path(value):
    os.makedirs(value, exist_ok=True)
    if not os.path.isdir(value):
        raise argparse.ArgumentTypeError(f"Invalid path: {value} is not a valid directory.")
    return value


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('alist_url', help='alist url', type=validate_alist_url)
    parser.add_argument('-s', '--startswith', help='download files startswith it', type=str)
    parser.add_argument('-e', '--endswith', help='download files endswith it', type=str)
    parser.add_argument('-p', '--pathsave', default=os.getcwd(), help='download files save this path', type=check_path)
    args = parser.parse_args()
    return args


def get_alist_ip_port_and_path(alist_url):
    ip_port = get_url_ip_port(alist_url)
    list_files_url = f'http://{ip_port}/api/fs/list'
    url_list = get_string_split_list(alist_url, ip_port)
    if len(url_list) != 2:
        raise Exception(f'not found {ip_port} in {alist_url}, length err')
    path_url = url_list[1]
    return ip_port, path_url


def get_alist_fs_list(alist_url):
    ip_port, path_url = get_alist_ip_port_and_path(alist_url)
    list_files_url = f'http://{ip_port}/api/fs/list'
    body = {"path":path_url,"password":"","page":1,"per_page":0,"refresh":False}
    print(list_files_url, body)
    data = json.dumps(body).encode('utf-8')
    data = bytes(parse.urlencode(body), encoding="utf8")
    req = request.Request(url=list_files_url,data=data,method="POST")
    response = request.urlopen(req)
    code = response.code
    if code // 100 != 2:
        raise Exception(f'{list_files_url} response.code is {code}')
    response_data = response.read().decode('utf-8')
    response_data_dict = json.loads(response_data)
    alist_code = response_data_dict.get('code') or 0
    if alist_code // 100 != 2:
        raise Exception(f'{list_files_url} body.code is {alist_code}')
    return response_data_dict


def get_can_download_files(alist_url):
    content_dict = get_alist_fs_list(alist_url)
    print(json.dumps(content_dict, indent=4))
    content_list = content_dict['data']['content']
    all_fiels = []
    for value_dict in content_list:
        is_dir_flag = value_dict.get('is_dir')
        if is_dir_flag is False:
            all_fiels.append(value_dict.get('name'))
    return all_fiels


def get_download_file_urls(alist_url, need_download_files):
    ip_port, path_url = get_alist_ip_port_and_path(alist_url)
    download_file_urls = []
    for file in need_download_files:
        url = f'http://{ip_port}/d/{path_url}/{file}'
        url = url.replace('//', '/')
        url = url.replace('http:/', 'http://')
        download_file_urls.append(url)
    return download_file_urls


def use_wget_download(download_file_urls, pathsave):
    for url in download_file_urls:
        cmd = f'wget {url} -P {pathsave}'
        print(cmd)
        flag = execute_command_in_popen(cmd)
        completed(flag, f'download {url}')


def download_files(alist_url, startswith, endswith, pathsave):
    all_files = get_can_download_files(alist_url)
    print(f'get_can_download_files is {all_files}')
    need_download_files = copy.deepcopy(all_files)
    for file in all_files:
        if startswith:
            if not file.startswith(startswith):
                if file in need_download_files:
                    need_download_files.remove(file)
        if endswith:
            if not file.endswith(endswith):
                if file in need_download_files:
                    need_download_files.remove(file)
    need_download_files = [parse.quote(file) for file in need_download_files]
    print(f'need_download_files is {need_download_files}')
    download_file_urls = get_download_file_urls(alist_url, need_download_files)
    print(f'download_file_urls is {download_file_urls}')
    use_wget_download(download_file_urls, pathsave)


if __name__ == '__main__':
    args = parse_arguments()
    print(f'args is {args}')
    download_files(args.alist_url, args.startswith, args.endswith, args.pathsave)
