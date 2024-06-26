#!/bin/bash -x
WORK_DIR=`dirname $0`
cd $WORK_DIR
package_base_name=$(crudini --get setup.cfg metadata name)

if [ -z $BUILD_NUMBER ] || [ -z $JOB_NAME ] || [ -z $GIT_BRANCH ]; then
   echo "Not in jenkins!"
   echo "you can test use follow command"
   echo "export BUILD_NUMBER=0; export JOB_NAME=cc-aio; export PROJECT_NAME=cc-aio; export GIT_BRANCH=master"
   exit 1
fi

# master or bugfix
if [[ "$GIT_BRANCH" =~ "master" ]];then
   BRANCH_FLAG=999
else
   BRANCH_FLAG=${GIT_BRANCH##*.}
fi

BIG_NUMBER=$(crudini --get setup.cfg metadata big_number_version)
SMALL_NUMBER=$BRANCH_FLAG
PBR_VERSION=$BIG_NUMBER.$SMALL_NUMBER.$BUILD_NUMBER
export PBR_VERSION

ls dist |grep "^$package_base_name.*\.tar\.gz$" | wc -l | grep -q "^1$"
if [ $? -ne 0 ]; then
    echo "Error: $package_base_name*.tar.gz not found!"
    exit -1
fi

package_name=$(ls dist |grep "^$package_base_name.*\.tar\.gz$")
package_new_name=$package_base_name-$PBR_VERSION.tar.gz
/bin/cp dist/$package_name $package_new_name

IDENTITY=samba@192.168.1.4
FILEDIR=/smb/ata-WDC_WD40EJRX-89AKWY0_WD-WX72D71J52XA/fileserver/OneDev/projects/$PROJECT_NAME/$GIT_BRANCH
echo "FILEDIR is $FILEDIR"
md5sum $package_new_name > $package_new_name.md5
ssh $IDENTITY mkdir -p $FILEDIR/$BUILD_NUMBER
scp $package_new_name $package_new_name.md5 $IDENTITY:$FILEDIR/$BUILD_NUMBER/
ssh $IDENTITY "rm -rf $FILEDIR/latest;ln -sf $FILEDIR/$BUILD_NUMBER $FILEDIR/latest"
