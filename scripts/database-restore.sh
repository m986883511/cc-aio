#!/usr/bin/env bash

LOG_FILE=/var/log/kolla/mariadb/database-restore.log
HOSTS_FILE=/etc/cs/hosts
MARIADB_IMAGE_FULL=astute-tec.com:4000/astute/mariadb-server:zed

if [ $# -eq 1 ]; then
    back_file=$1
    if [ -e $back_file ]; then
        echo "recover db use $back_file"
    else
        echo "$back_file is not exist!"
        exit -1
    fi
else
    echo "Usage: database-restore.sh /path/to/database_backup_file"
    echo "       Find all available backup files which start with 'mysqlbackup-' "
    echo "       in '/var/lib/docker/volumes/mariadb_backup/_data/'."
    exit -1
fi

function restore() {
    local tmp_script=$(mktemp)
    local base_back_file=$(basename $back_file)
    local mariadb_ownership=$(stat -c "%u:%g" $back_file)
    cat >> $tmp_script <<EOF
#!/usr/bin/env bash
rm -rf /backup/restore
mkdir -p /backup/restore/full
if [ ! -f /backup/$base_back_file ];then
    echo "/backup/$base_back_file not found in volume 'mariadb_backup'."
    exit -1
fi
gunzip -c /backup/$base_back_file | mbstream -x -C /backup/restore/full/
echo "mariabackup --prepare ..."
mariabackup --prepare --target-dir /backup/restore/full
rm -rf /var/lib/mysql/* /var/lib/mysql/\.[^\.]*
echo "mariabackup --copy-back ..."
mariabackup --copy-back --target-dir /backup/restore/full
EOF

    chmod +x $tmp_script
    source /root/.bashrc
    conda activate astute
    kolla-ansible -i $HOSTS_FILE stop -t mariadb --yes-i-really-really-mean-it
    chown $mariadb_ownership $tmp_script
    docker run --rm -it --volumes-from mariadb --name dbrestore --volume mariadb_backup:/backup --volume $tmp_script:/backup/restore.sh $MARIADB_IMAGE_FULL /backup/restore.sh
    if [ ! $? -eq 0 ];then
        echo "Failed to prepare mariadb backup data."
        exit -1
    fi
    kolla-ansible -i $HOSTS_FILE mariadb_recovery -e mariadb_recover_inventory_name=$(hostnamectl hostname)
}

date +'%F %T: Start to restore from mariadb backup data: $back_file ..' | tee -a $LOG_FILE
restore | tee -a $LOG_FILE
date +'%F %T: Restore finished.' | tee -a $LOG_FILE
