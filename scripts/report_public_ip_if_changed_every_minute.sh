#!/bin/bash
PUBLIC_IP_SAVED_PATH="/tmp/public_ip.txt"
# WETCHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=8e3e4d48-0bc0-4b78-ab56-c36825bc8e9b"
FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/f54a776d-436f-4be1-8e08-f7ce25fde25b"

WHO_AM_I="陈永胜家"
RUN_AS_SOURCE_FLAG=
PUBLIC_IP=""
PUBLIC_IP_READ_CONTENT=""
CURRENT_SCRIPT_DIR=
CURRENT_SCRIPT_NAME=
CURRENT_SCRIPT_PATH=
DEST_SCRIPT_DIR="/usr/local/bin"
DEST_SCRIPT_NAME="report_public_ip_if_changed_every_minute.sh"
LOG_PATH="/var/log/$DEST_SCRIPT_NAME.log"
DEST_SCRIPT_PATH="$DEST_SCRIPT_DIR/$DEST_SCRIPT_NAME"

function completed() {
    if [[ $1 -eq 0 ]]; then
        echo -e "${GREEN}$2 success${PLAIN}"
    else
        echo -e "${RED}$2 failed${PLAIN}"
        if [ $# -ge 3 ]; then
            echo -e "$3"
        fi
        if [ -z "$RUN_AS_SOURCE_FLAG" ]; then
            echo "not run as source, exit script"
            exit 1
        fi
    fi
}

function get_public_ip(){
    echo "enter function name: ${FUNCNAME[0]}"
    result=$(curl cip.cc|grep ^IP)
    completed $? "curl cip.cc"
    PUBLIC_IP=$(echo $result| awk '{print $3}')
    completed $? "calc public ip"
    echo "public ip is $PUBLIC_IP"
}

function write_public_ip(){
    echo "enter function name: ${FUNCNAME[0]}"
    echo $PUBLIC_IP > $PUBLIC_IP_SAVED_PATH
    completed $? "saved $PUBLIC_IP to $PUBLIC_IP_SAVED_PATH"
}

function read_public_ip(){
    echo "enter function name: ${FUNCNAME[0]}"
    if [ -e "$PUBLIC_IP_SAVED_PATH" ]; then
        PUBLIC_IP_READ_CONTENT=$(<"$PUBLIC_IP_SAVED_PATH")
        echo "$PUBLIC_IP_SAVED_PATH content: $PUBLIC_IP_READ_CONTENT"
    else
        echo "$PUBLIC_IP_SAVED_PATH does not exist or is empty."
        PUBLIC_IP_READ_CONTENT=""
    fi
}

function set_crontab(){
    echo "enter function name: ${FUNCNAME[0]}"
    if crontab -l|grep -qF $DEST_SCRIPT_NAME; then
        echo "no need add $DEST_SCRIPT_NAME to crontab"
    else
        echo "add $DEST_SCRIPT_NAME to crontab"
        crontab -l > mycron
        #echo new cron into cron file
        echo "* * * * * $DEST_SCRIPT_PATH" >> mycron
        #install new cron file
        crontab mycron
        completed $? "add $DEST_SCRIPT_NAME to crontab"
        rm mycron
    fi
}

function send_change_public_ip(){
    echo "enter function name: ${FUNCNAME[0]}"
    text="I am $WHO_AM_I, public ip changed to $PUBLIC_IP"
    curl -X POST -H "Content-Type: application/json" -d '{"msg_type": "text", "content": {"text": "'"$text"'"}}' "$FEISHU_WEBHOOK"
    completed $? "send public_ip=$PUBLIC_IP to webhook"
}

function check_public_changed(){
    read_public_ip
    get_public_ip
    if [ "$PUBLIC_IP" == "$PUBLIC_IP_READ_CONTENT" ]; then
        echo "public ip is $PUBLIC_IP not change"
    else
        echo "public ip change to $PUBLIC_IP"
        send_change_public_ip
    fi
}

function run_directly(){
    start_log
    echo "enter function name: ${FUNCNAME[0]}"
    echo "Script is being run directly, $CURRENT_SCRIPT_PATH run at $(date)"
    check_public_changed
    write_public_ip
    copy_this_cripts_to_usr_local_bin
    set_crontab
}

function start_log(){
    printf '#%.0s' {1..50}
    echo -e '\n'
}

function run_as_source(){
    start_log
    echo "enter function name: ${FUNCNAME[0]}"
    echo "Script is being sourced, $CURRENT_SCRIPT_PATH run at $(date)"
    echo "not run any func"
}

function with_logs_piped() {
  local logfile=$1; shift
  "$@" > >(tee -a -- "$logfile") 2>&1
}

function copy_this_cripts_to_usr_local_bin(){
    echo "enter function name: ${FUNCNAME[0]}"
    echo "current file is $CURRENT_SCRIPT_PATH"
    if [[ "$CURRENT_SCRIPT_PATH" == "$DEST_SCRIPT_PATH" ]]; then
        echo "no need copy $CURRENT_SCRIPT_PATH"
    else
        /bin/cp $CURRENT_SCRIPT_PATH $DEST_SCRIPT_PATH
        completed $? "copy $CURRENT_SCRIPT_PATH to $DEST_SCRIPT_PATH"
    fi
    chmod 777 $DEST_SCRIPT_PATH
    completed $? "chmod $DEST_SCRIPT_PATH"
}

if [[ "$0" == "$BASH_SOURCE" ]]; then
    CURRENT_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    CURRENT_SCRIPT_NAME=$(basename $0)
    CURRENT_SCRIPT_PATH=$CURRENT_SCRIPT_DIR/$CURRENT_SCRIPT_NAME
    echo "$CURRENT_SCRIPT_PATH"
    with_logs_piped $LOG_PATH run_directly
else
    RUN_AS_SOURCE_FLAG=1
    CURRENT_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    CURRENT_SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
    CURRENT_SCRIPT_PATH=$CURRENT_SCRIPT_DIR/$CURRENT_SCRIPT_NAME
    echo "$CURRENT_SCRIPT_PATH"
    with_logs_piped $LOG_PATH run_as_source
fi