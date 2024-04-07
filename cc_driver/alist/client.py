import requests

from cc_driver.alist import storage

class Client():
    def __init__(self, alist_url, admin_password):
        self.alist_url = alist_url
        self.admin_password = admin_password
        token = self.login()
        self.headers = {'Authorization': token}
        self.storage = storage.Storage(self.alist_url, self.headers)
    
    def login(self):
        url = f'{self.alist_url}/api/auth/login'
        data = {"username":"admin","password":self.admin_password}
        res= requests.post(url, json=data)
        if res.status_code / 100 == 2:
            res_dict = res.json()
            token = res_dict.get('data', {}).get('token') or ''
            if not token:
                raise Exception(f'login {self.alist_url} use {self.admin_password} failed, token is empty!')
            return token
        else:
            raise Exception(f'login {self.alist_url} use {self.admin_password} failed')
