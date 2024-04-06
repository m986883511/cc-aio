#!/bin/bash

# 绑定pid文件 避免多人操作
pid_file="/tmp/install_base_env.pid"
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

#####
set -e
set -u
set -o pipefail

WORK_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$WORK_DIR" || exit 1

source ./utils.sh

sleep 1
# echo $SSH_CONNECTION | awk '{print $1}'

# 获取当前脚本的名称
current_script=$(basename "$0")
# 获取调用当前脚本的脚本名称
calling_script=$(ps -p $PPID -o comm=)
echo_log "Current script: $current_script"
echo_log "Calling script: $calling_script"

# set +u
REPO_SERVER_IP="127.0.0.1"
if [ -v SSH_CONNECTION ]; then
    if [ "$calling_script" = 'sshd' ]; then
        REPO_SERVER_IP=$(echo $SSH_CONNECTION | awk '{print $1}')
    fi
fi
# set -u

function check_root_space_bigger_than(){
    echo "enter function name: ${FUNCNAME[0]}"
    local total_root_space
    local total_root_space_g
    local root_min_space
    root_min_space=$(crudini --get $PVETUI_CONFIG_PATH base_env root_min_space)
    completed $? "get $PVETUI_CONFIG_PATH configed root_min_space"
    total_root_space=$(df -h / | awk 'NR==2 {print $2}')
    completed $? "get root space"
    total_root_space_g=$(python3 -c "$(cat << EOF
root_space_size='$total_root_space'
root_space_size=root_space_size.lower()
number, end = float(root_space_size[:-1]), root_space_size[-1]
if 'g' == end:
    size=number
elif 't' == end:
    size=number*1024
else:
    size=0
print(int(size))
EOF
)")
    echo "root space is $total_root_space_g"
    if [ "$total_root_space_g" -gt $root_min_space ]; then
        echo "root space bigger than ${root_min_space}GB"
    else
        completed 1 "check root space bigger than ${root_min_space}GB"
    fi
}

function main(){
    check_root_space_bigger_than
    get_pve_ip
    echo_log "REPO_SERVER_IP is $REPO_SERVER_IP"
    install_pve_base_env
    change_ssh_strict_host_no
    create_pip_conf $REPO_SERVER_IP
    install_base_python_packages
    blacklist_driver

    pip install pbr
    completed $? "install pbr python package"
    pip install --use-deprecated=legacy-resolver --upgrade cg-aio
    completed $? "install cg-aio python package"
    start_hostrpc_server
}

with_logs_piped $LOG_PATH main $@
