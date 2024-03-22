#!/bin/bash -x
WORK_DIR=`dirname $0`
cd $WORK_DIR
PROJECT_DIR=`pwd`

completed() {
  if [[ $1 -eq 0 ]]; then
    echo -e "$2 success"
  else
    echo -e "$2 failed"
    exit 1
  fi
}

# master or bugfix
if [[ "$GIT_BRANCH" =~ "master" ]];then
   BRANCH_FLAG=999
else
   BRANCH_FLAG=${GIT_BRANCH##*.}
fi

if [ -z $BUILD_NUMBER ];then BUILD_NUMBER=0; fi
BIG_NUMBER=$(crudini --get setup.cfg metadata big_number_version)
SMALL_NUMBER=$BRANCH_FLAG
PBR_VERSION=$BIG_NUMBER.$SMALL_NUMBER.$BUILD_NUMBER
export PBR_VERSION

function activate_conda_env() {
  echo "enter function name: ${FUNCNAME[0]}"
  local conda_env_name="$1"
  source ~/.bashrc
  completed $? "source ~/.bashrc"
  eval "$(conda shell.bash hook)"
  completed $? "conda shell.bash hook"
  conda activate "$conda_env_name"
  completed $? "activate conda $conda_env_name env"
}

git log --pretty=format:"%h %ad %s" --date=short -30 > ChangeLog
openssl enc -aes-256-cbc -salt -in ChangeLog -out doc/ChangeLog -pass pass:astute -md sha256

rm -rf dist
activate_conda_env astute
python setup.py sdist
