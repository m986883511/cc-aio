#!/bin/bash

# 绑定pid文件 避免多人操作
pid_file="/tmp/add_as_ceph_node.pid"
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

function main(){
    local current_hostname=$(hostname)
    local host_number="${current_hostname#host}"  # 提取主机号，去除前缀"host"
    host_number="${host_number#0}"  # 去除可能的前导零
    local ceph_public_ip="192.222.13.$(printf "%d" "$host_number")"
    ceph orch host add $current_hostname $ceph_public_ip
    completed $? "ceph orch host add $current_hostname"
    hostcli ceph set-current-node-as-mon-mgr-node
    completed $? "set-current-node-as-mon-mgr-node"
    wait_current_node_install_ceph_completed
}

with_logs_piped $LOG_PATH main $@
