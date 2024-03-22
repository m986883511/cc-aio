import sys
import os
import logging

import eventlet
eventlet.monkey_patch()
import oslo_messaging
from oslo_config import cfg

from oslo_messaging import rpc

from hostadmin import config
from hostadmin import business
from hostadmin import depends

CONF = cfg.CONF
LOG = None


def run_depend_tasks():
    # 就算报错也要执行下去，否则hostadmin容器就起不来了
    LOG.info(f'{CONF.package_name} depends start')
    depends.set_xhci_hcd_to_use_vfio_driver()


def main():
    CONF(sys.argv[1:], project=CONF.package_name, version='1.0')
    logging.setup(CONF, CONF.package_name)
    python_logging.captureWarnings(True)

    global LOG
    LOG = logging.getLogger(__name__)
    run_depend_tasks()
    LOG.info(f'{CONF.package_name} server start, topic is {CONF.package_name}, server is {CONF.host}')
    transport = oslo_messaging.get_rpc_transport(cfg.CONF)
    endpoints = [

        business.GlanceEndPoint(),
        business.HostEndPoint(),

        business.CephEndPoint(),
        business.DiskEndPoint(),
        business.NetworkEndPoint(),
        business.KollaEndPoint(),
        business.SshEndPoint()
    ]
    target = oslo_messaging.Target(topic=CONF.package_name, server=CONF.host)
    server = rpc.get_rpc_server(transport, target, endpoints, executor='eventlet')
    server.start()
    server.wait()


if __name__ == '__main__':
    main()
