#!/bin/bash
# NOTE: This script is used only by the operation engineer to upload a single image file !!!
INPUT_FILE=$(realpath $1)
shopt -s expand_aliases
source ~/.bashrc
source /etc/cs/admin-openrc.sh

function ts_echo() {
    echo "[$(date +'%F %T')]: $*"
}

openstack --version >/dev/null 2>&1
if [ $? != 0 ]; then
   echo "please source /etc/cs/admin-openrc.sh first!"
   exit -1
fi
if [ $# -ne 1 ]; then
    echo "Upload image with image ini filename."
    echo "Usage: upload-image.sh image/image-xxx.ini"
    exit -1
fi

docker_exec_qemuimg="docker exec -uroot -it glance_api qemu-img"

file $INPUT_FILE | grep -Ei "ISO 9660|QEMU QCOW|boot sector" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "update image with original file..."
    supposed_os_type="linux"
    supposed_os_distro="arch"
    distros=("arch" "centos" "debian" "fedora" "freebsd" "gentoo" "mandrake" "mandriva" "mes" "msdos" "netbsd" "netware" "openbsd" "opensolaris" "opensuse" "rhel" "sled" "ubuntu" "windows")
    image_name_lower=$(echo "$INPUT_FILE" | tr '[:upper:]' '[:lower:]')
    for distro in "${distros[@]}"; do
        if [[ $image_name_lower == *$distro* ]]; then
            supposed_os_distro=$distro
            if [[ $distro == "windows" ]] || [[ $distro == "msdos" ]]; then
                supposed_os_type="windows"
            fi
        fi
    done
    IMAGE_INI_FILE=$INPUT_FILE.ini
    supposed_image_name=$(basename $INPUT_FILE | cut -d'.' -f1)$(date +"_%Y%m%d")

    cat >$IMAGE_INI_FILE <<EOF
[DEFAULT]
# name: the image name in the cloud
name=$supposed_image_name

# file: the image file name
file=$INPUT_FILE

# upload image to nfs,rbd,file
image_backend_type = rbd

# os_type: [windows,linux]
os_type=$supposed_os_type

# os_distro: [arch,centos,debian,fedora,freebsd,
#             gentoo,mandrake,mandriva,mes,msdos,
#             netbsd,netware,openbsd,opensolaris,
#             opensuse,rhel,sled,ubuntu,windows]
os_distro=$supposed_os_distro

# os_admin_user & os_password
os_admin_user=admin
os_password=********

# hw_firmware_type: bios or uefi
#hw_firmware_type=uefi

# hw_qemu_guest_agent: yes or no
hw_qemu_guest_agent=yes

# img_config_drive: optional or mandatory
img_config_drive=optional

# define by skyline
usage_type=common
EOF
    vi $IMAGE_INI_FILE
    echo -e "\033[0;32;1mpress enter to start ...\033[0m"
    read -r _
else
    IMAGE_INI_FILE=$INPUT_FILE
    echo "update image with config file..."
    if [ "$(file $IMAGE_INI_FILE | grep -c 'ASCII text')" -eq 0 ]; then
        file $IMAGE_INI_FILE
        echo "$IMAGE_INI_FILE is not an ASCII text file?"
        exit -1
    fi
fi

images_dir=$(
    cd $(dirname $IMAGE_INI_FILE)
    pwd
)
image_name=$(crudini --get $IMAGE_INI_FILE DEFAULT name | sed 's/,/ /g')
file_name=$(crudini --get $IMAGE_INI_FILE DEFAULT file | sed 's/,/ /g')
file_name=$(basename $file_name)

image_backend_type=$(crudini --get $IMAGE_INI_FILE DEFAULT image_backend_type 2>/dev/null | sed 's/,/ /g')
os_type=$(crudini --get $IMAGE_INI_FILE DEFAULT os_type 2>/dev/null | sed 's/,/ /g')
os_distro=$(crudini --get $IMAGE_INI_FILE DEFAULT os_distro 2>/dev/null | sed 's/,/ /g')
os_admin_user=$(crudini --get $IMAGE_INI_FILE DEFAULT os_admin_user 2>/dev/null | sed 's/,/ /g')
os_password=$(crudini --get $IMAGE_INI_FILE DEFAULT os_password 2>/dev/null | sed 's/,/ /g')
hw_firmware_type=$(crudini --get $IMAGE_INI_FILE DEFAULT hw_firmware_type 2>/dev/null | sed 's/,/ /g')
hw_qemu_guest_agent=$(crudini --get $IMAGE_INI_FILE DEFAULT hw_qemu_guest_agent 2>/dev/null | sed 's/,/ /g')
img_config_drive=$(crudini --get $IMAGE_INI_FILE DEFAULT img_config_drive 2>/dev/null | sed 's/,/ /g')
usage_type=$(crudini --get $IMAGE_INI_FILE DEFAULT usage_type 2>/dev/null | sed 's/,/ /g')

image_property=""
[ -z "$os_type" ] || image_property="$image_property --property os_type=$os_type"
[ -z "$os_distro" ] || image_property="$image_property --property os_distro=$os_distro"
[ -z "$os_admin_user" ] || image_property="$image_property --property os_admin_user=$os_admin_user"
[ -z "$os_password" ] || image_property="$image_property --property os_password=$os_password"
[ -z "$hw_qemu_guest_agent" ] || image_property="$image_property --property hw_qemu_guest_agent=$hw_qemu_guest_agent"
[ -z "$hw_firmware_type" ] || image_property="$image_property --property hw_firmware_type=$hw_firmware_type"
[ -z "$img_config_drive" ] || image_property="$image_property --property img_config_drive=$img_config_drive"
[ -z "$usage_type" ] || image_property="$image_property --property usage_type=$usage_type"

function get_image_backend {
    image_backend=$(crudini --get /etc/kolla/glance-api/glance-api.conf glance_store default_backend)
    if [[ "$image_backend"x == "rbdx" ]];then
        image_pool='images'
        rbd_image_name=$IMAGE_ID
    elif [[ "$image_backend"x == "cinderx" ]];then
        # We assume cinder backend contain rbd, or else we should set 
        # 'image_backend_type' to non-rbd value
        image_pool='volumes'
        rbd_image_name="volume-$IMAGE_ID"
    fi
}

function upload_image_to_glance_rbd_backend {
    IMAGE_ID=$(uuidgen)
    get_image_backend
    rbd import $IMAGE_FILE $rbd_image_name --dest-pool $image_pool --image-format 2
    rbd snap create --pool $image_pool --image $rbd_image_name --snap snap
    rbd snap protect --pool $image_pool --image $rbd_image_name --snap snap

    # Define the variables with image data
    image_id=$IMAGE_ID
    name=$image_name
    size=$IMAGE_SIZE
    image_status='active'
    disk_format='raw'
    container_format='bare'
    ts_echo "Calculate md5sum..."
    checksum=$(md5sum $IMAGE_FILE | awk '{print $1}')
    ts_echo "md5sum: $checksum"
    owner=$(openstack project show admin -c id -f value)
    min_disk=0
    min_ram=0
    protected=1
    virtual_size=$IMAGE_SIZE
    visibility='public'
    os_hidden=0
    os_hash_algo='sha512'
    ts_echo "Calculate sha512sum..."
    os_hash_value=$(sha512sum $IMAGE_FILE | awk '{print $1}')
    ts_echo "sha512sum: $os_hash_value"
    
    ts_echo "Update glance database..."
    # Insert into images table
    mysql glance -e "INSERT INTO images (id, name, size, status, created_at, updated_at, deleted_at, deleted, disk_format, container_format, checksum, owner, min_disk, min_ram, protected, virtual_size, visibility, os_hidden, os_hash_algo, os_hash_value) VALUES ('$image_id', '$name', $size, '$image_status', NOW(), NOW(), NULL, 0, '$disk_format', '$container_format', '$checksum', '$owner', $min_disk, $min_ram, $protected, $virtual_size, '$visibility', $os_hidden, '$os_hash_algo', '$os_hash_value');"
    
    # Insert into image_properties table
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'os_type','$os_type', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'os_distro','$os_distro', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'os_admin_user', '$os_admin_user', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'os_password', '$os_password', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'hw_qemu_guest_agent', '$hw_qemu_guest_agent', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'img_config_drive','$img_config_drive', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'usage_type','$usage_type', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'owner_specified.openstack.md5','', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'owner_specified.openstack.sha256','', NOW(), NOW(), NULL, 0);"
    mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'owner_specified.openstack.object','images/$name', NOW(), NOW(), NULL, 0);"
    if [[ "$hw_firmware_type"x == "biosx" || "$hw_firmware_type"x == "uefix" ]];then
        mysql glance -e "INSERT INTO image_properties (image_id, name, value, created_at, updated_at, deleted_at, deleted) VALUES ('$image_id', 'hw_firmware_type', '$hw_firmware_type', NOW(), NOW(), NULL, 0);"
    fi
    
    # Insert into image_locations table
    if [[ "$image_backend"x == "rbdx" ]];then
        image_location="rbd://$(ceph fsid)/images/$image_id/snap"
        meta_data='{"store": "rbd"}'
    else
        image_location='cinder://cinder/volume-$image_id'
        meta_data='{"store": "cinder"}'
    fi
    location_status='active'
    mysql glance -e "INSERT INTO image_locations (image_id, value, created_at, updated_at, deleted_at, deleted, meta_data, status) VALUES ('$image_id', '$image_location', NOW(), NOW(), NULL, 0, '$meta_data', '$location_status');"
    ts_echo "Update glance database ok"
    openstack image show $image_id
}

function upload_image_to_glance {
    IMAGE_NAME=$1
    IMAGE_FILE=$2
    IMAGE_PROPERTY=$3

    [ -z "$IMAGE_NAME" ] && exit -1
    [ -z "$IMAGE_FILE" ] && exit -1

    IMAGE_TAR_TMPDIR=''
    if [[ $IMAGE_FILE =~ ".tar.gz" ]]; then
        IMAGE_TAR_TMPDIR=$(sudo mktemp -d /tmp/images.XXXXXXXXXX)
        echo "sudo tar -zxvf $IMAGE_FILE -C $IMAGE_TAR_TMPDIR ... "
        sudo tar -zxvf "$IMAGE_FILE" -C "$IMAGE_TAR_TMPDIR"
        sudo chmod 777 -fR "$IMAGE_TAR_TMPDIR"
        UNTAR_FILE=$(sudo ls $IMAGE_TAR_TMPDIR | grep -v ".md5")
        IMAGE_FILE="$IMAGE_TAR_TMPDIR/$UNTAR_FILE"
    fi

    # how to get the image?
    # file or url or copyfrom?
    IMAGE_CREATE_MODE=file
    #   --file <FILE>         Local file that contains disk image to be uploaded
    #                         during creation. Alternatively, images can be passed
    #                         to the client via stdin.

    #IMAGE_DISK_FORMAT=`sudo qemu-img info $IMAGE_FILE | grep "file format"| awk -F':' '{print $2}'| sed 's/[^[:alnum:]]//g'`
    IMAGE_DISK_FORMAT=
    FILE_DESC=$(file $IMAGE_FILE | cut -d : -f 2)
    if [ ! -z "$(echo $FILE_DESC | grep 'QEMU QCOW')" ]; then
        if [[ "$image_backend_type"x == "rbd"x ]]; then
            echo "Only raw format images can be imported to ceph directly!"
            ts_echo "Detect qcow2 image file, convert it to raw format..."
            STAGE_DIR="/var/lib/docker/volumes/glance/_data/staging"
            STAGE_FILE=$STAGE_DIR/$(basename $IMAGE_FILE)
            STAGE_FILE_MAP="/var/lib/glance/staging/$(basename $IMAGE_FILE)"
            \cp $IMAGE_FILE $STAGE_FILE
            $docker_exec_qemuimg convert -O raw $STAGE_FILE_MAP $STAGE_FILE_MAP.raw
            rm -f $STAGE_FILE
            ts_echo "Convert complete."
            IMAGE_SIZE=$($docker_exec_qemuimg info $STAGE_FILE_MAP.raw | grep "virtual size" | awk -F'(' '{print $2}' | awk '{print $1}')
            if [ -z $IMAGE_SIZE ];then
                echo "Get image$STAGE_FILE.raw virtual size failed"
                rm -f $STAGE_FILE.raw
                exit -1
            fi
            export IMAGE_FILE=$STAGE_FILE.raw
            export IMAGE_DISK_FORMAT="raw"
        else
            export IMAGE_DISK_FORMAT="qcow2"
        fi
    elif [ ! -z "$(echo $FILE_DESC | grep 'ISO')" ]; then
        export IMAGE_DISK_FORMAT="iso"
    elif [ ! -z "$(echo $FILE_DESC | grep 'boot sector')" ]; then
        export IMAGE_DISK_FORMAT="raw"
    else
        echo "Format of image file $IMAGE_FILE is not support!"
        exit
    fi

    # --container-format <CONTAINER_FORMAT>
    #                       Container format of image. Acceptable formats: ami,
    #                       ari, aki, bare, and ovf.
    IMAGE_CONTAINER_FORMAT=bare
    #   --owner <TENANT_ID>   Tenant who should own image.
    IMAGE_OWNER=
    #   --min-disk <DISK_GB>  Minimum size of disk needed to boot image (in
    #                         gigabytes).
    IMAGE_MIN_DISK=
    #   --min-ram <DISK_RAM>  Minimum amount of ram needed to boot image (in
    #                         megabytes).
    IMAGE_MIN_RAM=
    #   --location <IMAGE_URL>
    #                         URL where the data for this image already resides. For
    #                         example, if the image data is stored in swift, you
    #                         could specify 'swift+http://tenant%3Aaccount:key@auth_
    #                         url/v2.0/container/obj'. (Note: '%3A' is ':' URL
    IMAGE_URL=
    #   --copy-from <IMAGE_URL>
    #                         Similar to '--location' in usage, but this indicates
    #                         that the Glance server should immediately copy the
    #                         data and store it in its configured image store.
    COPY_FROM=
    #   --is-public {True,False}
    #                         Make image accessible to the public.
    IS_PUBLIC=True
    #   --is-protected {True,False}
    #                         Prevent image from being deleted.
    IS_PROTECTED=True
    #   --property <key=value>
    #                         Arbitrary property to associate with image. May be
    #                         used multiple times.

    openstack image show $IMAGE_NAME >/dev/null 2>&1
    if [ $? == 0 ]; then
        echo "Image with name $IMAGE_NAME is already created in glance!"
        if [ -n "$IMAGE_TAR_TMPDIR" ]; then
            echo "sudo rm -fR $IMAGE_TAR_TMPDIR..."
            sudo rm -fR "$IMAGE_TAR_TMPDIR"
        fi
        if [[ ! -z $STAGE_FILE && -e $STAGE_FILE.raw ]];then
            rm -f $STAGE_FILE.raw
        fi
        exit -1
    fi

    if [ "$IMAGE_CREATE_MODE" == "file" ]; then
        if [ ! -e "$IMAGE_FILE" ]; then
            echo "Image file $IMAGE_FILE does not exist!"
            if [ -n "$IMAGE_TAR_TMPDIR" ]; then
                echo "sudo rm -fR $IMAGE_TAR_TMPDIR..."
                sudo rm -fR "$IMAGE_TAR_TMPDIR"
            fi
            if [[ ! -z $STAGE_FILE && -e $STAGE_FILE.raw ]];then
                rm -f $STAGE_FILE.raw
            fi
            exit -1
        fi

        if [[ $IMAGE_DISK_FORMAT == "raw" && $image_backend_type == "rbd" ]];then
            upload_image_to_glance_rbd_backend 
        else
            OPTION=" --file $IMAGE_FILE"
            [ ! -z "$IMAGE_DISK_FORMAT" ] && OPTION+=" --disk-format $IMAGE_DISK_FORMAT"
            [ ! -z "$IMAGE_CONTAINER_FORMAT" ] && OPTION+=" --container-format $IMAGE_CONTAINER_FORMAT"
            [ "${IS_PUBLIC}x" == "Truex" ] && OPTION+=" --public"
            [ "${IS_PROTECTED}x" == "Truex" ] && OPTION+=" --protected"
            [ ! -z "$IMAGE_PROPERTY" ] && OPTION+=" $IMAGE_PROPERTY"
            echo openstack image create $OPTION
            openstack image create $OPTION $IMAGE_NAME
        fi
    fi

    if [[ ! -z $STAGE_FILE && -e $STAGE_FILE.raw ]];then
        rm -f $STAGE_FILE.raw
    fi

    if [ -n "$IMAGE_TAR_TMPDIR" ]; then
        echo "sudo rm -fR $IMAGE_TAR_TMPDIR..."
        sudo rm -fR "$IMAGE_TAR_TMPDIR"
    fi
}

# main
if [ ! -f "$images_dir/$file_name" ]; then
    echo "Image file $images_dir/$file_name does not exist!"
    exit -1
fi

openstack image show "$image_name" >/dev/null 2>&1
if [ $? == 0 ]; then
    echo "Image with name $image_name is already created in glance!"
    exit -1
fi

upload_image_to_glance "$image_name" "$images_dir/$file_name" "$image_property"
