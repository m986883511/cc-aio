
YUM_REPO_DIR=/etc/yum.repos.d
YUM_REPO_BACKUP_DIR=/etc/yum.repos.d/bak
YUM_OFFLINE_REPO_NAME=local.repo
# REPO_SERVER_IP="0.0.0.0"
REPO_SERVER_PORT=7080
AUTHOR_NAME="cc"
OPT_AUTHOR_DIR="/opt/$AUTHOR_NAME"
REPO_SERVER_NAME="repo-server"
HOSTRPC_SERVER_NAME="$AUTHOR_NAME-hostrpc"
REPO_SERVER_SYSTEMD_FILE=/usr/lib/systemd/system/$REPO_SERVER_NAME.service
HOSTRPC_SERVER_SYSTEMD_FILE=/usr/lib/systemd/system/$HOSTRPC_SERVER_NAME.service
REPO_SERVER_DIR="$OPT_AUTHOR_DIR/$AUTHOR_NAME-aio-bin/repo"
YUM_PACKAGES_DIR_PREFIX="$REPO_SERVER_DIR/yum"
PIP_PACKAGES_DIR_PREFIX="$REPO_SERVER_DIR/pip"
# base packages
BASE_BASE_RPM="which tar wget systemd sshpass newt python3 rsync pciutils"
CEPH_BASE_RPM="podman lvm2 cephadm chrony ceph-common smartmontools jq gdisk $BASE_BASE_RPM"
OPENSTACK_BASE_RPM="docker python3-pip nfs-utils $BASE_BASE_RPM"
PVE_BASE_DEBS="samba samba-common python3-pip wireguard sshpass crudini git net-tools parted"
BASE_PIP_PACKAGES=""
INVENTORY_HOSTS_PATH="/etc/$AUTHOR_NAME/hosts"
# 
SYS_ARCH=$(uname -m)
SSH_TIMEOUT=2

# Colors
RED=''
GREEN=''
YELLOW=''
BLUE=''
PLAIN=''

JM_IP_PRIFIX="192.222.1."
JM_VERSION_DIR="$OPT_AUTHOR_DIR/jmversion"
AIO_CONF_NAME='aio.conf'
PVETUI_CONFIG_PATH="/etc/$AUTHOR_NAME/$AIO_CONF_NAME"
PVE_IP_ADDRESS=
CONDA_BIN_PATH="/root/miniconda3/condabin/conda"
LOG_PATH="/var/log/$AUTHOR_NAME/shell.log"


function echo_log() {
    echo "$*" >> /tmp/pvetui.log
}

function completed() {
    if [[ $1 -eq 0 ]]; then
        echo -e "${GREEN}$2 success${PLAIN}"
    else
        echo -e "${RED}$2 failed${PLAIN}"
        if [ $# -ge 3 ]; then
            echo -e "$3"
        fi
        exit 1
    fi
}

function echo_and_exit_when_failed() {
    if [[ $1 -ne 0 ]]; then
        echo -e "${RED}$2 failed${PLAIN}"
        if [ $# -ge 3 ]; then
            echo -e "$3"
        fi
        exit 1
    fi
}

function get_os_release_id() {
    local os_release_id=$(awk -F= '/^[iI][dD]=/{print tolower($2)}' /etc/os-release | sed "s/['\"]//g")
    echo $os_release_id
}

function start_repo_server() {
    command -v python3
    completed $? "check command python3 exist"

    PYTHON_BIN=$(command -v python3)
    if [ ! -f $REPO_SERVER_SYSTEMD_FILE ]; then
        cat > $REPO_SERVER_SYSTEMD_FILE << EOF
[Unit]
Description=Yum Repo Server
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root

WorkingDirectory=${REPO_SERVER_DIR}
ExecStart=${PYTHON_BIN} -m http.server ${REPO_SERVER_PORT}
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF
    fi

    systemctl enable $REPO_SERVER_NAME.service --now
    local repo_server_status=`systemctl is-active $REPO_SERVER_NAME.service`
    if [ $repo_server_status = active ]; then
        completed 0 "start $REPO_SERVER_NAME"
    else
        sleep 5s
        repo_server_status=`systemctl is-active $REPO_SERVER_NAME.service`
        if [ $repo_server_status != active ]; then
            completed 1 "start $REPO_SERVER_NAME"
        fi
    fi
}

function blacklist_driver(){
    cat > /etc/modprobe.d/pve-blacklist.conf << EOF
blacklist nvidiafb
blacklist nvidia
blacklist radeon
blacklist amdgpu
blacklist i915
blacklist nouveau
blacklist snd_hda_intel
options vfio_iommu_type1 allow_unsafe_interrupts=1
EOF
}

function set_and_update_grub(){
    crudini --set /etc/default/grub "" GRUB_CMDLINE_LINUX_DEFAULT "\"quiet initcall_blacklist=sysfb_init\""
    completed $? "open grub initcall_blacklist"
    update-grub
    completed $? "update-grub"
    update-initramfs -u -k all
    completed $? "update-initramfs -u -k all"
}


function delete_local_lvm_storage(){
    local content
    content=$(pvesh get /storage)
    completed $? "pvesh get /storage"
    if echo "$content" | grep -q "local-lvm"; then
        pvesh delete /storage/local-lvm
        completed $? "delete local-lv storage"
    else
        echo "no need delete local-lvm"
    fi
    pvesh set /storage/local --content rootdir,vztmpl,backup,snippets,images,iso
    completed $? "set local storage content"
    pvesh get /storage/local
    completed $? "get local storage content"
    content=$(lvs)
    completed $? "lvs"
    if echo "$content" | grep -q "data pve"; then
        lvremove pve/data -y
        completed $? "delete lv pve/data"
    else
        echo "no need delete pve/data"
    fi
    lvextend -l +100%FREE -r pve/root
    completed $? "lvextend pve/root"
}


function start_hostrpc_server() {
    echo_log "enter function name: ${FUNCNAME[0]}"
    command -v cc-hostrpc
    completed $? "check command hostrpc exist"

    if [ ! -f $HOSTRPC_SERVER_SYSTEMD_FILE ]; then
        cat > $HOSTRPC_SERVER_SYSTEMD_FILE << EOF
[Unit]
Description=cs hostrpc
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root

WorkingDirectory=/root
ExecStart=cc-hostrpc
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF
    fi

    systemctl enable $HOSTRPC_SERVER_NAME.service --now
    local repo_server_status=`systemctl is-active $HOSTRPC_SERVER_NAME.service`
    if [ $repo_server_status = active ]; then
        completed 0 "start $HOSTRPC_SERVER_NAME"
    else
        sleep 5s
        repo_server_status=`systemctl is-active $HOSTRPC_SERVER_NAME.service`
        if [ $repo_server_status != active ]; then
            completed 1 "start $HOSTRPC_SERVER_NAME"
        fi
    fi
    systemctl restart $HOSTRPC_SERVER_NAME
    completed $? "restart $HOSTRPC_SERVER_NAME"
}

function check_network_connection(){
    local host_or_ip=$1
    ping -t 1 -c 1 $host_or_ip
}

function check_ssh_passwordless(){
    local host_or_ip=$1
    local SSH_PRIVATE_KEY_PATH=$(python -c "from hostadmin.files import FilesDir; print(FilesDir.SSH.id_rsa)")
    ssh -o PreferredAuthentications=publickey -o ConnectTimeout=$SSH_TIMEOUT -i $SSH_PRIVATE_KEY_PATH root@$host_or_ip /bin/true
}

function set_ssh_passwordless(){
    local host_or_ip=$1
    local root_password=$2
    local SSH_PUBLIC_KEY_PATH=$(python -c "from hostadmin.files import FilesDir; print(FilesDir.SSH.id_rsa_pub)")
    sshpass -p $root_password ssh-copy-id -i $SSH_PUBLIC_KEY_PATH root@$host_or_ip
    completed $? "set ssh passwordless"
}

function install_ceph_base_env() {
    local base_rpm=$CEPH_BASE_RPM
    yum install -y $base_rpm
    completed $? "install ceph base packages"
}

function install_pve_base_env() {
    local base_debs=$PVE_BASE_DEBS
    apt install -y $base_debs
    completed $? "install pve base packages"
}

function scp_dir_to_remote_host(){
    local host_or_ip=$1
    local src_dir=$2
    local dst_dir=$3
    local SSH_PRIVATE_KEY_PATH=$(python -c "from hostadmin.files import FilesDir; print(FilesDir.SSH.id_rsa)")
    scp -o StrictHostKeyChecking=no -i $SSH_PRIVATE_KEY_PATH -r $src_dir root@$host_or_ip:$dst_dir
    completed $? "scp $src_dir root@$host_or_ip:$dst_dir"
}

function scp_remote_host_dir_to_current_host(){
    local host_or_ip=$1
    local src_dir=$2
    local dst_dir=$3
    local SSH_PRIVATE_KEY_PATH=$(python -c "from hostadmin.files import FilesDir; print(FilesDir.SSH.id_rsa)")
    scp -o StrictHostKeyChecking=no -i $SSH_PRIVATE_KEY_PATH -r root@$host_or_ip:$src_dir $dst_dir
    completed $? "scp root@$host_or_ip:$src_dir $dst_dir"
}

function install_openstack_base_env() {
    local base_rpm=$OPENSTACK_BASE_RPM
    local release_id=$(get_os_release_id)
    if [ $release_id = 'rocky' ]; then
        base_rpm=$(echo "$base_rpm" | sed 's/docker/docker-ce/')
        base_rpm="$base_rpm nmap"
    fi
    yum install -y $base_rpm
    mkdir -p ~/.docker
    # NOTE(chengml): With this, we can use 'ctrl-p' in container 
    # to get previous command in shell
    cat > ~/.docker/config.json <<EOF
{
    "detachkeys": "ctrl-q,ctrl-q"
}
EOF
    completed $? "install openstack base packages"
}

function change_ssh_strict_host_no() {
    echo_log "enter function name: ${FUNCNAME[0]}"
    sed -i '/StrictHostKeyChecking/d' /etc/ssh/ssh_config
    echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
    completed $? "change ssh StrictHostKeyCheckin no"
}

function get_cpu_arch() {
  if [ $SYS_ARCH = "aarch64" ]; then
    echo "arm64"
  elif [ $SYS_ARCH = "x86_64" ]; then
    echo "amd64"
  else
    echo "Unsupported architecture"
    exit 1
  fi
}

function number_to_hostname(){
    local number=$1
    local formatted_number=$(printf "host%03d" "$number")
    echo $formatted_number
}

function ip_to_hostname(){
    local ip_address=$1
    if [ "$ip_address" = localhost ]; then

        ip_address=$PVE_IP_ADDRESS
    fi
    local last_octet=$(echo "$ip_address" | awk -F'.' '{print $NF}')
    echo $(number_to_hostname $last_octet)
}

function write_etc_hosts(){
    local hosts_file="/etc/hosts"
    for i in {1..200}; do
        ip_prifix=$(echo "$PVE_IP_ADDRESS" | awk -F. '{print $1"."$2"."$3"."}')
        if [ -z "$ip_prifix" ]; then
            completed 1 "get ip_prifix"
        fi
        ip="${ip_prifix}${i}"
        host="host$(printf "%03d" $i)"
        if grep -q -E "($ip|$host)\s" "$hosts_file"; then
            /bin/true
        else
            echo_log "write: $ip $host to /etc/hosts"
            echo "$ip $host" >> "$hosts_file"
        fi
    done
}

function install_base_python_packages(){
    if [ -z $BASE_PIP_PACKAGES ];then
        echo "no need install base_python_package"
    else
        pip3 install $BASE_PIP_PACKAGES
        completed $? "pip3 install $BASE_PIP_PACKAGES"
    fi
}

function get_pve_ip(){
    PVE_IP_ADDRESS=$(grep -w "$(hostname)" /etc/hosts | awk '{print $1}')
    if [ -z "$PVE_IP_ADDRESS" ]; then
        completed 1 "get PVE_IP_ADDRESS"
    fi
}

function check_kolla_ansible_version_exist(){
    local file=$(ls $JM_VERSION_DIR|grep "kolla-deploy-.*-$(uname -m).bin")
    if [ -z "$file" ]; then
        completed 1 "not found kolla-deploy version in $JM_VERSION_DIR"
    fi
}

function get_kolla_ansible_version_path(){
    check_kolla_ansible_version_exist
    local file_pattern="$JM_VERSION_DIR/kolla-deploy-*-$(uname -m).bin"
    local max_number=0
    local max_file=""

    for file in $file_pattern; do
        number=$(python3 -c "import re;s='$file';m=re.split(r'[-.]', s);a='$(uname -m)';i=m.index(a);print(m[i-1])")
        echo_and_exit_when_failed $? "calc build number of $file"
        if [ "$number" -gt "$max_number" ]; then
            max_number=$number
            max_file=$file
        fi
    done
    if [ -n "$max_file" ]; then
        echo "$max_file"
    else
        echo "not found kolla-deploy version in $JM_VERSION_DIR" 
        return 1
    fi
}

function start_docker_service(){
    systemctl start docker
    systemctl enable docker
    sleep 3
    systemctl is-active docker
    completed $? "start docker service"
}

function check_kolla_registry_version_exist(){
    local file=$(ls $JM_VERSION_DIR|grep "kolla-registry-.*-$(uname -m).*.tar")
    if [ -z "$file" ]; then
        completed 1 "not found kolla-registry version in $JM_VERSION_DIR"
    fi
}

function get_kolla_registry_version_path(){
    check_kolla_registry_version_exist
    local file_pattern="$JM_VERSION_DIR/kolla-registry-*-$(uname -m).*.tar"
    local max_number=0
    local max_file=""

    for file in $file_pattern; do
        number=$(python3 -c "import re;s='$file';m=re.split(r'[-.]', s);a='$(uname -m)';i=m.index(a);print(m[i-1])")
        echo_and_exit_when_failed $? "calc build number of $file"
        if [ "$number" -gt "$max_number" ]; then
            max_number=$number
            max_file=$file
        fi
    done
    if [ -n "$max_file" ]; then
        echo "$max_file"
    else
        echo "not found kolla-registry version in $JM_VERSION_DIR"
        return 1
    fi
}

function with_logs_piped() {
  local logfile=$1; shift
  "$@" > >(tee -a -- "$logfile") 2>&1
}

function install_kolla_deploy_version(){
    local already_installed=''
    if [ -f $CONDA_BIN_PATH ]; then
        $CONDA_BIN_PATH --version
        if [ $? == 0 ]; then
            $CONDA_BIN_PATH env list |grep ^cs
            if [ $? == 0 ]; then
                echo_log "kolla-deploy package is already installed"
                already_installed=1
            fi
        fi
    fi
    if [ -z "$already_installed" ]; then
        local path=$(get_kolla_ansible_version_path)
        echo_log "will install kolla-deploy version use $path"
        bash $path
        completed $? "install kolla-deploy version use $path"
    fi
}

function install_kolla_registry_version(){
    local already_installed=''
    echo_log "enter function name: ${FUNCNAME[0]}"
    docker images | grep 'kolla-registry'
    if [ $? == 0 ]; then
        echo_log "kolla-registry package is already installed"
        already_installed=1
    fi
    if [ -z "$already_installed" ]; then
        local path=$(get_kolla_registry_version_path)
        local conda_env_name="cc"
        source ~/.bashrc
        completed $? "source ~/.bashrc"
        eval "$(conda shell.bash hook)"
        completed $? "conda shell.bash hook"
        conda activate "$conda_env_name"
        completed $? "activate conda $conda_env_name env"
        kolla-import-registry $path
        completed $? "kolla-import-registry $path"
    fi
}

function execute_kolla_init(){
    local conda_env_name="cc"
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    conda activate "$conda_env_name"
    completed $? "activate conda $conda_env_name env"
    kolla-init
    completed $? "kolla-init"
}

function execute_kolla_generate(){
    local conda_env_name="cc"
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    conda activate "$conda_env_name"
    completed $? "activate conda $conda_env_name env"
    kolla-generate
    completed $? "kolla-generate"
}

function execute_kolla_deploy(){
    local conda_env_name="cc"
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    conda activate "$conda_env_name"
    completed $? "activate conda $conda_env_name env"
    kolla-deploy
    completed $? "kolla-deploy"
}

function execute_kolla_add_nodes(){
    local conda_env_name="cc"
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    conda activate "$conda_env_name"
    completed $? "activate conda $conda_env_name env"
    kolla-add-nodes $1
    completed $? "kolla-add-nodes"
}

function gen_openstack_ceph_config(){
    echo "enter function name: ${FUNCNAME[0]}"
    local conda_env_name="cc"
    local ceph_admin_node=$1
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    conda activate "$conda_env_name"
    completed $? "activate conda $conda_env_name env"
    kolla-generate
    completed $? "kolla-generate for ceph"
    kolla-ansible genconfig -i $INVENTORY_HOSTS_PATH --tags glance,cinder,nova
    completed $? "genconfig for glance,cinder,nova"
}

function wait_current_node_install_ceph_completed(){
    local start_time=$(date +%s)
    local end_time=$((start_time + 120))  # 设置2分钟的结束时间
    while true; do
        # 执行需要重试的指令
        hostcli ceph ceph-orch-ps-current-node
        if [ $? -eq 0 ]; then
            echo "install ceph completed "
            break  # 如果指令成功执行，跳出循环
        fi
        current_time=$(date +%s)
        if [ $current_time -ge $end_time ]; then
            echo "Command execution failed within 2 minutes."
            # break  # 如果超过2分钟，跳出循环
            completed 1 "wait install ceph failed with timeout"
        fi
        echo "Command execution failed. Retrying in 5 seconds..."
        sleep 5  # 休眠5秒钟
    done
}

function create_rbd_volume_type(){
    echo "enter function name: ${FUNCNAME[0]}"
    source ~/.bashrc
    completed $? "source ~/.bashrc"
    eval "$(conda shell.bash hook)"
    completed $? "conda shell.bash hook"
    source /etc/$AUTHOR_NAME/admin-openrc.sh
    completed $? "source /etc/$AUTHOR_NAME/admin-openrc.sh"

    volume_type_list=$(openstack volume type list -f value -c Name)
    completed $? "get volume_type_list"
    if [[ $volume_type_list == *rbd* ]]; then
        echo "already create rbd voluem type"
    else
        openstack volume type create rbd
        completed $? "create voluem type rbd"
        openstack volume type set rbd --property volume_backend_name=rbd-1 --property image_service:store_id=cinder
        completed $? "exec: openstack volume type set rbd --property volume_backend_name=rbd-1 --property image_service:store_id=cinder"
    fi
    docker_mysql_cmd=$(crudini --get /etc/$AUTHOR_NAME/admin-openrc.sh "" "alias mysql")
    completed $? "crudini get mysql alias"
    docker_mysql_cmd=${docker_mysql_cmd//\"/}
    completed $? "get true mysql cmd"
    $docker_mysql_cmd cinder -e "update volume_types set is_public=0 where name='__DEFAULT__'"
    completed $? "update __DEFAULT__ is_public to 0"
    volume_type_list=$(openstack volume type list -f value -c Name)
    completed $? "get volume_type_list"
}

function restart_ceph_about_container(){
    echo "enter function name: ${FUNCNAME[0]}"
    local control_nodes
    local pure_compute_nodes
    control_nodes=$(crudini --get $PVETUI_CONFIG_PATH openstack control_nodes)
    completed $? "read openstack control_nodes"
    pure_compute_nodes=$(crudini --get $PVETUI_CONFIG_PATH openstack pure_compute_nodes)
    completed $? "read openstack pure_compute_nodes"

    control_nodes="${control_nodes//,/ }"
    for node in $control_nodes; do
        echo "restart $node"
        hostcli ssh ssh-run-on-remote $node "cc-hostcli ceph restart-ceph-about-container"
        completed $? "restart $node ceph about container"
    done
    completed 0 "restart all control_nodes"
    pure_compute_nodes="${pure_compute_nodes//,/ }"
    for node in $pure_compute_nodes; do
        echo "restart $node"
        hostcli ssh ssh-run-on-remote $node "cc-hostcli ceph restart-ceph-about-container"
        completed $? "restart $node ceph about container"
    done
    completed 0 "restart all pure_compute_nodes"
}

function create_yum_repo(){
    # $YUM_PACKAGES_DIR_PREFIX
    local release_id=$(get_os_release_id)
    local default_path=$YUM_PACKAGES_DIR_PREFIX/$release_id
    local local_path="${1:-$default_path}"
    command -v createrepo
    completed $? "check command createrepo exist"
    cp_cephadm_rpm_to_repo
    createrepo -pdo $local_path $local_path
    completed $? "createrepo to $local_path"
}

function create_pip_conf(){
    echo_log "enter function name: ${FUNCNAME[0]}"
    local server_ip=$1
    mkdir -p /root/.config/pip/
    cat > /root/.config/pip/pip.conf <<EOF
[global]
index-url = http://$1:$REPO_SERVER_PORT/pip/simple
[install]
trusted-host = $1
EOF
    completed $? "create_pip_conf to $(hostname)"
}

if [[ "$0" == "$BASH_SOURCE" ]]; then
    echo_log "*************************************************"
    echo_log "*************************************************"
    echo "run as bash"
else
    echo_log "================================================="
    echo_log "================================================="
    echo "run as source"
    RUN_AS_SOURCE_FLAG=1
fi
