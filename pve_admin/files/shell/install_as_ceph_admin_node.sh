#!/bin/bash

# 绑定pid文件 避免多人操作
pid_file="/tmp/install_as_ceph_admin_node.pid"
if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file")

    if ps -p "$pid" > /dev/null; then
        echo "Check pid file $pid_file"
        echo "Another instance of the script is already running with PID $pid."
        exit 1
    fi
fi
cleanup() {
    if [ -f "$pid_file" ]; then
        rm "$pid_file"
    fi
    exit
}
trap cleanup EXIT
echo $$ > "$pid_file"

WORK_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$WORK_DIR" || exit 1

source ./utils.sh

sleep 1

ceph_config_default_pool_size=$1
if [ -z "$ceph_config_default_pool_size" ]; then
    ceph_config_default_pool_size=3
fi
echo "ceph_config_default_pool_size is $ceph_config_default_pool_size"
calling_script=$(ps -p $PPID -o comm=)

function change_pool_default_size(){
    echo "enter function name: ${FUNCNAME[0]}"
    local hostadmin_ceph_conf_path=$(python -c "from pve_admin.files import FilesDir; print(FilesDir.Ceph.conf)")
    crudini --set $hostadmin_ceph_conf_path global osd_pool_default_size $ceph_config_default_pool_size
    completed $? "set osd_pool_default_size as $1"
}

function install_ceph_admin_node(){
    echo "enter function name: ${FUNCNAME[0]}"
    local hostadmin_ceph_conf_path=$(python -c "from pve_admin.files import FilesDir; print(FilesDir.Ceph.conf)")
    local SSH_PRIVATE_KEY_PATH=$(python -c "from pve_admin.files import FilesDir; print(FilesDir.SSH.id_rsa)")
    local SSH_PUBLIC_KEY_PATH=$(python -c "from pve_admin.files import FilesDir; print(FilesDir.SSH.id_rsa_pub)")
    local current_hostname=$(hostname)
    local host_number="${current_hostname#host}"  # 提取主机号，去除前缀"host"
    host_number="${host_number#0}"  # 去除可能的前导零
    local ceph_public_ip="192.222.13.$(printf "%d" "$host_number")"  # 构建新的IP地址
    cephadm bootstrap --mon-ip $ceph_public_ip --skip-monitoring-stack --initial-dashboard-password password --cluster-network 192.222.12.0/24 --ssh-private-key $SSH_PRIVATE_KEY_PATH --ssh-public-key $SSH_PUBLIC_KEY_PATH -c $hostadmin_ceph_conf_path
    completed $? "install ceph admin node"
}

function scp_etc_conf_to_master_node(){
    echo "enter function name: ${FUNCNAME[0]}"
    echo "Calling script: $calling_script"
    if [ -v SSH_CONNECTION ]; then
        if [ "$calling_script" = 'sshd' ]; then
            REPO_SERVER_IP=$(echo $SSH_CONNECTION | awk '{print $1}')
            pve_cli ssh scp-dir-to-remote-host $REPO_SERVER_IP /etc/ceph /etc/
            completed $? "scp /etc/ceph to $REPO_SERVER_IP"
        fi
    fi
    REPO_SERVER_IP=$(echo $SSH_CONNECTION | awk '{print $1}')
}

function config_ceph_cluster(){
    echo "enter function name: ${FUNCNAME[0]}"
    ceph orch apply mon --unmanaged
    completed $? "ceph orch apply mon --unmanaged"
    ceph orch apply mgr --unmanaged
    completed $? "ceph orch apply mgr --unmanaged"
    pve_cli ceph set-current-node-as-mon-mgr-node
    completed $? "set-current-node-as-mon-mgr-node"
}

function main(){
    local current_node_installed_ceph
    current_node_installed_ceph=$(crudini --get $ACD_CONFIG_PATH ceph current_node_installed_ceph)
    if [ $? == 0 ]; then
        if [ "$current_node_installed_ceph" = "true" ] || [ "$current_node_installed_ceph" = "True" ]; then
            echo "already installed ceph"
            return
        fi
    fi
    change_pool_default_size
    install_ceph_admin_node
    config_ceph_cluster
    wait_current_node_install_ceph_completed
    scp_etc_conf_to_master_node

    crudini --set $ACD_CONFIG_PATH ceph current_node_installed_ceph true
    completed $? "set current_node_installed_ceph as true"
}

with_logs_piped $LOG_PATH main $@
