#!/bin/bash
. /etc/profile
. ~/.bash_profile
AUTHOR_NAME="cc"
WHO_AM_I="$(hostname)"
RUN_AS_SOURCE_FLAG=
PUBLIC_IP=""
PUBLIC_IP_READ_CONTENT=""
CURRENT_SCRIPT_DIR=
CURRENT_SCRIPT_NAME=
CURRENT_SCRIPT_PATH=
DEST_SCRIPT_DIR="/usr/local/bin"
DEST_SCRIPT_NAME="report_public_ip_if_changed_robot.sh"
LOG_DIR="/var/log/$AUTHOR_NAME"
mkdir -p $LOG_DIR
LOG_PATH="$LOG_DIR/cron.log"
DEST_SCRIPT_PATH="$DEST_SCRIPT_DIR/$DEST_SCRIPT_NAME"
AIO_CONF_NAME='aio.conf'
AIO_CONF_PATH="/etc/$AUTHOR_NAME/$AIO_CONF_NAME"

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

PUBLIC_IP_SAVED_PATH=$(crudini --get $AIO_CONF_PATH public_ip public_ip_txt_path)
completed $? 'read public_ip public_ip_txt_path'
if [ -z "$PUBLIC_IP_SAVED_PATH" ];then
    PUBLIC_IP_SAVED_PATH="/tmp/public_ip.txt"
fi
FEISHU_WEBHOOK_UUID=$(crudini --get $AIO_CONF_PATH public_ip feishu_webhook_uuid)
completed $? 'read public_ip feishu_webhook_uuid'
IPV4_OR_IPV6=$(crudini --get $AIO_CONF_PATH public_ip ipv4_or_ipv6)
completed $? 'read public_ip ipv4_or_ipv6'
FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/$FEISHU_WEBHOOK_UUID"

function get_public_ipv4(){
    echo "enter function name: ${FUNCNAME[0]}"
    result=$(curl cip.cc|grep ^IP)
    completed $? "curl cip.cc"
    PUBLIC_IP=$(echo $result| awk '{print $3}')
    completed $? "calc public ip"
    echo "public ip is $PUBLIC_IP"
}

function get_public_ipv6(){
    echo "enter function name: ${FUNCNAME[0]}"
    result=$(curl https://v6.ident.me)
    completed $? "curl https://v6.ident.me"
    PUBLIC_IP=$result
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
    if [ -z "$FEISHU_WEBHOOK_UUID" ];then
        completed $? "not config feishu webhook, skip send"
    else
        text="I am $WHO_AM_I, public ip changed to $PUBLIC_IP"
        curl -X POST -H "Content-Type: application/json" -d '{"msg_type": "text", "content": {"text": "'"$text"'"}}' "$FEISHU_WEBHOOK"
        completed $? "send public_ip=$PUBLIC_IP to webhook"
    fi
}

function get_public_ip(){
    # if [ "$IPV4_OR_IPV6" = "ipv4"  ];then
    #     get_public_ipv4
    # else
    #     get_public_ipv6
    # fi
    cc-hostcli network get-public-ip
    completed $? "cc-hostcli network get-public-ip"
    PUBLIC_IP=$(crudini --get $AIO_CONF_PATH public_ip address)
    completed $? "read public_ip via crudini"
}

function check_public_changed(){
    read_public_ip
    get_public_ip
    if [ "$PUBLIC_IP" == "$PUBLIC_IP_READ_CONTENT" ]; then
        echo "public ip is $PUBLIC_IP not change"
    else
        echo "public ip change to $PUBLIC_IP"
        cc-hostcli service update-wireguard-service
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