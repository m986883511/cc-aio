#!/bin/bash
WORK_DIR=$(cd $(dirname $0) && pwd)
cd $WORK_DIR
source ./utils.sh
LOG_DIR="/var/log/$AUTHOR_NAME"
mkdir -p $LOG_DIR
LOG_PATH="$LOG_DIR/aio.log"

function main(){
  startTime=$(current_time)
  echo "start-at "$startTime
  print_script_executed_path                  $@
  check_current_user_is_root                  $@
  copy_files_in_bin                           $@
  add_usr_local_to_PATH
  allow_install_python_package
  init_setup
  start_repo_server
  # write_etc_hosts
  create_local_file_repo
  install_base_apt_packages
  create_pip_conf localhost
  install_cc_aio
  echo "use command cc-aio to continue"
  echo    "start-at "$startTime
  echo -e "end-at   "$(current_time)"\n\n\n"
}

with_logs_piped $LOG_PATH main
