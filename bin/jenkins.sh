#!/bin/bash -x
# by: wang.chao
# date: 2023-5-8
WORK_DIR=`dirname $0`
cd $WORK_DIR

if [ -z $BUILD_NUMBER ] || [ -z $JOB_NAME ] || [ -z $GIT_BRANCH ]; then
   echo "Not in jenkins!"
   echo "debug use follow"
   echo "export BUILD_NUMBER=0; export JOB_NAME=cc-aio; export PROJECT_NAME=cc-aio; export GIT_BRANCH=master"
   exit -1
fi

# master or bugfix
if [[ "$GIT_BRANCH" =~ "master" ]];then
   BRANCH_FLAG=999
else
   BRANCH_FLAG=${GIT_BRANCH##*.}
fi

BIG_NUMBER="1"
SMALL_NUMBER=$BRANCH_FLAG
PBR_VERSION=$BIG_NUMBER.$SMALL_NUMBER.$BUILD_NUMBER
export PBR_VERSION

package_new_name="$PROJECT_NAME-$PBR_VERSION.bin"

IDENTITY=wc@192.168.1.4
FILEDIR=/smb/4t/fileserver/OneDev/projects/$PROJECT_NAME/$GIT_BRANCH
md5sum $package_new_name >> ${package_new_name}.md5
ssh $IDENTITY mkdir -p $FILEDIR/$BUILD_NUMBER
scp $package_new_name ${package_new_name}.md5 $IDENTITY:$FILEDIR/$BUILD_NUMBER/
ssh $IDENTITY "rm -rf $FILEDIR/latest;ln -sf $FILEDIR/$BUILD_NUMBER $FILEDIR/latest"
