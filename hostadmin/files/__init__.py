import os

hostadmin_files_dir = os.path.dirname(__file__)
hostadmin_ssh_dir = os.path.join(hostadmin_files_dir, 'ssh')
hostadmin_ceph_dir = os.path.join(hostadmin_files_dir, 'ceph')
hostadmin_shell_dir = os.path.join(hostadmin_files_dir, 'shell')
hostadmin_host_dir = os.path.join(hostadmin_files_dir, 'host')


class FilesDir:
    hostadmin = os.path.dirname(hostadmin_files_dir)
    files = hostadmin_files_dir

    class SSH:
        ssh_dir = hostadmin_ssh_dir
        id_rsa = os.path.join(hostadmin_ssh_dir, 'id_rsa')
        id_rsa_pub = os.path.join(hostadmin_ssh_dir, 'id_rsa.pub')

    class Ceph:
        conf = os.path.join(hostadmin_ceph_dir, 'ceph.conf')
    
    class Host:
        pci_device_id = os.path.join(hostadmin_host_dir, 'pci-device-id.ini')
        chrony_conf = os.path.join(hostadmin_host_dir, 'chrony.conf')
        ustc_apt_sources = os.path.join(hostadmin_host_dir, 'ustc-sources.list')
    
    class Shell:
        shell_dir = hostadmin_shell_dir
        install_base_env = os.path.join(hostadmin_shell_dir, 'install_base_env.sh')
        deploy_kolla = os.path.join(hostadmin_shell_dir, 'deploy_kolla.sh')
        install_kolla_ansible = os.path.join(hostadmin_shell_dir, 'install_kolla_ansible.sh')
        add_compute_node = os.path.join(hostadmin_shell_dir, 'add_compute_node.sh')
        kolla_access_ceph = os.path.join(hostadmin_shell_dir, 'kolla_access_ceph.sh')
        install_as_ceph_admin_node = os.path.join(hostadmin_shell_dir, 'install_as_ceph_admin_node.sh')
        add_as_ceph_node = os.path.join(hostadmin_shell_dir, 'add_as_ceph_node.sh')
