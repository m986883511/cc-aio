import os
import base64
import hashlib
import logging
import traceback
from datetime import datetime

from oslo_config import cfg

from cs_utils import execute, func, file, _

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class LicenseEndPoint(object):

    def __init__(self):
        self.LICENSE_ERROR = {
            "0": {'state': 'normal', 'msg': _("License is ok.")},
            "255": {'state': 'unknown_error', 'msg': _("Unknown license error!")},
            "254": {'state': 'invalid_license', 'msg': _("Invalid license!")},
            "253": {'state': 'machine_mismatch', 'msg': _("License machine code does not match!")},
            "252": {'state': 'time_expired', 'msg': _("License is expired!")}
        }
        self.ATLICENSE_EXE = '/usr/bin/atlicense'
        self.check_rpm = 'docker-ce'
        self.CORRECT_MD5 = ['67520e4bd0c9ddc133916b8447e7f085', '9523385c147b1f00576fcfe6e1ef9641']  # amd64, arm64

    def _get_license_lic_sig(self, license_str) -> dict:
        assert isinstance(license_str, str), f'license is not str, it is {type(license_str)}'
        license_str = license_str.replace('\n\n', '-')
        license_str = license_str.replace('\n', '')
        license = [i for i in license_str.split('-') if i]
        license_split_len = len(license)
        if license_split_len != 2:
            msg = f'split license length error is {license_split_len}, license_str={license_str}'
            return False, msg
        else:
            data = dict(lic=license[0], sig=license[1])
            return True, data

    def _get_install_date_seconds(self):
        execute.execute_command('rm -f /var/lib/rpm/db.*')
        flag, content = execute.execute_command(f"rpm -qi docker-ce | grep 'Install Date'")
        execute.completed(flag, 'get install data', content)
        install_date_str = func.get_string_split_list(content, split_flag='te:')[-1]
        install_time_format = "%a %d %b %Y %H:%M:%S %p %Z"
        # 将安装时间字符串转换为datetime对象
        install_time = datetime.strptime(install_date_str, install_time_format)
        # 计算时间与1970年1月1日之间的时间差
        epoch = datetime(1970, 1, 1)
        time_difference = install_time - epoch
        # 将时间差转换为秒数
        seconds = int(time_difference.total_seconds())
        # 打印转换后的秒数
        return seconds

    def _get_final_expired_date_seconds(self, install_date_seconds, effective_days, expired_date):
        if effective_days == 0:
            # 无限期的license 认为100年
            effective_days = 100 * 365
        expired_date_seconds_1 = install_date_seconds + effective_days * 24 * 3600
        if expired_date:
            # 将日期字符串转换为datetime对象
            date = datetime.strptime(expired_date, "%Y-%m-%d")
            # 计算日期与1970年1月1日之间的时间差
            epoch = datetime(1970, 1, 1)
            time_difference = date - epoch
            expired_date_seconds_2 = int(time_difference.total_seconds())
        else:
            expired_date_seconds_2 = 0
        LOG.info(f'expired_date_seconds_1={expired_date_seconds_1}, expired_date_seconds_2={expired_date_seconds_2}')
        return max(expired_date_seconds_1, expired_date_seconds_2)

    def get_license_dict(self, ctxt, license_str=None):
        LOG.info('get license dict..')
        if license_str:
            assert isinstance(license_str, str), f'license is not str, it is {type(license_str)}'
            LOG.info('valid skyline import license str')
            flag, value = self._get_license_lic_sig(license_str)
            if not flag:
                return dict(ok=False, msg=value)
            license_dict = file.ini_string_to_dict(value['lic'])
        else:
            LOG.info('import is temporary_license_dict')
            license_dict = self.get_temporary_license_dict(ctxt=ctxt)
        install_date_seconds = self._get_install_date_seconds()
        effective_days = license_dict['limitation']['effective_days']
        effective_days = int(effective_days) if effective_days else 0
        expired_date = license_dict['limitation']['expired_date']
        license_dict['limitation']['install_date'] = datetime.utcfromtimestamp(install_date_seconds).strftime("%Y-%m-%d")
        final_expired_date_seconds = self._get_final_expired_date_seconds(install_date_seconds, effective_days, expired_date)
        license_dict['limitation']['expired_date'] = datetime.utcfromtimestamp(final_expired_date_seconds).strftime("%Y-%m-%d")
        return license_dict

    def valid_license_string(self, ctxt, license_str):
        LOG.info('valid license string..')
        assert isinstance(license_str, str), f'license is not str, it is {type(license_str)}'
        with open(self.ATLICENSE_EXE, 'rb') as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        verify_md5 = md5 in self.CORRECT_MD5
        if not verify_md5:
            return dict(ok=False, msg='atlicense md5 is not corrent')
        flag, value = self._get_license_lic_sig(license_str)
        if not flag:
            return dict(ok=False, msg=value)
        return_code, content = execute.execute_command(f"atlicense -l {value['lic']} -s {value['sig']}",
                                                       return_code_dict=self.LICENSE_ERROR)
        if return_code != 0:
            return dict(ok=False, msg=content)
        return dict(ok=True, msg=content)

    def get_machine_code_string(self, ctxt) -> str:
        from pve_admin.business import HostEndPoint
        machine_code_dict = HostEndPoint().get_machine_code(ctxt={})
        return machine_code_dict['machine_code']

    def get_apply_license_string(self, ctxt, update_dict=None) -> str:
        # update_dict = {'name': str, 'max_compute_nodes': int, 'machine_code': str}
        # FLAG20240316 skyline-apiserver项目联合修改
        update_dict = update_dict or {}
        if 'machine_code' not in update_dict:
            update_dict['machine_code'] = self.get_machine_code_string(ctxt={})

        temporary_license_dict = self.get_temporary_license_dict(ctxt=ctxt)
        for section, section_dict in temporary_license_dict.items():
            for key, value in section_dict.items():
                if key in update_dict:
                    section_dict[key] = update_dict[key]

        lic = "[default]"
        lic += "\r\n" + "type              = " + "Enterprise"
        lic += "\r\n"
        lic += "\r\n" + "[customer]"
        lic += "\r\n" + "name              = " + data.get('name', '')
        lic += "\r\n"
        lic += "\r\n" + "[limitation]"
        lic += "\r\n" + "max_compute_nodes = " + str(data['max_compute_nodes'])
        lic += "\r\n" + "effective_days    = " + str(data['effective_days'])
        lic += "\r\n" + "expired_date      = " + str(data['expired_date'])
        lic += "\r\n" + "machine_code      = " + data.get('machine_code', '')
        mm = base64.b64encode(lic.encode('utf-8')).decode('utf-8')
        return mm
    
    def get_temporary_license_dict(self, ctxt) -> dict:
        data = {
            'default':{
                'type': 'temporary'
            },
            'customer':{
                'name': 'test'
            },
            'limitation':{
                'max_compute_nodes': 3,
                'machine_code': u'',
                'customer_name': u'test',
                'effective_days': u'30',
                'expired_date': u'',
            }
        }
        return data
