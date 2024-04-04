#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import logging
import traceback

import jsonrpclib
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

from cg_utils import func
from hostadmin import hostcli, business
from hostadmin.config import CONF

LOG = logging.getLogger(__name__)


def get_all_support_funcs():
    all_endpoints = [i for i in dir(business) if i.endswith('EndPoint')]
    result = {}
    for endpoint in all_endpoints:
        moudule = getattr(business, endpoint)
        func_names = func.find_class_functions_with_param(moudule, 'ctxt')
        for func_name in func_names:
            result[func_name] = moudule
    return result


def do_work(func_name, **kwargs):
    all_support_funcs = get_all_support_funcs()
    if func_name not in all_support_funcs:
        return f'func_name={func_name} is not support, support is {list(all_support_funcs.keys())}'
    module = all_support_funcs[func_name]
    func_obj = getattr(module(), func_name)
    return func_obj(**kwargs)


def rpc_server():
    current_hostname = func.get_current_node_hostname()
    all_support_funcs = get_all_support_funcs()
    support_func_names = list(all_support_funcs.keys())
    LOG.info(f"support_func_names={support_func_names}")
    ip_222 = func.get_hostname_map_ip(current_hostname)
    s = SimpleJSONRPCServer((ip_222, CONF.json_rpc_server_port))
    s.register_function(do_work, 'do_work')
    LOG.info(f"Run hostadmin RPC service, listen on http://{ip_222}:{CONF.json_rpc_server_port}")
    try:
        s.serve_forever()
    except Exception as e:
        LOG.error("start RPC server failed: %s" % str(e))
        LOG.error(traceback.format_exc())
        sys.exit()


def rpc_client(func_name, hostname=None, **kwargs):
    hostname = hostname or func.get_current_node_hostname()
    kwargs['ctxt'] = kwargs.get('ctxt') or {}
    kwargs['func_name'] = func_name
    LOG.info(f'rpc run func={func_name} on hostname={hostname} kwargs={kwargs}')
    ip_222 = func.get_hostname_map_ip(hostname)
    rpc_server_url = f'http://{ip_222}:{CONF.json_rpc_server_port}'
    LOG.info(f'rpc_server_url={rpc_server_url}')
    try:
        s = ret = None
        s = jsonrpclib.Server(rpc_server_url)
        func_obj = getattr(s, 'do_work')
        LOG.info(f"will Call function name={func_name} obj={func_obj}")
        ret = func_obj(**kwargs)
        LOG.info(f"Call function name={func_name} obj={func_obj} succeed: return_value={ret}")
    except Exception as e:
        LOG.error("Call function {} failed: {}".format(func_name, str(e)))
        raise
    LOG.info("Call function {} succeed: return value {}".format(func_name, ret))
    return ret
