#!/bin/bash

# 绑定pid文件 避免多人操作
pid_file="/tmp/add_compute_node.pid"
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
# set -e
# set -u
# set -o pipefail

WORK_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$WORK_DIR" || exit 1

source ./utils.sh

need_add_node=$1
if [ -z $need_add_node ]; then
  completed 1 "add_compute_node.sh need a node param"
fi

function main(){
    execute_kolla_generate
    execute_kolla_add_nodes $need_add_node
}

with_logs_piped $LOG_PATH main $@
