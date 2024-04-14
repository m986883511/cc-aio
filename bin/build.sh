#!/bin/bash
WORK_DIR=$(cd $(dirname $0) && pwd)
cd $WORK_DIR
source ./utils.sh

# Colors
RED=''
GREEN=''
YELLOW=''
BLUE=''
PLAIN=''
LOG_PATH="/var/log/$PROJECT_NAME.log"
AUTHOR_ZH_NAME="B站UP主吵吵博士"
GIFT_DIR_NAME="${AUTHOR_ZH_NAME}的赠礼"

function make_bin() {
  echo "enter function name: ${FUNCNAME[0]}"
  rm -rf $PROJECT_NAME-*.bin
  [ -z $BUILD_NUMBER ] && BUILD_NUMBER=0
  [ -z $GIT_BRANCH ] && GIT_BRANCH="null"

  # master or bugfix
  if [[ "$GIT_BRANCH" =~ "master" ]];then
     BRANCH_FLAG=999
  else
     BRANCH_FLAG=${GIT_BRANCH##*.}
  fi
  
  if [ -z $BUILD_NUMBER ];then BUILD_NUMBER=0; fi
  BIG_NUMBER="1"
  SMALL_NUMBER=$BRANCH_FLAG
  PBR_VERSION=$BIG_NUMBER.$SMALL_NUMBER.$BUILD_NUMBER
  export PBR_VERSION

  chmod +x $MAKE_SELF_DIR/makeself.sh
  $MAKE_SELF_DIR/makeself.sh --gzip $CACHE_DIR $PROJECT_NAME-$PBR_VERSION.bin $PROJECT_NAME ./install.sh
  completed $? "make $PROJECT_NAME bin"
}

function start_log(){
    printf '#%.0s' {1..50}
    echo -e '\n'
}

function make_apt_source(){
    mkdir -p $APT_REPO_DIR
    python3 download_alist_dir.py $MY_ALIST_ADDRESS/4t/fileserver/debian/archives deb.txt $APT_REPO_DIR
    docker rm -f build_apt_sources
    docker run -d --name build_apt_sources -v $APT_REPO_DIR:/tmp/apt -w /tmp/apt debian:dpkg-dev sleep 1d
    docker exec build_apt_sources bash /generate_apt_source.sh
    completed $? "make apt source"
}

function download_cc_aio(){
    python3 download_alist.py $MY_ALIST_ADDRESS/4t/fileserver/jenkins/production-pve/cc-aio/master/latest -s cc-aio -e tar.gz -p $PIP_REPO_DIR
    completed $? "download cc-aio package"
}

function make_pip_source(){
    mkdir -p $PIP_REPO_DIR
    python3 download_alist_dir.py $MY_ALIST_ADDRESS/4t/fileserver/pypi pypi.txt $PIP_REPO_DIR
    download_cc_aio
    docker run --rm --privileged -v $PIP_REPO_DIR:/pypi -w /pypi create-source dir2pi .
    completed $? "make pip source"
}


function download_files(){
    mkdir -p $OTHER_FILES_DIR
    python3 download_alist.py $MY_ALIST_ADDRESS/4t/soft/linux/alist -s alist-linux-musl-amd64.tar.gz -p $OTHER_FILES_DIR
    completed $? "download alist tar.gz"
}

function download_cc_gift(){
    mkdir -p $CHAOGE_GIFT_DIR
    python3 download_alist.py $MY_ALIST_ADDRESS/4t/work/cc-aio/$GIFT_DIR_NAME -p $CHAOGE_GIFT_DIR
    completed $? "download cc-aio gift"
}

function download_bin(){
    mkdir -p $REPO_BIN_DIR
    python3 download_alist.py $MY_ALIST_ADDRESS/4t/work/cc-aio/bin -p $REPO_BIN_DIR
    completed $? "download cc-aio bin"
}

function download_rom(){
    mkdir -p $REPO_ROM_DIR
    python3 download_alist.py $MY_ALIST_ADDRESS/4t/work/cc-aio/rom -p $REPO_ROM_DIR
    completed $? "download cc-aio rom"
}

function run_directly(){
  start_log
  startTime=$(current_time)
  echo "start-at "$startTime
  print_script_executed_path          $@
  cp ./install.sh $CACHE_DIR
  cp ./utils.sh $CACHE_DIR
  cp -r doc $CACHE_DIR
  make_apt_source
  make_pip_source
  download_files
  download_bin
  download_rom
  download_cc_gift
  make_bin                            $@
  echo    "start-at "$startTime
  echo -e "end-at   "$(current_time)"\n\n\n"
}

function run_as_source(){
    start_log
    echo "enter function name: ${FUNCNAME[0]}"
    echo "Script is being sourced, $CURRENT_SCRIPT_PATH run at $(date)"
    echo "not run any func"
}

function setup_work_dir(){
  echo "CURRENT_SCRIPT_PATH is $CURRENT_SCRIPT_PATH"
  CACHE_DIR="$CURRENT_SCRIPT_DIR/.cache"
  MAKE_SELF_DIR=$CURRENT_SCRIPT_DIR/makeself
  APT_REPO_DIR="$CACHE_DIR/repo/apt/"
  PIP_REPO_DIR="$CACHE_DIR/repo/pip/"
  OTHER_FILES_DIR="$CACHE_DIR/repo/files/"
  REPO_BIN_DIR="$CACHE_DIR/repo/bin/"
  REPO_ROM_DIR="$CACHE_DIR/repo/rom/"
  CHAOGE_GIFT_DIR="$CACHE_DIR/gift/$GIFT_DIR_NAME"
  rm -rf $CACHE_DIR
  mkdir -p $CACHE_DIR
}

if [[ "$0" == "$BASH_SOURCE" ]]; then
    CURRENT_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    CURRENT_SCRIPT_NAME=$(basename "$0")
    CURRENT_SCRIPT_PATH=$CURRENT_SCRIPT_DIR/$CURRENT_SCRIPT_NAME
    setup_work_dir
    with_logs_piped $LOG_PATH run_directly
else
    RUN_AS_SOURCE_FLAG=1
    CURRENT_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    CURRENT_SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
    CURRENT_SCRIPT_PATH=$CURRENT_SCRIPT_DIR/$CURRENT_SCRIPT_NAME
    setup_work_dir
    with_logs_piped $LOG_PATH run_as_source
fi
