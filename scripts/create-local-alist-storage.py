import os
import json
import logging
import argparse

from cc_utils import execute, func, file, AUTHOR_NAME, AIO_CONF_NAME
from cc_driver.alist import client

LOG = logging.getLogger(__name__)

def get_alist_default_value(key):
    flag, content = execute.crudini_get_config(ini_path=f'/etc/{AUTHOR_NAME}/{AIO_CONF_NAME}', section='alist', key=key)
    if flag == 0 and content:
        return content
    LOG.warning(f"read default alist key={key} config failed, please set it!")


def get_samba_default_value(key):
    flag, content = execute.crudini_get_config(ini_path=f'/etc/{AUTHOR_NAME}/{AIO_CONF_NAME}', section='samba', key=key)
    if flag == 0 and content:
        return content
    LOG.warning(f"read default samba key={key} config failed, please set it!")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--alist_ip', help='alist ip', default='localhost')
    parser.add_argument('--admin_password', help='admin password', default=get_alist_default_value('default_admin_password'))
    parser.add_argument('--default_share_path', help='download.txt path', default=get_samba_default_value('default_share_path'))
    args = parser.parse_args()
    return args


class CreateLocalAlistStorage():
    def __init__(self, args_dict):
        self.alist_url = f"http://{args_dict['alist_ip']}:5244"
        self.admin_password = args_dict['admin_password']
        self.default_share_path = args_dict['default_share_path']
        self.alist_client = client.Client(self.alist_url, self.admin_password)
        self.storage_client = self.alist_client.storage
        self.mount_path = f'/{func.get_current_node_hostname()}'

    def get_already_create_id(self):
        current_storages = self.storage_client.list_storage()
        content = current_storages.get('data', {}).get('content') or []
        for value_dict in content:
            mount_path = value_dict['mount_path']
            if mount_path == self.mount_path:
                return value_dict['id']

    def run(self):
        already_create_id = self.get_already_create_id()
        if already_create_id:
            self.storage_client.remove_storage(already_create_id)
        self.storage_client.create_storage(local_path=self.default_share_path)


if __name__ == '__main__':
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/create-local-alist-storage.log')
    args = parse_arguments()
    args_dict = args.__dict__
    LOG.info(args_dict)
    for key, value in args_dict.items():
        if not value:
            raise Exception(f'please set {key} value')
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/create-local-alist-storage.log')
    LOG.info('--------- create-local-alist-storage start ---------')
    CreateLocalAlistStorage(args_dict).run()
    LOG.info('--------- create-local-alist-storage end ---------')
