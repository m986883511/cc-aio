import os
import logging

from hostadmin import rpc
from hostadmin.config import CONF, HOSTRPC_CONF_PATH

from cc_utils import func, AUTHOR_NAME
from hostadmin import depends

LOG = logging.getLogger(__name__)


def main():
    func.set_simple_log(f'/var/log/{AUTHOR_NAME}/hostadmin.log')
    LOG.info("--------- hostrpc service start ---------")
    func.create_conf_file(HOSTRPC_CONF_PATH)
    depends.chmod_ssh_key_path()
    depends.chmod_scripts_path()
    depends.set_xhci_hcd_to_use_vfio_driver()
    CONF(default_config_files = [HOSTRPC_CONF_PATH])
    rpc.rpc_server()


if __name__ == '__main__':
    main()
