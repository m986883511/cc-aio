#!/usr/bin/env bash
source /root/.bashrc
conda activate astute
kolla-ansible mariadb_backup -i /etc/cs/hosts -e mariadb_backup_host=$(hostnamectl hostname)
find /var/lib/docker/volumes/mariadb_backup/_data/ -maxdepth 1 -name "mysqlbackup-*" -mtime +10 -exec rm -rf {} \;
