#!/bin/bash
APT_REPO_DIR=/etc/apt/sources.list.d
APT_REPO_BACKUP_DIR=/etc/apt/sources.list.d/bak
REPO_SERVER_IP="localhost"
REPO_SERVER_PORT=7080
AUTHOR_NAME="cc"
OPT_AUTHOR_DIR="/opt/$AUTHOR_NAME"
REPO_SERVER_NAME="repo-server"
if [ -z "$PROJECT_NAME" ];then
    PROJECT_NAME="$AUTHOR_NAME-aio"
fi
REPO_SERVER_SYSTEMD_FILE=/usr/lib/systemd/system/$REPO_SERVER_NAME.service
PROJECT_INSTALL_PATH="$OPT_AUTHOR_DIR/$PROJECT_NAME"
REPO_SERVER_DIR="$OPT_AUTHOR_DIR/$PROJECT_NAME/repo"
PIP_PACKAGES_DIR_PREFIX="$REPO_SERVER_DIR/pip"
APT_PACKAGES_DIR_PREFIX="$REPO_SERVER_DIR/apt"
SYS_ARCH=$(uname -m)
SSH_TIMEOUT=2
CS_VERSION_DIR="$OPT_AUTHOR_DIR/version"
MY_ALIST_ADDRESS="http://192.168.1.4:5244"
ALIST_HDD_PATH="/host004/ata-WDC_WD40EJRX-89AKWY0_WD-WX72D71J52XA"
PVE_IP_ADDRESS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
PLAIN='\033[0m'

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

function check_current_user_is_root() {
  echo "enter function name: ${FUNCNAME[0]}"
  current_user=$(whoami)
  if [ $current_user != "root" ]; then
    echo "ERROR: please run as root"
    exit 1
  fi
}

function copy_files_in_bin() {
  echo "enter function name: ${FUNCNAME[0]}"
  if [ -d $PROJECT_INSTALL_PATH ]; then
    if [ "$WORK_DIR" != "$PROJECT_INSTALL_PATH" ]; then
      echo -e "\t rm -rf old dir $PROJECT_INSTALL_PATH"
      rm -rf $PROJECT_INSTALL_PATH
      completed $? "delete old dir $PROJECT_INSTALL_PATH"
      mkdir -p $PROJECT_INSTALL_PATH
      completed $? "create new dir $PROJECT_INSTALL_PATH"
      /bin/cp -r * $PROJECT_INSTALL_PATH
      completed $? "copy files to $PROJECT_INSTALL_PATH"
    fi
  else
    mkdir -p $PROJECT_INSTALL_PATH
    completed $? "create new dir $PROJECT_INSTALL_PATH"
    /bin/cp -r * $PROJECT_INSTALL_PATH
    completed $? "copy files to $PROJECT_INSTALL_PATH"
  fi
}

function get_cpu_arch() {
  if [ $(uname -m) = "aarch64" ]; then
    echo "arm64"
  elif [ $(uname -m) = "x86_64" ]; then
    echo "amd64"
  else
    echo "Unsupported architecture"
    exit 1
  fi
}

function current_time() {
  echo "$(TZ=UTC-8 date +%Y-%m-%d' '%H:%M:%S)"
}

function with_logs_piped() {
  local logfile=$1; shift
  "$@" > >(tee -a -- "$logfile") 2>&1
}

function get_os_release_id() {
    local os_release_id=$(awk -F= '/^[iI][dD]=/{print tolower($2)}' /etc/os-release | sed "s/['\"]//g")
    echo $os_release_id
}

function install_cc_aio(){
  pip3 install pbr
  completed $? "install pbr"
  pip3 uninstall cc-aio -y
  pip3 install --use-deprecated=legacy-resolver cc-aio
  completed $? "install cc-aio"
}

function allow_install_python_package(){
    local manage_path
    manage_path=$(find /usr/lib/ -name EXTERNALLY-MANAGED*)
    if [ -z "$manage_path" ]; then
        completed 0 "already delete EXTERNALLY-MANAGED"
    else
        rm -f $manage_path
        completed 0 "delete $manage_path"
    fi
}

function init_setup(){
    echo "enter function name: ${FUNCNAME[0]}"
    change_ssh_strict_host_no
    mkdir -p $CS_VERSION_DIR
    completed $? "create $CS_VERSION_DIR ok dir"
}

function change_ssh_strict_host_no() {
    echo "enter function name: ${FUNCNAME[0]}"
    sed -i '/StrictHostKeyChecking/d' /etc/ssh/ssh_config
    echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
    completed $? "change ssh StrictHostKeyCheckin no"
}

function print_script_executed_path() {
  echo "enter function name: ${FUNCNAME[0]}"
  local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local SCRIPT_NAME="$(basename "$0")"
  script_executed_path=$SCRIPT_DIR/$SCRIPT_NAME
  echo "executed script path is $script_executed_path"
  echo "executed script work dir is $(pwd)"
}


function add_usr_local_to_PATH(){
    local m_path="/usr/local/bin"
    if ! echo "$PATH" | grep -q "$m_path" ; then
        export PATH="$m_path:$PATH"
    fi
    local m_path="/usr/local/sbin"
    if ! echo "$PATH" | grep -q "$m_path" ; then
        export PATH="$m_path:$PATH"
    fi
}

function start_repo_server() {
    command -v python3
    completed $? "check command python3 exist"

    PYTHON_BIN=$(command -v python3)
    if [ ! -f $REPO_SERVER_SYSTEMD_FILE ]; then
        cat > $REPO_SERVER_SYSTEMD_FILE << EOF
[Unit]
Description=Repo Server
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root

WorkingDirectory=${REPO_SERVER_DIR}
ExecStart=${PYTHON_BIN} -m http.server -b localhost ${REPO_SERVER_PORT}
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

set_dir_and_parent_dirs_permissions() {
    local directory=$1
    chmod 777 "$directory"
    echo "chmod 777 "$directory""

    shang=$(dirname $directory)
    if [ "$shang" != "/" ]; then
        set_dir_and_parent_dirs_permissions "$shang"
    fi
}

function install_base_apt_packages(){
    apt install python3-pip -y
    completed $? "install python3-pip deb"
    apt install crudini -y
    completed $? "install crudini deb"
    apt install sshpass -y
    completed $? "install sshpass deb"
}

function create_local_file_repo(){
    local pve_release
    local pve_version_output
    local release_id=$(get_os_release_id)
    mkdir -p $APT_REPO_BACKUP_DIR
    mv $APT_REPO_DIR/*.list $APT_REPO_BACKUP_DIR
    pve_version_output=$(pvesh get version --output-format json)
    completed $? "get pve version"
    pve_release=$(python3 -c "import json;mm=json.loads('$pve_version_output');print(mm['release'])")
    completed $? "calc pve version"
    local local_apt_source_path=$APT_PACKAGES_DIR_PREFIX/$pve_release
    if [ -d $local_apt_source_path ];then
        completed 0 "current pve version is $pve_release, check local apt source path exist"
    else
        local support_version=$(ls $APT_PACKAGES_DIR_PREFIX)
        echo "support pve version is $support_version" 
        completed 1 "current pve version is $pve_release, check support pve version"
    fi
    cat > /etc/apt/sources.list <<EOF
deb [trusted=yes] file://$APT_PACKAGES_DIR_PREFIX/$pve_release ./
EOF
    completed $? "create local apt repo file"
    chmod -R 777 $APT_PACKAGES_DIR_PREFIX
    completed $? "chmod 777 debs"
    set_dir_and_parent_dirs_permissions $APT_PACKAGES_DIR_PREFIX
    completed $? "set_dir_and_parent_dirs_permissions $APT_PACKAGES_DIR_PREFIX"
    apt update
    completed $? "apt update"
}

function get_pve_ip(){
    PVE_IP_ADDRESS=$(grep -w "$(hostname)" /etc/hosts | awk '{print $1}')
    if [ -z "$PVE_IP_ADDRESS" ]; then
        completed 1 "get PVE_IP_ADDRESS"
    fi
}

function write_etc_hosts(){
    local hosts_file="/etc/hosts"
    local ip_prifix=""
    get_pve_ip
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
            echo "write: $ip $host to /etc/hosts"
            echo "$ip $host" >> "$hosts_file"
        fi
    done
}

function generate_changelog() {
  echo "enter function name: ${FUNCNAME[0]}"
  local est_path=$1
  git log --pretty=format:"%h %ad %an %s" --date=short -30 > doc/ChangeLog
  completed $? "generate ChangeLog"
#   openssl enc -aes-256-cbc -salt -in ChangeLog -out $est_path -pass pass:password -md sha256
#   completed $? "enc Changelog"
}

function check_if_ssh_is_passwordless() {
  echo "enter function name: ${FUNCNAME[0]}"
  echo "begin check ssh passwordless"
  local terminal=$1
  ssh -o PasswordAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=3 $terminal /bin/true
  completed $? "check passwordless ssh to $terminal"
}

function create_pip_conf(){
    echo "enter function name: ${FUNCNAME[0]}"
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
    echo "*************************************************"
    echo "*************************************************"
    echo "run as bash"
else
    echo "================================================="
    echo "================================================="
    echo "run as source"
    RUN_AS_SOURCE_FLAG=1
fi
