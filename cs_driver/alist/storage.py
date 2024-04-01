import json

import requests

from cs_utils import func

class Storage():
    def __init__(self, alist_url, headers):
        self.alist_url = alist_url
        self.headers = headers

    def list_storage(self):
        """
        {
            'code': 200, 
            'message': 'success', 
            'data': {
                'content': [
                    {
                        'id': 1, 
                        'mount_path': '/host197', 
                        'order': 0, 
                        'driver': 'Local', 'cache_expiration': 0, 'status': 'work', 
                        'addition': '{
                            "root_folder_path":"/smb",
                            "thumbnail":false,"thumb_cache_folder":"","show_hidden":true,
                            "mkdir_perm":"777","recycle_bin_path":"delete permanently"
                        }', 
                        'remark': '', 'modified': '2024-04-01T21:17:33.225439974+08:00', 
                        'disabled': False, 
                        'enable_sign': False, 'order_by': '', 'order_direction': '', 
                        'extract_folder': '', 'web_proxy': False, 
                        'webdav_policy': 'native_proxy', 'down_proxy_url': ''
                    }
                ], 
                'total': 1
            }
        }
        """
        url = f'{self.alist_url}/api/admin/storage/list'
        res= requests.get(url, headers=self.headers)
        if res.status_code / 100 == 2:
            res_dict = res.json()
            return res_dict
        else:
            raise Exception(f'get list_storage failed')

    def remove_storage(self, id_value):
        url = f'{self.alist_url}/api/admin/storage/delete'
        params = {'id': id_value}
        res= requests.post(url, headers=self.headers, params=params)
        if res.status_code / 100 == 2:
            res_dict = res.json()
            return res_dict
        else:
            raise Exception(f'remove storage_list failed')
    
    def create_storage(self, local_path='/smb'):
        mount_path = func.get_current_node_hostname()
        addition = {
            'root_folder_path': local_path, 
            'thumbnail': False, 
            'thumb_cache_folder': '', 
            'show_hidden': True, 
            'mkdir_perm': '777', 
            'recycle_bin_path': 'delete permanently'
        }
        body={
            "mount_path": f"/{mount_path}",
            "order": 0,
            "remark": "",
            "webdav_policy": "native_proxy",
            "down_proxy_url": "",
            "order_by": "",
            "order_direction": "",
            "extract_folder": "",
            "enable_sign": False,
            "driver": "Local",
            "addition": json.dumps(addition)
        }
        url = f'{self.alist_url}/api/admin/storage/create'
        res= requests.post(url, headers=self.headers, json=body)
        if res.status_code / 100 == 2:
            res_dict = res.json()
            return res_dict
        else:
            raise Exception(f'remove storage_list failed')
        
