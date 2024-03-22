#!/usr/bin/env bash
interface="vmbond"
check_interval=3
timeout=600
checks=0
while true; do
    if ip link show "$interface" >/dev/null 2>&1; then
        echo "Interface $interface exists."
        break
    fi

    checks=$((checks + 1))
    if (( checks * check_interval >= timeout )); then
        # Figure out via 'journalctl -xeu kolla-openvswitch_db-container.service'
        echo "Timeout: Interface $interface was not created within the specified duration."
        exit 1
    fi

    sleep "$check_interval"
done

ip_endswith=$(hostname | grep -oE '[0-9]+' | sed 's/^0*//')
vmbond_ip="192.222.22.${ip_endswith}/24"
real_ip=$(ip -o -4 addr show vmbond | awk '{print $4}')
if [[ ${vmbond_ip}x != ${real_ip}x ]];then
    ip addr flush vmbond
    ip addr add $vmbond_ip dev vmbond
else
    echo "IP config already ok"
fi
ip link set vmbond up
exit 0
