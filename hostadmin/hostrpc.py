import os

from hostadmin import rpc
from hostadmin.config import CONF, HOSTRPC_CONF_PATH

from cs_utils import func
from hostadmin import depends


def main():
    func.set_simple_log(f'/var/log/cs/hostrpc.log')
    func.create_conf_file(HOSTRPC_CONF_PATH)
    depends.chmod_ssh_key_path()
    depends.chmod_scripts_path()
    depends.set_xhci_hcd_to_use_vfio_driver()
    CONF(default_config_files = [HOSTRPC_CONF_PATH])
    rpc.rpc_server()


if __name__ == '__main__':
    main()
