#!/bin/bash
. /etc/profile
. ~/.bashrc
AUTHOR_NAME="cc"
WHO_AM_I="$(hostname)"
RUN_AS_SOURCE_FLAG=
PUBLIC_IP=""
PUBLIC_IP_READ_CONTENT=""
CURRENT_SCRIPT_DIR=
CURRENT_SCRIPT_NAME=
CURRENT_SCRIPT_PATH=
DEST_SCRIPT_DIR="/usr/local/bin"
DEST_SCRIPT_NAME="set-dns.sh"
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

DNS1=$(crudini --get $AIO_CONF_PATH network dns1)
completed $? 'read network dns1'
DNS2=$(crudini --get $AIO_CONF_PATH network dns2)
completed $? 'read network dns2'
DNS3=$(crudini --get $AIO_CONF_PATH network dns3)
completed $? 'read network dns3'

function set_crontab(){
    echo "enter function name: ${FUNCNAME[0]}"
    if crontab -l|grep -qF $DEST_SCRIPT_NAME; then
        echo "no need add $DEST_SCRIPT_NAME to crontab"
    else
        echo "add $DEST_SCRIPT_NAME to crontab"
        crontab -l > setdns
        #echo new cron into cron file
        echo "@reboot sleep 10 && $DEST_SCRIPT_PATH" >> setdns
        #install new cron file
        crontab setdns
        completed $? "add $DEST_SCRIPT_NAME to crontab"
        rm setdns
    fi
}

function run_directly(){
    start_log
    echo "enter function name: ${FUNCNAME[0]}"
    echo "Script is being run directly, $CURRENT_SCRIPT_PATH run at $(date)"
    pvesh set /nodes/localhost/dns --search localdomain --dns1 $DNS1 --dns2 $DNS2 --dns3 $DNS3
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