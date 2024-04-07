import os
import json
import logging
import argparse

from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.DescribeSubDomainRecordsRequest import DescribeSubDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest

from cc_utils import execute, func, file, AUTHOR_NAME, AIO_CONF_NAME

LOG = logging.getLogger(__name__)

class DynamicDNS:
    def __init__(self, args_dict: dict):
        self.args_dict = args_dict
        self.client = AcsClient(args_dict["accessKeyId"], args_dict["accessKeySecret"], args_dict["regionId"])
        self.ip_type = "AAAA" if args_dict.get('ipv4_or_ipv6') == 'ipv6' else "A"
        self.domain = args_dict.get('domain')
        self.rr = args_dict.get('rr')
        self.public_ip_txt_path = args_dict.get('public_ip_txt_path')
        self.saved_current_public_ip = self.get_saved_public_ip()
        self.priority = '5'
        self.ttl = 600

    def get_saved_public_ip(self):
        if os.path.exists(self.public_ip_txt_path):
            content = file.read_file_content(self.public_ip_txt_path, mode='r')
            if content:
                return content.strip()
        LOG.warning(f'not get public_ip from {self.public_ip_txt_path}')

    def run(self):
        """
        {'TotalCount': 1, 'PageSize': 20, 'RequestId': '7985813F-7B20-5B7D-AF86-15FE990FA638', 'DomainRecords': {'Record': [{'Status': 'ENABLE', 'RR': 'www', 'Line': 'default', 'Locked': False, 'Type': 'A', 'DomainName': 'chaoshen.icu', 'Value': '1.2.3.4', 'RecordId': '887212231443622912', 'UpdateTimestamp': 1711894085000, 'TTL': 600, 'CreateTimestamp': 1711890734000, 'Weight': 1}]}, 'PageNumber': 1}
        """
        if not self.saved_current_public_ip:
            return
        des_result = self.describe_domain_records(self.ip_type, self.domain)
        LOG.info(des_result)
        if des_result["TotalCount"] == 0:
            self.add_record(self.ip_type, self.saved_current_public_ip, self.rr, self.domain)
        else:
            request_id = des_result["DomainRecords"]["Record"][0]["RecordId"]
            LOG.info("RequestID: " + request_id)
            request_value = des_result["DomainRecords"]["Record"][0]["Value"]
            request_rr = des_result["DomainRecords"]["Record"][0]["RR"]
            if self.saved_current_public_ip != request_value or self.rr != request_rr:
                self.update_record(self.ip_type, self.saved_current_public_ip, self.rr, request_id)
                LOG.info(f'{self.rr}.{self.domain}被解析到{self.saved_current_public_ip}')

    def describe_domain_records(self, record_type, subdomain):
        LOG.info("域名解析记录查询")
        request = DescribeDomainRecordsRequest()
        request.set_accept_format('json')
        request.set_Type(record_type)
        request.set_DomainName(subdomain)
        response = self.client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        result = json.loads(response)
        logging.debug(result)
        return result

    def describe_subdomain_records(self, record_type, subdomain):
        LOG.info("子域名解析记录查询")
        request = DescribeSubDomainRecordsRequest()
        request.set_accept_format('json')
        request.set_Type(record_type)
        request.set_SubDomain(subdomain)
        response = self.client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        result = json.loads(response)
        logging.debug(result)
        return result

    def add_record(self, record_type, value, rr, domain_name):
        LOG.info("添加域名解析记录")
        request = AddDomainRecordRequest()
        request.set_accept_format('json')
        request.set_Priority(self.priority)
        request.set_TTL(self.ttl)
        request.set_Value(value)
        request.set_Type(record_type)
        request.set_RR(rr)
        request.set_DomainName(domain_name)
        response = self.client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        result = json.loads(response)
        logging.debug(result)
        return result

    def update_record(self, record_type, value, rr, record_id):
        LOG.info("更新域名解析记录")
        request = UpdateDomainRecordRequest()
        request.set_accept_format('json')
        request.set_Priority(self.priority)
        request.set_TTL(self.ttl)
        request.set_Value(value)
        request.set_Type(record_type)
        request.set_RR(rr)
        request.set_RecordId(record_id)
        response = self.client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        logging.debug(response)
        return response
   

def get_public_ip_default_value(key):
    flag, content = execute.crudini_get_config(ini_path=f'/etc/{AUTHOR_NAME}/{AIO_CONF_NAME}', section='public_ip', key=key)
    if flag == 0 and content:
        return content
    LOG.warning(f"read default public_ip key={key} config failed, please set it!")

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', help='domain url', default=get_public_ip_default_value('domain'))
    parser.add_argument('--accessKeyId', help='download.txt path', default=get_public_ip_default_value('accessKeyId'))
    parser.add_argument('--accessKeySecret', help='save dir', default=get_public_ip_default_value('accessKeySecret'))
    parser.add_argument('--regionId', help='download.txt path', default=get_public_ip_default_value('regionId'))
    parser.add_argument('--rr', help='url prifix, like www', default=get_public_ip_default_value('rr'))
    parser.add_argument('--public_ip_txt_path', help='public_ip_txt_path', default=get_public_ip_default_value('public_ip_txt_path'))
    parser.add_argument('--ipv4_or_ipv6', help='ipv4_or_ipv6', default=get_public_ip_default_value('ipv4_or_ipv6'))
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/ddns.log')
    args = parse_arguments()
    args_dict = args.__dict__
    for key, value in args_dict.items():
        if not value:
            raise Exception(f'please set {key} value')
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/ddns.log')
    LOG.info('--------- ddns start ---------')
    DynamicDNS(args_dict).run()
    LOG.info('--------- ddns end ---------')
