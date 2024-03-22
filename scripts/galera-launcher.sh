#!/usr/bin/env bash

# DO MARIADB RECOVERY WITH CONDITIONS:
# 1. Current node hold management vip(kolla_internal_vip_address)
# 2. All control nodes are up(up for >= 5min)
# 3. All mariadb container are down

LOG_FILE=/var/log/kolla/mariadb/galera-launcher.log
HOSTS_FILE=/etc/cs/hosts

function check_to_recover() {
    # Check if we hold the management vip
    mgt_vip=$(grep ^mgt_vip /etc/cs/pvetui.conf | awk -F'=' '{print $2}' | xargs)
    if [ -z $mgt_vip ];then
        echo "Can get management vip"
        exit -1
    fi
    if ! hostname -I | grep -w $mgt_vip &>/dev/null;then
        echo "May not hold management vip on current node"
        exit 0
    fi
    
    # Check if all control nodes are up
    up_host_out=$(ansible -i $HOSTS_FILE control -m shell -a "awk '{print int(\$1/60) \" min\"} ' /proc/uptime" 2>/dev/null | awk '{print $1}')
    for x in $up_host_out;do
        if [[ $x -ge 5 ]];then
            ((up_host_num++))
        fi
    done
    if [ $up_host_num -lt 3 ];then
        echo "May not all control nodes are up"
        exit 0
    fi
    
    # Check if all mariadb containers are down
    up_db_out=$(ansible -i $HOSTS_FILE control -m shell -a "docker inspect --format='{{ '{{' }} .State.Status {{ '}}' }}' mariadb" 2>/dev/null | grep running)
    up_db_num=$(echo $up_db_out | wc -l)
    if [[ $up_db_num -ne 0 ]];then
        echo "Not all mariadb containers are down"
        exit 0
    else
        echo "All mariadb containers are down"
        echo "Try to recover with 'kolla-ansible mariadb_recovery' .."
        kolla-ansible mariadb_recovery -i $HOSTS_FILE
    fi
}

date +'%F %T: Start to check and recover galera cluster ..' | tee -a $LOG_FILE
check_to_recover | tee -a $LOG_FILE
date +'%F %T: Check and recover finished.' | tee -a $LOG_FILE
