import os
import json
import click
import logging

from pve_admin import business
from pve_admin.config import CONF
from cs_utils import func

LOG = logging.getLogger(__name__)


@click.group()
def cli():
    os.environ['IN_CLICK'] = 'True'
    func.set_simple_log('/var/log/astute/pve_cli.log')
    LOG.info('--------- command start ---------')

# ------------------------------------------------------------------------- #

@cli.group()
def cinder():
    pass


@cinder.command()
def get_cinder_backends():
    value = business.CinderEndPoint().get_cinder_backends(ctxt={})
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def glance():
    pass


@glance.command()
def get_glance_backend():
    value = business.GlanceEndPoint().get_glance_backend(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def host():
    pass


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
    click.secho(f"you can use 'pve_cli host get-support-pci-devices' to check it", fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def disk():
    pass


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


# ------------------------------------------------------------------------- #

@cli.group()
def keystone():
    pass


@keystone.command()
def get_ldap_settings():
    value = business.KeystoneEndPoint().get_ldap_settings(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


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
def network():
    pass


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

# ------------------------------------------------------------------------- #

@cli.group()
def nova():
    pass


@nova.command()
def get_nova_allocation_ratio_settings():
    value = business.NovaEndPoint().get_nova_allocation_ratio_settings(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@nova.command()
@click.option('--cpu_allocation_ratio')
@click.option('--ram_allocation_ratio')
@click.option('--disk_allocation_ratio')
@click.option('--vcpu_pin_set')
@click.option('--reserved_host_memory_mb')
def config_host_nova_settings(*args, **kwargs):
    update_dict = {key:value for key, value in kwargs.items() if value is not None}
    value = business.NovaEndPoint().config_host_nova_settings(ctxt={}, config=update_dict)
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@nova.command()
def get_nova_mdev_types_settings():
    value = business.NovaEndPoint().get_nova_mdev_types_settings(ctxt={})
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@nova.command()
@click.argument('pci_address', type=click.STRING)
@click.argument('mdev_type_name', type=click.STRING)
def config_nova_mdev_types_settings(pci_address, mdev_type_name):
    """
    PCI_ADDRESS     pci设备的地址，记得补0，否则报错

    MDEV_TYPE_NAME  这个vgpu支持的mdev_type
    """
    value = business.NovaEndPoint().config_nova_mdev_types_settings({}, pci_address, mdev_type_name)
    assert isinstance(value, dict), f'return value should be dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@nova.command()
def get_pci_device_spec():
    """
    返回nova针对于直通PCI设备的配置
    """
    value = business.NovaEndPoint().get_pci_device_spec({})
    assert type(value) in [list, dict], f'return value should be list/dict, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')


@nova.command()
@click.argument('vendor', type=click.STRING)
def set_pci_device_spec(vendor):
    """
    VENDOR  厂家的设备号
    """
    value = business.NovaEndPoint().set_pci_device_spec({}, vendor)
    assert isinstance(value, list), f'return value should be list, but is {type(value)}'
    value = json.dumps(value, indent=4)
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def kolla():
    pass


@kolla.command()
def deploy():
    value = business.KollaEndPoint().deploy(ctxt={})
    click.secho(value, fg='green')


@kolla.command()
def install_kolla_ansible():
    value = business.KollaEndPoint().install_kolla_ansible(ctxt={})
    click.secho(value, fg='green')


@kolla.command()
@click.argument('ceph_admin_node')
def access_ceph(ceph_admin_node):
    value = business.KollaEndPoint().access_ceph(ctxt={}, ceph_admin_node=ceph_admin_node)
    click.secho(value, fg='green')


@kolla.command()
@click.argument('host')
def add_compute_node(host):
    value = business.KollaEndPoint().add_compute_node(ctxt={}, host=host)
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

@cli.group()
def license():
    pass

# lincese_string_help = 'astute generate license string, can copy from mysql'

@license.command()
def get_machine_code_string():
    value = business.LicenseEndPoint().get_machine_code_string(ctxt={})
    click.secho(value, fg='green')


@license.command()
@click.argument('lincese_string')
def get_apply_license_string(lincese_string):
    value = business.LicenseEndPoint().get_apply_license_string(ctxt={}, license_str=lincese_string)
    click.secho(value, fg='green')


@license.command()
@click.argument('lincese_string')
def valid_license_string(lincese_string):
    value = business.LicenseEndPoint().valid_license_string(ctxt={}, license_str=lincese_string)
    click.secho(value, fg='green')


@license.command()
@click.argument('lincese_string')
def get_license_dict(lincese_string):
    """asdadsfasdfasdfdasfad"""
    value = business.LicenseEndPoint().get_license_dict(ctxt={}, license_str=lincese_string)
    click.secho(value, fg='green')

# ------------------------------------------------------------------------- #

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
    msg = f"new pve_cli without click wrap file has created as {backup_file_path}"
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
@click.option('--compute', is_flag=True, default=False)
@click.option('--control', is_flag=True, default=False)
@click.argument('command', type=click.STRING)
def execute_on_multi_hosts(compute, control, command):
    """
    在哪种类型的主机上执行命令，命令有空格的话记得引号包裹
    
    例如: pve_cli ssh execute-on-multi-hosts 'date'
    """
    if compute and control:
        host_type = 'all_type'
    else:
        if compute:
            host_type = 'compute'
        elif control:
            host_type = 'control'
        else:
            host_type = 'all_type'
    business.SshEndPoint().execute_on_multi_hosts(ctxt={}, host_type=host_type, command=command)

# ------------------------------------------------------------------------- #

@nova.command()
@click.argument('instance_uuid', type=click.STRING)
def get_instance_vnc_detail(instance_uuid):
    """
    看某个主机的vnc连接地址和密码
    
    例如: kolla-command vnc get-instance-vnc-detail your-instance-uuid
    """
    columns = ['compute_host', 'instance_name', 'hostname', 'status']
    cmd = f"openstack server show {instance_uuid} -c {' -c '.join(columns)} -f value"
    flag, content = utils.execute_command(cmd)
    assert flag == 0, f"openstack server show {instance_uuid} failed, cmd={cmd}"
    content_list = [i.strip() for i in content.split() if i]
    instance_dict = dict(zip(columns, content_list))
    command = f'docker exec nova_libvirt virsh domdisplay --include-password {instance_uuid}'
    compute_host = instance_dict.get('compute_host')
    flag, content = utils.execute_ssh_command_via_id_rsa(command, SSH_KEY_FILE_PATH, compute_host)
    assert flag == 0, f"virsh domdisplay {instance_uuid} on {compute_host} failed, cmd={command}"
    vnc_dict = utils.virsh_dump_vnc_url_to_dict(content.strip())
    return_dict = {'vnc': vnc_dict, 'instance': instance_dict}
    click.secho(json.dumps(return_dict, indent=4), fg='green')


def main():
    cli()
