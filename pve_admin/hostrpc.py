import os

from pve_admin import rpc
from pve_admin.config import CONF, HOSTRPC_CONF_PATH

from cs_utils import func
from pve_admin import depends


def main():
    func.set_simple_log(f'/var/log/astute/pve_rpc.log')
    func.create_conf_file(HOSTRPC_CONF_PATH)
    depends.chmod_ssh_key_path()
    depends.chmod_scripts_path()
    depends.set_xhci_hcd_to_use_vfio_driver()
    CONF(default_config_files = [HOSTRPC_CONF_PATH])
    rpc.rpc_server()


if __name__ == '__main__':
    main()
