# hostrpc启动时候的预加载程序
import os
import logging

from hostadmin import business
from hostadmin.config import AUTHOR_NAME
from cc_utils import execute
from hostadmin.files import FilesDir

LOG = logging.getLogger(__name__)


def set_xhci_hcd_to_use_vfio_driver():
    value_dict = business.HostEndPoint().get_support_pci_devices({})
    gpu_dict = value_dict.get('gpu', {}) or {}
    for pci_id, value in gpu_dict.items():
        gpu_name = value.get('name')
        for device_dict in value.get('all_devices', []) or []:
            driver = device_dict.get('driver') or ''
            sub_pci_id = device_dict.get('pci_id') or ''
            if driver.lower() != 'xhci_hcd':
                continue
            LOG.info(f'set {gpu_name} sub_pci_id={sub_pci_id} xhci_hcd to vfio-pci')
            assert sub_pci_id, f'{sub_pci_id} can not be empty'
            cmd = f"pci_id={sub_pci_id} && echo $pci_id > /sys/bus/pci/devices/$pci_id/driver/unbind && echo $pci_id >/sys/bus/pci/drivers/vfio-pci/bind"
            flag, content = execute.execute_command(cmd)
            if flag == 0:
                LOG.info(f'set {gpu_name} sub_pci_id={sub_pci_id} xhci_hcd to vfio-pci success')
            else:
                LOG.error(f'set {gpu_name} sub_pci_id={sub_pci_id} xhci_hcd to vfio-pci failed, err={content}')


def chmod_ssh_key_path():
    cmd = f'chmod 600 {FilesDir.SSH.ssh_dir}/*'
    flag, content = execute.execute_command(cmd)
    if flag == 0:
        LOG.info(f'set ssh key path 600 success')
    else:
        LOG.error(f'set ssh key path {FilesDir.SSH.ssh_dir} 600 failed, err={content}')


def chmod_scripts_path():
    path = f'/usr/local/{AUTHOR_NAME}/scripts'
    if not os.path.exists(path):
        LOG.error(f'{path} not exist')
        return
    cmd = f'chmod -R 755 {path}/*'
    flag, content = execute.execute_command(cmd)
    if flag == 0:
        LOG.info(f'set scripts path 755 success')
    else:
        LOG.error(f'set scripts path {path} 755 failed, err={content}')
