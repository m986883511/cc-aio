import os
import json
import click
import logging

from hostadmin import business
from hostadmin.config import CONF
from cc_utils import func, AUTHOR_NAME

LOG = logging.getLogger(__name__)


@click.group()
def cli():
    os.environ['IN_CLICK'] = 'True'
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/hostcli.log')
    LOG.info('--------- command start ---------')


@cli.group()
def host():
    pass


@host.command()
def get_cpu_model():
    """
    获取cpu型号
    """
    value = business.HostEndPoint().get_cpu_model(ctxt={})
    click.secho(f'get cpu model, value="{value}", end and exit.', fg='green')


@host.command()
def set_apt_source_use_ustc():
    """
    让某个pve使用清华源, 并关闭企业订阅源
    """
    business.HostEndPoint().set_apt_source_use_ustc(ctxt={})
    click.secho(f'set pve apt sources.list use ustc', fg='green')


@host.command()
def get_machine_code():
    value = business.HostEndPoint().get_machine_code(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@host.command()
@click.option('--host', default=func.get_current_node_hostname())
def install_base_env(host):
    """
    安装基础环境
    """
    value = business.HostEndPoint().install_base_env(ctxt={}, host=host)
    click.secho(value, fg='green')


@host.command()
def get_hostname():
    value = business.HostEndPoint().get_hostname(ctxt={})
    assert isinstance(value, str), f'return value should be str, but is {type(value)}'
    click.secho(value, fg='green')


@host.command()
def get_ntp_servers():
    value = business.HostEndPoint().get_ntp_servers(ctxt={})
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@host.command()
def reboot():
    value = business.HostEndPoint().reboot(ctxt={})
    assert isinstance(value, bool), f'return value should be bool, but is {type(value)}'
    click.secho(value, fg='green')


@host.command()
@click.argument('ntp_server_ip', type=click.STRING)
def set_ntp_server(ntp_server_ip):
    business.HostEndPoint().set_ntp_server(ctxt={}, ntp_server_ip=ntp_server_ip)
    click.secho(f'设置ntp={ntp_server_ip}成功', fg='green')


@host.command()
def shutdown():
    value = business.HostEndPoint().shutdown(ctxt={})
    assert isinstance(value, bool), f'return value should be bool, but is {type(value)}'
    click.secho(value, fg='green')


@host.command()
def get_support_pci_devices():
    """only return gpu vgpu usb_controller"""
    value = business.HostEndPoint().get_support_pci_devices(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@host.command()
@click.argument('main_vendor', type=click.STRING)
@click.argument('size', type=click.STRING)
def set_vgpu_use_which_size(main_vendor, size):
    """设置vgpu显卡使用哪个子设备"""
    business.HostEndPoint().set_vgpu_use_which_size(ctxt={}, main_vendor=main_vendor, size=size)
    click.secho('配置成功', fg='green')


@host.command()
def get_vgpu_mdev_types():
    """only return support vgpu flavor"""
    value = business.HostEndPoint().get_vgpu_mdev_types(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@host.command()
@click.argument('main_vendor', type=click.STRING)
@click.option('--reset', is_flag=True, default=False, help='删除其他设备的直通配置，只直通这一个')
@click.option('--no-check', is_flag=True, default=False, help='不检查输入的main_vendor在不在系统中')
def set_pci_device_use_vfio(main_vendor, reset=False, no_check=False):
    """
    让某个pci设备以及它下面的子设备被vfio接管，需要重启系统生效

    MAIN_VENDOR: set this vendor to /etc/modprobe.d/vfio-pci.conf
    """
    value = business.HostEndPoint().set_pci_device_use_vfio(ctxt={}, vendor=main_vendor, reset=reset, no_check=no_check)
    click.secho(value, fg='green')
    click.secho(f'if {main_vendor} driver is use is not vfio, you need reboot to take effect', fg='red')
    click.secho(f"you can use 'cc-hostcli host get-support-pci-devices' to check it", fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def pve():
    pass


@pve.command()
def create_vbios_file():
    """创建核显直通的vbios文件"""
    file_path = business.PveEndPoint().create_vbios_file(ctxt={})
    click.secho(f"create vbios file success, path={file_path}, end and exit.", fg='green')


@pve.command()
def repair_modify_hostname():
    """修改主机名后的善后工作"""
    business.PveEndPoint().repair_modify_hostname(ctxt={})
    click.secho(f"repair_modify_hostname success, end and exit.", fg='green')


@pve.command()
@click.option('--ip_mask', type=click.STRING, help="cidr格式 类似192.168.1.44/24")
@click.option('--gateway', type=click.STRING, help="默认网关 就是运营商光猫的网关")
@click.option('--hostname', type=click.STRING, help="主机名 pve主机名修改牵扯太多 请勿轻易修改")
@click.option('--dns', type=click.STRING, default='8.8.8.8', help="dns 默认8.8.8.8")
def change_single_pve_node_network(ip_mask, gateway, dns, hostname):
    """
    修改pve节点的网络
    
    """
    business.PveEndPoint().change_single_pve_node_network(ctxt={}, ip_mask=ip_mask, gateway=gateway, dns=dns, hostname=hostname)
    s = ''
    if ip_mask:
        s += f'ip_mask={ip_mask}, '
    if gateway:
        s += f'gateway={gateway}, '
    if dns:
        s += f'dns={dns}, '
    click.secho(f'change pve node network {s}success!', fg='green')


@pve.command()
def open_ipv6_support():
    business.PveEndPoint().open_ipv6_support(ctxt={})
    click.secho('open_ipv6_support success, may need reboot!', fg='green')


# ------------------------------------------------------------------------- #

@cli.group()
def disk():
    pass


@disk.command()
@click.argument('dev_disk')
@click.argument('confirm_text')
def format_disk_and_create_one_primary(dev_disk, confirm_text):
    """格式化磁盘并创建一个ext4主分区
    
    dev_disk: 例如 /dev/sda

    confirm_text: 必须为 yes-i-really-really-format-it
    """
    business.DiskEndPoint().format_disk_and_create_one_primary(ctxt={}, dev_disk=dev_disk, confirm_text=confirm_text)
    click.secho(f'format {dev_disk} create_one_primary success, end and exit.', fg='green')


@disk.command()
@click.argument('dev_disk')
@click.argument('new_mount_path')
@click.argument('confirm_text')
def umount_disk_and_mount_new(dev_disk, new_mount_path, confirm_text):
    """解除硬盘所有挂载并挂载新的
    
    dev_disk: 例如 /dev/sda

    new_mount_path: 例如 /smb

    confirm_text: 必须为 yes-i-really-really-mount-it
    """
    business.DiskEndPoint().umount_disk_and_mount_new(ctxt={}, dev_disk=dev_disk, new_mount_path=new_mount_path, confirm_text=confirm_text)
    click.secho(f'umount_disk_and_mount_new success ot {new_mount_path}, end and exit.', fg='green')

@disk.command()
@click.option('--return_root_disk', is_flag=True, default=False)
def get_all_disks(return_root_disk):
    """get all disks"""
    value = business.DiskEndPoint().get_all_disks(ctxt={}, return_root_disk=return_root_disk)
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')

@disk.command()
def list_data_disks():
    """list all data disks for osd"""
    value = business.DiskEndPoint().list_data_disks(ctxt={})
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@disk.command()
def list_cache_disks():
    """list all cache disks for osd"""
    value = business.DiskEndPoint().list_cache_disks(ctxt={})
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@disk.command()
def list_osds():
    """list all cache disks for osd"""
    value = business.DiskEndPoint().list_osds(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@disk.command()
@click.argument('osd_disks')
@click.argument('cache_disk')
@click.option('--allow_hdd_as_osd', is_flag=True, default=False)
def add_osds(osd_disks, cache_disk, allow_hdd_as_osd):
    """OSD_DISKS: sda,sdb,sdc\n
    CACHE_DISK: name=sdd,bcache_size=140,db_size=40,max_backends=5"""
    business.DiskEndPoint().add_osds(ctxt={}, osd_disks=osd_disks, cache_disk=cache_disk, allow_hdd_as_osd=allow_hdd_as_osd)


@disk.command()
@click.argument('osd_ids')
def remove_osds(osd_ids):
    """OSD_IDS:  osd.1,osd.2,osd.3"""
    business.DiskEndPoint().remove_osds(ctxt={}, osd_ids=osd_ids)


@disk.command()
@click.argument('disks')
def clear_disks(disks):
    """OSD_IDS:  all,sda,sdb"""
    business.DiskEndPoint().clear_disks(ctxt={}, disks=disks)



@cli.group()
def ceph():
    pass


@ceph.command()
def set_current_node_as_mon_mgr_node():
    value = business.CephEndPoint().set_current_node_as_mon_mgr_node(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
def ceph_orch_ps_current_node():
    value = business.CephEndPoint().ceph_orch_ps_current_node(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
def restart_ceph_about_container():
    value = business.CephEndPoint().restart_ceph_about_container(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
@click.argument('ceph_node_hostname')
def check_ceph_node_network(ceph_node_hostname):
    value = business.CephEndPoint().check_ceph_node_network(ctxt={}, ceph_node_hostname=ceph_node_hostname)
    click.secho(value, fg='green')


@ceph.command()
def check_ceph_health():
    value = business.CephEndPoint().check_ceph_health(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
@click.option('--ceph_version_path')
def run_ceph_registry(**kwargs):
    value = business.CephEndPoint().run_ceph_registry(ctxt={}, **kwargs)
    click.secho(value, fg='green')


@ceph.command()
@click.argument('remote_host')
def copy_ceph_public_key_to_remote_host(remote_host):
    flag, value = business.CephEndPoint().copy_ceph_public_key_to_remote_host(ctxt={}, remote_host=remote_host)
    if flag == 0:
        click.secho(f'copy ceph pub key to {remote_host} success', fg='green')
    else:
        click.secho(value, fg='red')
        raise click.ClickException("")


@ceph.command()
def pull_ceph_image():
    flag, value = business.CephEndPoint().pull_ceph_image(ctxt={})
    if flag == 0:
        click.secho(f'pull ceph image success', fg='green')
    else:
        click.secho(value, fg='red')
        raise click.ClickException("")


@ceph.command()
def check_host_kernel_support_bcache():
    value = business.CephEndPoint().check_host_kernel_support_bcache(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
@click.argument('host', type=click.STRING)
def set_ceph_registry_url(host):
    value = business.CephEndPoint().set_ceph_registry_url(ctxt={}, host=host)
    click.secho(value, fg='green')


@ceph.command()
def get_ceph_fsid():
    value = business.CephEndPoint().get_ceph_fsid(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
def get_ceph_nodes():
    value = business.CephEndPoint().get_ceph_nodes(ctxt={})
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@ceph.command()
@click.argument('host', type=click.STRING)
@click.option('--osd_pool_default_size', default=3)
def run_install_ceph_node(host, osd_pool_default_size):
    value = business.CephEndPoint().run_install_ceph_node(ctxt={}, host=host, osd_pool_default_size=osd_pool_default_size)
    click.secho(value, fg='green')


@ceph.command()
@click.argument('host', type=click.STRING)
def run_add_ceph_node(host):
    value = business.CephEndPoint().run_add_ceph_node(ctxt={}, host=host)
    click.secho(value, fg='green')


@ceph.command()
def cephadm_init_pools():
    value = business.CephEndPoint().cephadm_init_pools(ctxt={})
    click.secho(value, fg='green')


@ceph.command()
def delete_ceph_cluster():
    value = business.CephEndPoint().delete_ceph_cluster(ctxt={})
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def service():
    pass


@service.command()
@click.argument('start_or_stop', type=click.STRING)
def start_or_stop_wireguard(start_or_stop):
    """
    启动还是停止VPN隧道服务

    start_or_stop: 只能是start或者stop
    """
    business.ServiceEndPoint().start_or_stop_wireguard(ctxt={}, start_or_stop=start_or_stop)
    click.secho(f'{start_or_stop} wireguard success', fg='green')


@service.command()
@click.argument('add_or_remove', type=click.STRING)
@click.argument('client_name', type=click.STRING)
def add_or_remove_wireguard_client(add_or_remove, client_name):
    """
    添加还是删除wireguard-client

    add_or_remove: 只能是add或者remove
    """
    business.ServiceEndPoint().add_or_remove_wireguard_client(ctxt={}, add_or_remove=add_or_remove, client_name=client_name)
    click.secho(f'{add_or_remove} wireguard client={client_name} success, exit.', fg='green')


@service.command()
def update_wireguard_service():
    """
    更新配置到wireguard服务
    """
    business.ServiceEndPoint().update_wireguard_service(ctxt={})
    click.secho(f'update wireguard service success, exit.', fg='green')


@service.command()
@click.argument('start_or_stop', type=click.STRING)
def start_or_stop_aliyun_ddns(start_or_stop):
    """
    启动还是停止阿里云DDNS服务

    start_or_stop: 只能是start或者stop
    """
    business.ServiceEndPoint().start_or_stop_aliyun_ddns(ctxt={}, start_or_stop=start_or_stop)
    click.secho(f'{start_or_stop} listen_publialiyun_ddnsc_ip_change_rebot success', fg='green')


@service.command()
@click.argument('start_or_stop', type=click.STRING)
def start_or_stop_listen_public_ip_change_rebot(start_or_stop):
    """
    启动还是停止公网ip变更通知机器人

    start_or_stop: 只能是start或者stop
    """
    business.ServiceEndPoint().start_or_stop_listen_public_ip_change_rebot(ctxt={}, start_or_stop=start_or_stop)
    click.secho(f'{start_or_stop} listen_public_ip_change_rebot success', fg='green')


@service.command()
@click.argument('share_path', default='/smb', type=click.STRING)
@click.argument('samba_user_password', default='samba', type=click.STRING)
def create_samba_service(share_path, samba_user_password):
    """
    创建samba文件共享服务 (windows共享网络盘)

    share_path: 共享路径, 默认是/smb

    samba_user_password: samba用户的密码, 默认是samba
    """
    business.ServiceEndPoint().create_samba_service(ctxt={}, share_path=share_path, samba_user_password=samba_user_password)
    click.secho(f'create samba service success', fg='green')


@service.command()
@click.argument('admin_password', default='password', type=click.STRING)
def create_alist_service(admin_password):
    """
    创建alist服务 (浏览器下载文件看视频)

    admin_password: 浏览器登陆时admin的密码
    """
    business.ServiceEndPoint().create_alist_service(ctxt={}, admin_password=admin_password)
    click.secho(f'create alist service success', fg='green')


@service.command()
@click.option('--text', type=click.STRING)
@click.option('--path', type=click.STRING)
def show_qrencode(text, path):
    """
    显示二维码

    text: 要二维码显示的字符串
    path: 要二维码显示的文件路径
    """
    business.ServiceEndPoint().show_qrencode(ctxt={}, text=text, path=path)
    click.secho(f'show {text}={text} path={path} qrencode success', fg='green')


@service.command()
@click.argument('bind_port', default=8888, type=click.INT)
def create_block_simple_api_service(bind_port):
    """
    创建只响应一次接口的阻塞API服务

    bind_port: 绑定的端口 默认为8888
    """
    business.ServiceEndPoint().create_block_simple_api_service(ctxt={}, bind_port=bind_port)
    click.secho(f'test simple api service success', fg='green')


# ------------------------------------------------------------------------- #

@cli.group()
def network():
    pass


@network.command()
def get_pve_main_bridge_nics():
    value = business.NetworkEndPoint().get_pve_main_bridge_nics(ctxt={})
    click.secho(value, fg='green')


@network.command()
@click.argument('host', type=click.STRING)
def check_network_connection(host):
    value = business.NetworkEndPoint().check_network_connection(ctxt={}, host=host)
    assert isinstance(value, bool), f'return value should be bool, but is {type(value)}'
    click.secho(value, fg='green')


@network.command()
@click.option('--output_dict', is_flag=True, default=False)
def get_all_physical_nics(output_dict):
    output_dict = 'dict' if output_dict else 'list'
    value = business.NetworkEndPoint().get_all_physical_nics(ctxt={}, format=output_dict)
    assert type(value) in [list, dict], f'return value should be list/dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho('-'*50)
    click.secho(value, fg='green')


@network.command()
@click.argument('host')
def check_kolla_interface_exist(host):
    value = business.NetworkEndPoint().check_kolla_interface_exist(ctxt={}, host=host)
    click.secho(f'check kolla interface exist on {host} success')

@network.command()
@click.argument('usage')
@click.argument('nic')
@click.option('--bond_mode', default=0)
@click.option('--input_ip')
@click.option('--input_gateway')
def set_usage_network(usage, nic, bond_mode, input_ip, input_gateway):
    value = business.NetworkEndPoint().set_usage_network(ctxt={}, usage=usage, nic=nic, bond_mode=bond_mode, input_ip=input_ip, input_gateway=input_gateway)
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho('-'*50)
    click.secho(value, fg='green')


@network.command()
@click.argument('origin_nic_name', type=click.STRING)
@click.argument('new_nic_name', type=click.STRING)
def set_nic_altname(origin_nic_name, new_nic_name):
    value = business.NetworkEndPoint().set_nic_altname(ctxt={}, origin_nic_name=origin_nic_name, new_nic_name=new_nic_name)
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho('-'*50)
    click.secho(value, fg='green')


@network.command()
@click.argument('usage')
def clear_usage_network(usage):
    value = business.NetworkEndPoint().clear_usage_network(ctxt={}, usage=usage)
    assert type(value) in [list, dict], f'return value should be list/dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho('-'*50)
    click.secho(value, fg='green')


@network.command()
@click.option('--output_dict', is_flag=True, default=False)
def get_nmcli_connection(output_dict):
    output_dict = 'dict' if output_dict else 'list'
    value = business.NetworkEndPoint().get_nmcli_connection(ctxt={}, output_format=output_dict)
    assert type(value) in [list, dict], f'return value should be list/dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho('-'*50)
    click.secho(value, fg='green')


@cli.command()
def generate_no_click_hostcli():
    current_file = os.path.abspath(__file__)
    # 获取当前文件所在的目录路径
    directory = os.path.dirname(current_file)
    # 获取当前文件的文件名（不包含路径）
    filename = os.path.basename(current_file)
    # 生成备份文件名
    backup_filename = os.path.splitext(filename)[0] + '_bak.py'
    # 构建备份文件的完整路径
    backup_file_path = os.path.join(directory, backup_filename)
    # 复制当前文件到备份文件
    msg = f"new hostcli without click wrap file has created as {backup_file_path}"
    with open(current_file, 'r') as input_file, open(backup_file_path, 'w') as output_file:
        # 遍历输入文件的每一行
        for line in input_file:
            # 如果行不是以 '@' 开头，则将其写入输出文件
            if not line.startswith('@'):
                output_file.write(line)
    click.secho(msg, fg='green')


@cli.group()
def ssh():
    pass


@ssh.command()
@click.argument('host', type=click.STRING)
def check_ssh_passwordless(host):
    value = business.SshEndPoint().check_ssh_passwordless(ctxt={}, host=host)
    assert isinstance(value, bool), f'return value should be bool, but is {type(value)}'
    click.secho(value, fg='green')

@ssh.command()
@click.argument('host', type=click.STRING)
@click.argument('src_dir', type=click.STRING)
@click.option('--progress', is_flag=True, default=False)
def rsync_dir_to_remote_host(host, src_dir, progress):
    """
    同步本机的某个目录到远程主机的相同目录
    """
    business.SshEndPoint().rsync_dir_to_remote_host(ctxt={}, host=host, src_dir=src_dir, progress=progress)


@ssh.command()
@click.argument('host', type=click.STRING)
def ssh_passwordless_to_host(host):
    value = business.SshEndPoint().ssh_passwordless_to_host(ctxt={}, host=host)
    value = value if value else '执行成功'
    click.secho(value, fg='green')


@ssh.command()
@click.argument('host', type=click.STRING)
@click.argument('cmd', type=click.STRING)
def ssh_run_on_remote(host, cmd):
    flag, value = business.SshEndPoint().ssh_run_on_remote(ctxt={}, host=host, cmd=cmd)
    color = 'green' if flag == 0 else 'red'
    temp = 'success' if flag == 0 else f'failed, err={value}'
    click.secho(f'execute command on {host} {temp}', fg=color)


@ssh.command()
@click.argument('host', type=click.STRING)
@click.argument('cmd', type=click.STRING)
def ssh_run_on_remote_via_popen(host, cmd):
    return_code = business.SshEndPoint().ssh_run_on_remote_via_popen(ctxt={}, host=host, cmd=cmd)
    color = 'green' if return_code == 0 else 'red'
    temp = 'success' if return_code == 0 else 'failed'
    click.secho(f'execute command on {host} {temp}', fg=color)


@ssh.command()
@click.argument('remote_host', type=click.STRING)
@click.argument('src_dir', type=click.STRING)
@click.argument('dst_dir', type=click.STRING)
def scp_dir_to_remote_host(remote_host, src_dir, dst_dir):
    flag, value = business.SshEndPoint().scp_dir_to_remote_host(ctxt={}, host=remote_host, src_dir=src_dir, dst_dir=dst_dir)
    if flag == 0:
        click.secho(f'scp {src_dir} to {remote_host}:{dst_dir} success', fg='green')
    else:
        click.secho(value, fg='red')
        raise click.ClickException("")


@ssh.command()
@click.argument('remote_host', type=click.STRING)
@click.argument('src_dir', type=click.STRING)
@click.argument('dst_dir', type=click.STRING)
def scp_remote_host_dir_to_current_host(remote_host, src_dir, dst_dir):
    flag, value = business.SshEndPoint().scp_remote_host_dir_to_current_host(ctxt={}, host=remote_host, src_dir=src_dir, dst_dir=dst_dir)
    if flag == 0:
        click.secho(f'scp {remote_host}:{src_dir} to {dst_dir} success', fg='green')
    else:
        click.secho(value, fg='red')
        raise click.ClickException("")


@ssh.command()
@click.argument('command', type=click.STRING)
def execute_on_all_hosts(command):
    """
    在所有关联的主机上执行相同的命令
    
    例如: hostcli ssh execute-on-all-hosts 'date'
    """
    business.SshEndPoint().execute_on_all_hosts(ctxt={}, command=command)


def main():
    cli()
