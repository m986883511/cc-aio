import os
import glob
import logging
import traceback
import json
import re
import time

from oslo_config import cfg

from cc_utils import execute, func, file, _

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class DiskEndPoint(object):
    def cephadm_shell(self, cmd):
        cmd = "cephadm shell " + cmd
        if os.environ.get('IN_CLICK'):
            import click
            click.secho(cmd.strip())
        flag, out = execute.execute_command(cmd)
        return flag, out

    def get_boot_disk(self):
        # 通过 pkname 获取 /boot 分区所在的磁盘
        cmd = "lsblk `df /boot | grep -Eo '/dev/[a-z0-9]*'` -ndo pkname"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, 'get boot disk by lsblk', out)
        return out.strip()

    def format_disk_and_create_one_primary(self, ctxt, dev_disk, confirm_text):
        true_confirm_text='yes-i-really-really-format-it'
        flag = true_confirm_text == confirm_text
        execute.completed(not flag, 'check confirm_text', f'input confirm_text not equal "{true_confirm_text}"')
        flag, content = execute.execute_command(f'apt install parted -y')
        execute.completed(flag, 'apt install parted', content)
        self.umount_disk(dev_disk)
        flag, content = execute.execute_command(f'parted {dev_disk} --script mklabel gpt mkpart primary ext4 1MiB 100%')
        execute.completed(flag, 'format_disk_and_create_one_primary', content)
        flag, content = execute.execute_command(f'sleep 5')
        execute.completed(flag, 'wait 5 seconds', content)
        flag, content = execute.execute_command(f'mkfs.ext4 {dev_disk}1')
        execute.completed(flag, f'mkfs.ext4 {dev_disk}1', content)
    
    def umount_disk(self, dev_disk):
        block_list = self.get_lsblk_of_disk(dev_disk)
        LOG.info(f'umount_disk_and_mount_new block_list={block_list}')
        for block_dict in block_list:
            mount = block_dict.get('mountpoint')
            if mount:
                flag, content = execute.execute_command(f"sed -i '/ \{mount} /d' /etc/fstab")
                execute.completed(flag, f"delete {mount} in /etc/fstab", content)
                flag, content = execute.execute_command(f"umount /dev/{block_dict['name']}")
                execute.completed(flag, f"umount /dev/{block_dict['name']}", content)

    def umount_disk_and_mount_new(self, ctxt, dev_disk, new_mount_path, confirm_text):
        true_confirm_text='yes-i-really-really-mount-it'
        flag = true_confirm_text == confirm_text
        execute.completed(not flag, 'check confirm_text', f'input confirm_text not equal "{true_confirm_text}"')
        self.umount_disk(dev_disk)
        """
        blkid /dev/sdb1
        UUID=66a4b8fe-8050-4e0e-b546-df42a9473706 /home/wc/share/4t ext4 defaults 0 0
        """
        #todo: 使用uuid更好
        flag, content = execute.execute_command(f'mkdir -p {new_mount_path}')
        execute.completed(flag, f'mkdir {new_mount_path}', content)
        flag, content = execute.execute_command(f"sed -i '/ \{new_mount_path} /d' /etc/fstab")
        execute.completed(flag, f"delete old {new_mount_path} in /etc/fstab")
        flag, content = execute.execute_command(f'echo "{dev_disk}1 {new_mount_path} ext4 defaults 0 0" >> /etc/fstab')
        execute.completed(flag, f'set {dev_disk}1 {new_mount_path} to /etc/fstab', content)
        flag, content = execute.execute_command(f'mount -a')
        execute.completed(flag, f'mount -a', content)
        flag, content = execute.execute_command(f'chown -R samba:sambashare {new_mount_path}')
        execute.completed(flag, f"chown new_mount_path={new_mount_path}")


    def get_all_disk_by_id(self, disk_list):
        def get_id(disk_name, disk_serial):
            cmd = "ls -l /dev/disk/by-id/ |grep -v part |grep -v pve |grep -v -i lvm"
            flag, out = execute.execute_command(cmd)
            lines = func.get_string_split_list(out, split_flag='\n')
            execute.completed(flag, '获取所有磁盘by-id', out)
            for link_line in lines:
                line_2 = func.get_string_split_list(link_line, split_flag='->')
                if len(line_2) != 2:
                    continue
                the_disk_id = func.get_string_split_list(line_2[0], split_flag=' ')[-1]
                the_disk_name = func.get_string_split_list(line_2[1], split_flag='/')[-1]
                if disk_name == the_disk_name:
                    if the_disk_id.endswith(disk_serial):
                        return the_disk_id

        for value_dict in disk_list:
            if value_dict.get('type') != 'disk':
                continue
            name, serial = value_dict['name'], value_dict['serial']
            value_dict['id'] = get_id(name, serial)
            block_list = self.get_lsblk_of_disk(f'/dev/{name}')
            value_dict['mount'] = [value.get('mountpoint') for value in block_list if value.get('mountpoint')]
            value_dict['block'] = [value.get('name') for value in block_list if value.get('name') != name]

    def disk_parts(self, disk_name):
        flag, out = execute.execute_command(f'ls /dev/{disk_name}*')
        execute.completed(flag, f'获取{disk_name}所有分区', out)
        out_list = func.get_string_split_list(out, split_flag=' ')
        out_list = [i for i in out_list if not i.endswith(disk_name)]
        return out_list

    def get_all_disks(self, ctxt, return_root_disk=False):
        """
        [
            {
                "name": "sda",
                "model": "MICRON SLC SSD",
                "size": 128000000000,
                "serial": "HXJ201802Q1124A176",
                "id": "ata-MICRON_SLC_SSD_HXJ201802Q1124A176",
                "mount": [
                    "/mnt"
                ],
                "media": "SSD"
            }
        ]
        """
        # 获取所有磁盘，-d 不含磁盘下的分区, -b size为字节单位，-o 字段，-J json格式输出
        cmd = "lsblk -d -b -o name,model,rota,size,type,serial -J --sort name 2>/dev/null"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, '获取所有磁盘', out)
        try:
            disks = json.loads(out).get('blockdevices', [])
        except Exception as e:
            execute.completed(1, 'get disks by lsblk', str(e))

        self.get_all_disk_by_id(disks)

        all_disks = []
        for disk in disks:
            # 过滤掉不是disk类型的，例如rom
            if disk.get('type') != 'disk':
                continue
            
            if '/' in disk.get('mount') or []:
                disk['root_disk_flag'] = True
                # 过滤boot分区所在的磁盘
                if not return_root_disk:
                    continue

            # 格式转换和去掉中间字段
            disk['media'] = 'HDD' if disk.get('rota') else 'SSD'
            disk.pop('rota')
            disk.pop('type')

            all_disks.append(disk)

        return all_disks

    def get_lsblk_of_disk(self, dev_disk):
        """
         [
            {
                "name": "sda",
                "type": "disk",
                "size": 128000000000,
                "mountpoint": ""
            },{
                "name": "sda1",
                "type": "part",
                "size": 127998623744,
                "mountpoint": "/mnt"
            }
        ]
        """
        # dev_disk 格式为 /dev/xxx
        cmd = f"lsblk {dev_disk} -b -o name,type,size,mountpoint -J --sort name 2>/dev/null"
        flag, out = execute.execute_command(cmd)
        try:
            disks = json.loads(out).get('blockdevices', [])
        except Exception as e:
            execute.completed(1, _(f"get part of disk {dev_disk} by lsblk"), str(e))
        return disks
    
    def get_part_of_disk(self, disk_name):
        # disk_name 格式为 /dev/xxx
        cmd = f"lsblk {disk_name} -b -o name,type,size -J --sort name 2>/dev/null"
        flag, out = execute.execute_command(cmd)
        try:
            disks = json.loads(out).get('blockdevices', [])
        except Exception as e:
            execute.completed(1, _(f"get part of disk {disk_name} by lsblk"), str(e))

        all_parts = []
        for disk in disks:
            if disk.get('type') == 'part':
                all_parts.append(dict(name=disk.get('name'), size=disk.get('size')))

        return all_parts

    def get_lv_of_disk(self, disk_name):
        cmd = f"lsblk {disk_name} -b -o name,type -J --sort name 2>/dev/null"
        flag, out = execute.execute_command(cmd)
        if flag:
            return []
        try:
            disks = json.loads(out).get('blockdevices', [])
        except Exception as e:
            raise Exception(f"failed to get lv of disk {disk_name} by lsblk: {e}!")

        return [ disk.get('name') for disk in disks if disk.get('type') == 'lvm' ]

    def get_part_info(self, part):
        part_no = re.search("[0-9]*$", part).group()
        part_disk = part[:-len(part_no)]
        if part_disk[-1] == 'p' and part_disk[-2].isdigit():
            part_disk = part_disk[:-1]
        return part_disk, part_no

    def get_smart_info(self, disk_name):
        # 获取机械盘的转速和尺寸
        # disk_name 格式为 /dev/xxx
        cmd = f"smartctl -i {disk_name} -j 2>/dev/null" 
        flag, out = execute.execute_command(cmd)
        try:
            smart = json.loads(out)
            rate = str(smart.get('rotation_rate', '-'))
            form = smart.get('form_factor',{}).get('name', '-')
        except Exception as e:
            LOG.error("failed to get disk info by smartctl: %s!" % e)
            rate = '-'
            form = '-'

        return dict(rate=rate, form=form)

    def get_all_osds(self):
        all_osds = {}

        # 根据pvs信息，生成从vg到pv的map表
        vg_2_pv = {}
        cmd = "pvs"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, 'get_all_osds pvs', out)
        out_lines = out.split('\n')
        for line in out_lines:
            line = [ l for l in line.split(' ') if l ]
            if len(line) >= 2:
                vg_2_pv[line[1]] = line[0]

        # 根据bcachectl list信息，生成BcacheDev到BackingDev（数据盘）、CacheDev（缓存盘分区）的map表
        bcache_devices = {}
        for bcache in self.get_bcaches():
            # 过滤掉无效的 BcacheDev
            if not bcache.get('BackingDev'):
                continue
            bcache_devices[bcache.get('BcacheDev')] = bcache

        # 获取osd的block的lv（这些lv的格式为全路径的vg-lv）
        cmd = "ls /var/lib/ceph/*/osd.*/block -l"
        flag, out = execute.execute_command(cmd)
        if flag:
            LOG.error("failed to list osd block: %s!" % out)
        else:
            out_lines = out.split('\n')
            for line in out_lines:
                osd_id = re.search('/osd.[0-9]*/block', line).group().split('/')[1]
                data_lv = line.split('/')[-1]
                fs_id = re.search('/var/lib/ceph/.*/osd', line).group().split('/')[-2]
                if osd_id in all_osds and all_osds.get(osd_id).get('fs_id') != fs_id:
                    logging.error("暂时不支持多集群，/var/lib/ceph/ 目录下有多种 ceph fsid")
                    return {}
                all_osds[osd_id] = dict(fs_id=fs_id, data_lv=data_lv)

        # 获取osd的db的lv（这些lv的格式为全路径的vg-lv）
        cmd = "ls /var/lib/ceph/*/osd.*/block.db -l"
        flag, out = execute.execute_command(cmd)
        if flag:
            LOG.error("failed to list osd block.db: %s!" % out)
        else:
            out_lines = out.split('\n')
            for line in out_lines:
                osd_id = re.search('/osd.[0-9]*/block.db', line).group().split('/')[1]
                db_lv = line.split('/')[-1]
                fs_id = re.search('/var/lib/ceph/.*/osd', line).group().split('/')[-2]
                if osd_id in all_osds and all_osds.get(osd_id).get('fs_id') != fs_id:
                    logging.error("暂时不支持多集群，/var/lib/ceph/ 目录下有多种 ceph fsid")
                    return {}
                all_osds[osd_id].update(dict(fs_id=fs_id, db_lv=db_lv))

        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            data_vg = osd.get('data_lv').split('-')[0]
            osd['data_disk'] = vg_2_pv.get(data_vg, '')

            if osd.get('db_lv'):
                db_vg = osd.get('db_lv').split('-')[0]
                osd['db_part'] = vg_2_pv.get(db_vg, '')

            # 获取bcache盘的后端数据盘和缓存分区
            if osd['data_disk'] in bcache_devices:
                osd['bcache_part'] = bcache_devices.get(osd['data_disk']).get('CacheDev')
                osd['data_disk'] = bcache_devices.get(osd['data_disk']).get('BackingDev')

        return all_osds

    def enabled_bcache(self):
        cmd = "lsmod | grep -w bcache"
        flag, out = execute.execute_command(cmd)
        return not flag

    def get_bcaches(self):
        if not self.enabled_bcache():
            return []

        cmd = "bcachectl list -f json"
        flag, out = execute.execute_command(cmd)
        try:
            bcaches = json.loads(out).get('bcache_devs')
            if bcaches is None:
                bcaches = []
        except Exception as e:
            raise Exception(f"failed to get bcahce devices by bcachectl list: {e}!")
        return bcaches

    def get_cache_devs(self):
        if not self.enabled_bcache():
            return []

        cmd = "bcachectl list -f json"
        flag, out = execute.execute_command(cmd)
        try:
            cache_devs = json.loads(out).get('cache_devs')
            if cache_devs is None:
                cache_devs = []
        except Exception as e:
            raise Exception(f"failed to get cahce devices by bcachectl list: {e}!")
        return [ dev.get('device') for dev in cache_devs ]

    def list_data_disks(self, ctxt):
        def is_exist_cache_parts(disk_name, cache_parts):
            parts = self.get_part_of_disk(disk_name)
            for part in parts:
                part_name = "/dev/" + part.get('name')
                if part_name in cache_parts:
                    return True
            return False

        data_disk_2_osd_id = {}
        cache_parts = []
        all_osds = self.get_all_osds()
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            data_disk_2_osd_id[osd.get('data_disk')] = osd_id
            if osd.get('bcache_part'):
                cache_parts.append(osd.get('bcache_part'))
            if osd.get('db_part'):
                cache_parts.append(osd.get('db_part'))

        data_disks = []
        for disk in self.get_all_disks(ctxt=ctxt):
            # 过滤掉已经为osd做缓存服务的盘
            if is_exist_cache_parts("/dev/" + disk.get('name'), cache_parts):
                continue

            disk_name = "/dev/" + disk.get('name')
            disk.update(self.get_smart_info(disk_name))
            disk['osd'] = data_disk_2_osd_id.get(disk_name, '')
            data_disks.append(disk)

        return data_disks

    def list_cache_disks(self, ctxt):
        cmd = 'modprobe -n -v "bcache"'
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, 'check system support bcache config', out)

        # 从osd信息中收集bcache和db分区信息
        all_osds = self.get_all_osds()
        bcache_parts = {}
        db_parts = {}
        osd_data_disks = {}
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            bcache_parts[osd.get('bcache_part')] = osd_id
            db_parts[osd.get('db_part')] = osd_id
            osd_data_disks[osd.get('data_disk')] = osd_id

        cache_disks = self.get_all_disks(ctxt=ctxt)

        # 过滤掉机械盘，机械盘不允许做缓存盘
        cache_disks = [ disk for disk in cache_disks if disk.get('media') != 'HDD']
        # 过滤掉已经是OSD的盘
        cache_disks = [ disk for disk in cache_disks if '/dev/' + disk.get('name') not in osd_data_disks ]

        for disk in cache_disks:
            backends = {}
            parts = self.get_part_of_disk("/dev/" + disk.get('name'))
            for part in parts:
                part_name = "/dev/" + part.get('name') 
                if part_name in bcache_parts:
                    osd_id = bcache_parts.get(part_name)
                    if osd_id not in backends:
                        backends[osd_id] = dict(osd=osd_id)
                    backends[osd_id]['bcache_part'] = part_name
                    backends[osd_id]['bcache_size'] = part.get('size')
                    backends[osd_id]['data_disk'] = all_osds.get(osd_id).get("data_disk")
                elif part_name in db_parts:
                    osd_id = db_parts.get(part_name)
                    if osd_id not in backends:
                        backends[osd_id] = dict(osd=osd_id)
                    backends[osd_id]['db_part'] = part_name
                    backends[osd_id]['db_size'] = part.get('size')
            disk['backends'] = backends

        return cache_disks

    def list_osds(self, ctxt):
        all_disk = {}
        for disk in self.get_all_disks(ctxt=ctxt):
            disk_name = "/dev/" + disk.get('name')
            all_disk[disk_name] = disk

        all_osds = self.get_all_osds()
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            data_disk = all_disk.get(osd.get('data_disk'))
            if data_disk:
                osd['media'] = data_disk.get('media')
                osd['size'] = data_disk.get('size')

        return all_osds

    def clear_lv(self, lv):
        # 根据pvs信息，生成从vg到pv的map表
        vg_2_pv = {}
        cmd = "pvs"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, _(f"clear_lv pvs"), out)
        out_lines = out.split('\n')
        for line in out_lines:
            line = [ l for l in line.split(' ') if l ]
            if len(line) >= 2:
                vg_2_pv[line[1]] = line[0]

        vg = lv.split('-')[0]
        lv = lv.split('-')[1]
        pv = vg_2_pv.get(vg)
        if not lv or not vg or not pv:
            LOG.info(f"failed to get lv info: pv={pv}, vg={vg}, lv={lv}!")
            return
        cmd = f"lvremove {vg}/{lv} -y; vgremove {vg} -y; pvremove {pv} -y;"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, _(f"clear_lv {lv}"), out)

    def clear_lvs(self):
        all_osds = self.get_all_osds()
        all_osd_lvs = []
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            if osd.get('data_lv'):
                all_osd_lvs.append(osd.get('data_lv'))
            if osd.get('db_lv'):
                all_osd_lvs.append(osd.get('db_lv'))

        cmd = "lvs"
        flag, out = execute.execute_command(cmd)
        if flag:
            raise Exception(f"failed to lvs: {out}!")

        out_lines = out.split('\n')
        for line in out_lines:
            if ' last seen on ' in line and ' not found' in line:
                continue
            line = [ l for l in line.split(' ') if l ]
            if len(line) < 2:
                continue
            lv = line[0]
            vg = line[1]
            if lv.lower() == 'lv' and vg.lower() == 'vg':
                continue
            if lv in ['root', 'swap']:
                continue
            if vg + '-' + lv in all_osd_lvs:
                continue
            # 此处的lvol0的命名需要跟lvcreate处的名称保持一致
            if lv == "at_lv":
                self.clear_lv(f"{vg}-{lv}")

    def clear_part(self, part):
        if part == '(none attached)':
            return

        # 根据bcachectl list信息，生成BcacheDev到BackingDev（数据盘）、CacheDev（缓存盘分区）的map表
        bcache_devices = {}
        for bcache in self.get_bcaches():
            # 过滤掉无效的 BcacheDev
            if not bcache.get('BackingDev'):
                continue
            bcache_devices[bcache.get('CacheDev')] = bcache

        cmd = ""
        if part in bcache_devices:
            bcache = bcache_devices.get(part)
            disk = bcache.get('BackingDev')
            lv_dev = f"/dev/at_{bcache.get('ShortName')}/at_lv"
            if os.path.exists(lv_dev):
                # 重要：在bcache上建立有逻辑卷，需要先删掉device mapper
                cmd += f"dmsetup remove {lv_dev};"
            cmd += f"bcachectl stop {disk};"
            cmd += f"bcachectl unregister {part};"
            if os.path.exists(disk):
                cmd += f"dd if=/dev/zero of={disk} bs=4M count=1;"
            if os.path.exists(part):
                cmd += f"dd if=/dev/zero of={part} bs=4M count=1;"
            part_disk, part_no = self.get_part_info(part)
            cmd += f"parted -s {part_disk} rm {part_no};"
            # 在 lvmdevices 中有残留，需要主动删除
            cmd += f"lvmdevices --deldev {bcache.get('BcacheDev')};"
        elif part in self.get_cache_devs():
            '''
            在 bcache_devs 中没有，在 cache_devs 中有的情况：
            # bcachectl list
            bcache (backing) devices:
            BcacheDev         BackingDev        CacheDev          cache_mode        state
            /dev/at_bcache2                     (none attached)
            /dev/bcache2      /dev/sdh          /dev/nvme0n1p1    writeback         clean

            Registered cache devices:
            /dev/nvme0n1p1 9d41ac2c-d908-4852-bbc0-512a33180dd1
            /dev/nvme0n1p3 7563db17-7b83-4628-9415-8a5f6a92db8f

            # bcachectl list -f json
            {"bcache_devs":[{"BcacheDev":"/dev/at_bcache2","ShortName":"at_bcache2","BackingDev":"","CacheDev":"(none attached)","CacheSetUUID":"(none attached)","Slaves":null,"Map":{"":"","BackingDev":"","BcacheDev":"/dev/at_bcache2","CacheDev":"(none attached)","cache_mode":"","state":""}},{"BcacheDev":"/dev/bcache2","ShortName":"bcache2","BackingDev":"/dev/sdh","CacheDev":"/dev/nvme0n1p1","CacheSetUUID":"9d41ac2c-d908-4852-bbc0-512a33180dd1","Slaves":["nvme0n1p1","sdh"],"Map":{"":"","BackingDev":"/dev/sdh","BcacheDev":"/dev/bcache2","CacheDev":"/dev/nvme0n1p1","cache_mode":"writeback","state":"clean"}}], 
             "cache_devs":[{"device":"/dev/nvme0n1p1","UUID":"9d41ac2c-d908-4852-bbc0-512a33180dd1"},{"device":"/dev/nvme0n1p3","UUID":"7563db17-7b83-4628-9415-8a5f6a92db8f"}]}
            '''
            cmd += f"bcachectl unregister {part};"
            if os.path.exists(part):
                cmd += f"dd if=/dev/zero of={part} bs=4M count=1;"
            part_disk, part_no = self.get_part_info(part)
            cmd += f"parted -s {part_disk} rm {part_no};"
        else:
            lv_dev = f"/dev/at_{part[len('/dev/'):]}/at_lv;"
            if os.path.exists(lv_dev):
                cmd += f"dmsetup remove {lv_dev};"

            '''
            清理磁盘上其他操作系统安装的残留lvm
            sdc             8:32   0 447.1G  0 disk
            └─sdc3          8:35   0 445.5G  0 part
              ├─rl00-swap 253:2    0     4G  0 lvm
              ├─rl00-home 253:3    0 371.5G  0 lvm
              └─rl00-root 253:4    0    70G  0 lvm
            '''
            lvs = self.get_lv_of_disk(part)
            for lv in lvs:
                lv_dev = f"/dev/mapper/{lv}"
                if os.path.exists(lv_dev):
                    cmd += f"dmsetup remove {lv_dev};"

            if os.path.exists(part):
                cmd += f"dd if=/dev/zero of={part} bs=4M count=1;"
            part_disk, part_no = self.get_part_info(part)
            cmd += f"parted -s {part_disk} rm {part_no};"
            cmd += f"lvmdevices --deldev {part};"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, _(f"clear_part {part}"), out)
        self._partprobe(_(f"clear_part {part} then partprobe"))

    def _partprobe(self, desc):
        flag, out = execute.execute_command('partprobe', shell=False, timeout=60)
        execute.completed(flag, desc, out)

    def clear_cache_disk(self, cache_disk):
        all_osds = self.get_all_osds()
        all_osd_parts = []
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            if osd.get('bcache_part'):
                all_osd_parts.append(osd.get('bcache_part'))
            if osd.get('db_part'):
                all_osd_parts.append(osd.get('db_part'))

        parts = self.get_part_of_disk(cache_disk)
        for part in parts:
            part_name = "/dev/" + part.get('name')
            if part_name in all_osd_parts:
                continue
            self.clear_part(part_name)

        # 检查是否清理干净了
        parts = self.get_part_of_disk(cache_disk)
        for part in parts:
            part_name = "/dev/" + part.get('name')
            if part_name in all_osd_parts:
                continue
            # 没有清理干净
            execute.completed(1, _(f"缓存盘 {cache_disk} 上有多余的分区清理"))

        # 如果在残留有跟分区设备重名的文件，则会影响后续的分区，需要清理
        for dev in glob.glob(f"{cache_disk}*"):
            if os.path.isfile(dev):
                os.remove(dev)

    def check_add_osds_args(self, ctxt, osd_disks, cache_disk, allow_hdd_as_osd=False):
        # osd_disks的格式："sda,sdb"
        osd_disks = osd_disks or ''
        osd_disks = func.get_string_split_list(osd_disks, split_flag=',')
        if not osd_disks:
            execute.completed(1, _("OSD_DISKS 参数为空"))

        # 获取所有磁盘信息
        all_disks = {}
        for data_disk in self.get_all_disks(ctxt=ctxt):
            all_disks[data_disk.get('name')] = data_disk

        # 从osd信息中收集数据盘、bcache和db分区信息
        all_osds = self.get_all_osds()
        bcache_parts = []
        db_parts = []
        osd_data_disks = []
        for osd_id in all_osds:
            osd = all_osds.get(osd_id)
            bcache_parts.append(osd.get('bcache_part'))
            db_parts.append(osd.get('db_part'))
            osd_data_disks.append(osd.get('data_disk'))

        max_osd_disk_size = 0
        for osd_disk in osd_disks:
            if osd_disk not in all_disks:
                execute.completed(1, _(f"检查数据盘 {osd_disk} 存在"))

            if "/dev/" + osd_disk in osd_data_disks:
                execute.completed(1, _(f"检查数据盘 {osd_disk} 不是OSD"))

            parts = self.get_part_of_disk("/dev/" + osd_disk)
            for part in parts:
                part_name = "/dev/" + part.get('name') 
                if part_name in bcache_parts or part_name in db_parts:
                    execute.completed(1, _(f"检查数据盘 {osd_disk} 未用于缓存盘"))

            # 统计所有数据盘中的容量最大值
            disk_size = all_disks.get(osd_disk).get('size')
            if disk_size > max_osd_disk_size:
                max_osd_disk_size = disk_size

        if not cache_disk:
            # 如果没有配置缓存盘，如果数据盘的介质是HDD，机械盘未开启bcache配置会导致性能不足
            for osd_disk in osd_disks:
                data_disk = all_disks.get(osd_disk)
                if data_disk.get('media') == 'HDD':
                    if allow_hdd_as_osd:
                        LOG.warning('you set allow_hdd_as_osd as True, 数据盘 {osd_disk} 是机械盘，未开启bcache会导致性能不足')
                    else:
                        execute.completed(1, _(f'数据盘 {osd_disk} 是机械盘，未开启bcache会导致性能不足'))
            return { 'osd_disks': osd_disks }

        if not self.enabled_bcache():
            execute.completed(1, _(f"检查内核bcache模块"))

        # cache_disk的格式："name=xxx,bcache_size=140,db_size=40,max_backends=5"
        cache_args = {}
        for x in cache_disk.split(','):
            x = x.strip()
            if len(x.split('=')) != 2:
                execute.completed(1, f'检查CACHE_DISK 参数 {x} 格式')
            k = x.split('=')[0].strip()
            v = x.split('=')[1].strip()
            cache_args[k] = v

        # 检查cache_disk是否有字段遗漏
        for k in ['name', 'bcache_size', 'db_size', 'max_backends']:
            if k not in cache_args:
                execute.completed(1, _(f"检查CACHE_DISK参数"), f'参数中缺少{k}')

        # 检查cache_disk的各字段格式是否正确
        cache_disk_name = cache_args.get('name')
        try:
            bcache_size = int(cache_args.get('bcache_size'))
        except:
            execute.completed(1, _(f"检查bcache_size是数字"))
        try:
            db_size = int(cache_args.get('db_size'))
        except:
            execute.completed(1, _(f"检查db_size是数字"))
        try:
            max_backends = int(cache_args.get('max_backends'))
        except:
            execute.completed(1, _(f"检查max_backends是数字"))

        # cache_disk_name 的校验
        if cache_disk_name in osd_disks:
            execute.completed(1, _(f"检查缓存盘{cache_disk_name}不在数据盘的列表中"))
        if cache_disk_name not in all_disks:
            execute.completed(1, _(f"检查缓存盘{cache_disk_name}存在"))
        cache_disk = None
        for c in self.list_cache_disks(ctxt):
            if c.get('name') == cache_disk_name:
                cache_disk = c
                break
        if not cache_disk:
            execute.completed(1, _(f"检查缓存盘{cache_disk_name}在可用的缓存盘列表中"))

        # 容量相关的校验
        min_bcache_size = round(max_osd_disk_size * 0.05 / (1024 * 1024 * 1024), 2)
        min_db_size = round(max_osd_disk_size * 0.02 / (1024 * 1024 * 1024), 2)
        if bcache_size < min_bcache_size:
            execute.completed(1, _(f"检查 bcache_size 容量", f"配置的 bcache_size 容量不足, 需不低于数据盘容量的5% {min_bcache_size}GB"))
        if db_size < min_db_size:
            execute.completed(1, f"检查 db_size 容量", _(f"配置的 db_size 容量不足, 需不低于数据盘容量的2% {min_db_size}GB"))
        if (bcache_size + db_size) * 1024 * 1024 * 1024 * max_backends > cache_disk.get('size'):
            err_mg = _(f"({bcache_size}GB + {db_size}GB) * {max_backends} 超过缓存盘容量")
            execute.completed(1, f"检查缓存盘容量", err_mg)
        if len(cache_disk.get('backends')) + len(osd_disks) > max_backends:
            err_mg = _(f"缓存盘已为 {len(cache_disk.get('backends'))} 个OSD服务, 再增加 {len(osd_disks)} 个OSD，会超出 max_backends={max_backends}")
            execute.completed(1, f"检查 max_backends", err_mg)
        for backend in cache_disk.get('backends').values():
            if backend.get('bcache_size') != bcache_size * 1024 * 1024 * 1024:
                err_mg = _("配置的 bcache_size 与存量的 bcache 分区大小不一致")
                execute.completed(1, f"检查 bcache_size", err_mg)
            if backend.get('db_size') != db_size * 1024 * 1024 * 1024:
                err_mg = _("配置的 db_size 与存量的 db 分区大小不一致")
                execute.completed(1, f"检查 db_size", err_mg)

        return {
            'osd_disks': osd_disks,
            'cache_disk_name': cache_disk_name,
            'bcache_size': bcache_size,
            'db_size': db_size,
            'cache_disk': cache_disk
        }

    def make_gpt(self, disk_name):
        cmd = f"parted -s {disk_name} print"
        flag, out = execute.execute_command(cmd)
        out_lines = out.split('\n')
        for line in out_lines:
            if 'Partition Table:' in line:
                if line.split(':')[-1].strip() == 'unknown':
                    cmd = f"parted -s {disk_name} mklabel gpt"
                    execute.execute_command(cmd)
                    return

    def creat_part(self, size, label, disk_name):
        # 如果有重名的分区，先删除再创建
        part = self.get_part_by_label(label)
        if part:
            self.clear_part(part)

        cmd = f"sgdisk -g -n 0:0:+{size}G -c 0:{label} {disk_name}"
        flag, out = execute.execute_command(cmd)
        self._partprobe(_(f"creat_part {part} then partprobe"))

    def get_part_by_label(self, label):
        cmd = f"blkid -o device -t PARTLABEL={label}"
        flag, out = execute.execute_command(cmd)
        part = out.strip()
        if flag or not part or '/dev/' not in part:
            return ""
        return part

    def make_cache(self, osd_disks, cache_disk, bcache_size, db_size):
        # 如果分区表丢失，尝试创建gpt分区表，避免后续分区失败
        self.make_gpt(cache_disk)

        # 进行bcache和db分区
        osd_disks_info = {}
        cmd = ""
        for osd_disk in osd_disks:
            cmd = f"lsblk -n --output serial -d {osd_disk} | sed 's/ /_/g'"
            flag, out = execute.execute_command(cmd)
            if flag:
                LOG.error("failed to sn of disk: %s!" % out)
                execute.completed(1, f"获取数据盘 {osd_disk} 的 sn")
                
            sn = out.strip()
            if not sn or len(sn) > 32:
                execute.completed(1, f"检查数据盘 {osd_disk} 的 sn", f"数据盘 {osd_disk} 的 sn={sn} 为空或超过32个字符")
            osd_disks_info[osd_disk] = dict(sn=sn)

            # cmd = f"sgdisk -g -n 0:0:+{bcache_size}G -c 0:{sn}_bc {cache_disk};"
            # cmd += f"sgdisk -g -n 0:0:+{db_size}G -c 0:{sn}_db {cache_disk};"
            # cmd += "partprobe"
            # flag, out = execute.execute_command(cmd)
            self.creat_part(bcache_size, sn+"_bc", cache_disk)
            self.creat_part(db_size, sn+"_db", cache_disk)

        # 建立bcache分区和db分区与数据盘的关系
        for osd_disk in osd_disks:
            sn = osd_disks_info.get(osd_disk).get('sn')
            
            # cmd = f"blkid -o device -t PARTLABEL={sn}_bc"
            # flag, out = execute.execute_command(cmd)
            # part = out.strip()
            # if flag or not part or '/dev/' not in part:
            #     return False, _(f"数据盘 {osd_disk} 的 bcache 分区创建失败"), {}
            # osd_disks_info.get(osd_disk).update(dict(bcache_part=part))

            # cmd = f"blkid -o device -t PARTLABEL={sn}_db"
            # flag, out = execute.execute_command(cmd)
            # part = out.strip()
            # if flag or not part or '/dev/' not in part:
            #     return False, _(f"数据盘 {osd_disk} 的 db 分区创建失败"), {}
            # osd_disks_info.get(osd_disk).update(dict(db_part=part))
            part = self.get_part_by_label(sn+"_bc")
            flag = 0 if part else 1
            execute.completed(flag, _(f"数据盘 {osd_disk} 的 bcache 分区创建"))
            osd_disks_info.get(osd_disk).update(dict(bcache_part=part))

            part = self.get_part_by_label(sn+"_db")
            flag = 0 if part else 1
            execute.completed(flag, _(f"数据盘 {osd_disk} 的 db 分区创建"))
            osd_disks_info.get(osd_disk).update(dict(db_part=part))

        # 创建bcache
        for osd_disk in osd_disks:
            bcache_part = osd_disks_info.get(osd_disk).get('bcache_part')
            cmd = f"bcachectl stop {osd_disk};"
            cmd += f"bcachectl unregister {bcache_part};"
            cmd += f"dd if=/dev/zero of={osd_disk} bs=4M count=1;"
            cmd += f"dd if=/dev/zero of={bcache_part} bs=4M count=1;"
            cmd += f"wipefs -a {osd_disk};"
            cmd += f"wipefs -a {bcache_part};"
            cmd += f"sleep 5;"
            cmd += f"make-bcache -B {osd_disk} -C {bcache_part} --wipe-bcache;"
            flag, out = execute.execute_command(cmd)

        # 等待5秒后再开始检测
        time.sleep(5)

        # 检查bcache的创建结果
        bcache_devices = {}
        for bcache in self.get_bcaches():
            # 过滤掉无效的 BcacheDev
            if not bcache.get('BackingDev'):
                continue
            if bcache.get('CacheDev') == '(none attached)':
                continue
            bcache_devices[bcache.get('BackingDev')] = bcache

        for osd_disk in osd_disks:
            bcache_dev = bcache_devices.get(osd_disk, {}).get('BcacheDev')
            flag = 0 if bcache_dev else 1
            execute.completed(flag, _(f"数据盘 {osd_disk} 的 bcache 创建"))
            osd_disks_info.get(osd_disk).update(dict(bcache_dev=bcache_dev))

        # bcache盘参数配置
        cmd = ""
        for osd_disk in osd_disks:
            bcache_dev = bcache_devices.get(osd_disk).get('ShortName')
            cmd += f"echo writeback > /sys/class/block/{bcache_dev}/bcache/cache_mode;"
            cmd += f"echo 40 > /sys/class/block/{bcache_dev}/bcache/writeback_percent;"
            cmd += f"echo 0 > /sys/class/block/{bcache_dev}/bcache/sequential_cutoff;"
            cmd += f"echo 0 > /sys/class/block/{bcache_dev}/bcache/cache/congested_write_threshold_us;"
            cmd += f"echo 0 > /sys/class/block/{bcache_dev}/bcache/cache/congested_read_threshold_us;"
        flag, out = execute.execute_command(cmd)

        execute.completed(0, f"为 {osd_disks} 准备bcache和db")
        return osd_disks_info

    def create_lv(self, pv):
        vg = "at_" + pv.split('/')[-1]
        lv = "at_lv"
        lv_dev = f"/dev/{vg}/{lv}"
        if os.path.exists(lv_dev):
            cmd = f"dmsetup remove {lv_dev}"
            flag, out = execute.execute_command(cmd)
        cmd = f"vgcreate {vg} {pv}"
        flag, out = execute.execute_command(cmd)
        if flag:
            LOG.error("failed to create vg: %s!" % out)
            return ""
        cmd = f"lvcreate -l +100%FREE {vg} --name {lv}"
        flag, out = execute.execute_command(cmd)
        if flag:
            LOG.error("failed to create lv: %s!" % out)
            return ""
        return f"/dev/{vg}/{lv}"

    def add_osds(self, ctxt, osd_disks, cache_disk, allow_hdd_as_osd=False):
        hostname = func.get_current_node_hostname()
        if not re.match(r'host\d{3}$', hostname):
            execute.completed(1, _(f"检查hostname {hostanme}格式"), "需为 hostxxx")

        args = self.check_add_osds_args(ctxt, osd_disks, cache_disk, allow_hdd_as_osd=allow_hdd_as_osd)

        # 清理残留lv/vg/pv
        self.clear_lvs()

        osd_disks = [ '/dev/' + osd_disk for osd_disk in args.get('osd_disks') ]
        cache_disk = "/dev/" + args.get('cache_disk_name') if args.get('cache_disk_name') else ""
        bcache_size = args.get('bcache_size')
        db_size = args.get('db_size')

        # 清理缓存盘上的多余分区（没有被OSD的bcache和db用到的分区）
        if cache_disk:
            self.clear_cache_disk(cache_disk)

        # 清理数据盘上的残留分区，如果有的话，例如其他系统装机残留等
        for osd_disk in osd_disks:
            parts = self.get_part_of_disk(osd_disk)
            for part in parts:
                self.clear_part("/dev/" + part.get('name'))
            parts = self.get_part_of_disk(osd_disk)
            if len(parts):
                execute.completed(1, _(f"数据盘 {osd_disk} 上有多余的分区清理"))

            # 此处dd清理一下数据盘，避免后续创建lv失败
            '''
            [root@host035 cs]# vgcreate at_sdd /dev/sdd
              Cannot use /dev/sdd: device is partitioned
              Command requires all devices to be found.
            [root@host035 cs]# dd if=/dev/zero of=/dev/sdd bs=4M count=1
            1+0 records in
            1+0 records out
            4194304 bytes (4.2 MB, 4.0 MiB) copied, 0.0176488 s, 238 MB/s
            [root@host035 cs]# vgcreate at_sdd /dev/sdd
              Physical volume "/dev/sdd" successfully created.
              Volume group "at_sdd" successfully created
            '''
            cmd = f"dd if=/dev/zero of={osd_disk} bs=4M count=1"
            flag, out = execute.execute_command(cmd)

        # 创建bcache
        if cache_disk:
            osd_disks_info = self.make_cache(osd_disks, cache_disk, bcache_size, db_size)

        # 创建lv和OSD
        for osd_disk in osd_disks:
            if cache_disk:
                bcache_lv = self.create_lv(osd_disks_info.get(osd_disk).get("bcache_dev"))
                db_lv = self.create_lv(osd_disks_info.get(osd_disk).get("db_part"))
                if not bcache_lv or not db_lv:
                    execute.completed(1, f"创建 bcache_lv={bcache_lv} 或 db_lv={db_lv} ")
                cmd = f"ceph orch daemon add osd {hostname}:data_devices={bcache_lv},db_devices={db_lv}"
                flag, out = self.cephadm_shell(cmd)
                execute.completed(flag, f"为 {osd_disk} 创建OSD", out)
            else:
                data_lv = self.create_lv(osd_disk)
                if not data_lv:
                    execute.completed(1, _(f"创建 data_lv={data_lv} "))
                cmd = f"ceph orch daemon add osd {hostname}:data_devices={data_lv}"
                flag, out = self.cephadm_shell(cmd)
                execute.completed(flag, f"为 {osd_disk} 创建OSD", out)

    def check_remove_osds_args(self, ctxt, osd_ids):
        # osd_ids的格式："osd.1,osd.2"
        osd_ids = osd_ids or ''
        osd_ids = func.get_string_split_list(osd_ids, split_flag=',')
        if not osd_ids:
            execute.completed(1, f"检查OSD_IDS参数存在")

        # 从osd信息中收集数据盘列表
        all_osds = self.get_all_osds()
        for osd_id in osd_ids:
            if osd_id not in all_osds:
                execute.completed(1, f"检查OSD {osd_id} 存在")

        return osd_ids

    def remove_osd(self, osd_id, osd):
        if not osd.get('data_lv'):
            execute.completed(1, f"检查{osd_id} 的数据盘逻辑卷不为空")

        # 删osd
        osd_short_id = osd_id.split('.')[1]
        cmd = f"ceph orch daemon rm --force {osd_id}"
        flag, out = self.cephadm_shell(cmd)
        execute.completed(flag, f"删除{osd_id}", out) 
        cmd = f"cephadm ceph-volume lvm zap --destroy --osd-id {osd_short_id}"
        flag, out = execute.execute_command(cmd)
        execute.completed(flag, f"删除{osd_id}", out)
        cmd = f"ceph osd purge --force {osd_short_id}"
        flag, out = self.cephadm_shell(cmd)
        execute.completed(flag, f"删除{osd_id}", out)

        # 等待osd被删掉，等待lv、vg、pv被自动清理
        for i in range(30):
            time.sleep(1)
            path = f"/var/lib/ceph/{osd.get('fs_id')}/{osd_id}/"
            if os.path.exists(path):
                LOG.error(f"删除 {osd_id} 失败{i}，残留有 {path}")
                continue
            path = f"/dev/mapper/{osd.get('data_lv')}"
            if os.path.exists(path):
                LOG.error(f"删除 {osd_id} 失败{i}，残留有 {path}")
                continue
            if osd.get('db_lv'):
                path = f"/dev/mapper/{osd.get('db_lv')}"
                if os.path.exists(path):
                    LOG.error(f"删除 {osd_id} 失败{i}，残留有 {path}")
                    continue
            break
        else:
            execute.completed(flag, f"删除{osd_id}", '等待超时')

        if osd.get('bcache_part') and osd.get('db_part'):
            # 手动再清理一下逻辑卷
            self.clear_lv(osd.get('data_lv'))
            self.clear_lv(osd.get('db_lv'))
            # 清理bcache分区和db分区
            self.clear_part(osd.get('bcache_part'))
            self.clear_part(osd.get('db_part'))

        execute.completed(0, _(f"删除OSD={osd_id}"))

    def remove_osds(self, ctxt, osd_ids):
        osd_ids = self.check_remove_osds_args(ctxt, osd_ids)
        all_osds = self.get_all_osds()
        for osd_id in osd_ids:
            self.remove_osd(osd_id, all_osds.get(osd_id))
        execute.completed(0, _(f"删除OSDs={osd_ids}"))

    def check_clear_disks_args(self, ctxt, disks):
        # disks的格式："all,sda,sdb"
        disks = disks or ''
        disks = func.get_string_split_list(disks, split_flag=',')
        if not disks:
            execute.completed(1, f"检查DISKS参数存在")

        all_disks = [ disk.get('name') for disk in self.get_all_disks(ctxt=ctxt) ]
        for disk in disks:
            if disk == 'all':
                continue
            if disk not in all_disks:
                execute.completed(1, f"检查disk {disk} 存在")

        if 'all' in disks:
            return all_disks
        else:
            return disks

    def clear_disks(self, ctxt, disks):
        disks = self.check_clear_disks_args(ctxt, disks)
        for disk in disks:
            self.clear_cache_disk("/dev/" + disk)
        execute.completed(0, _(f"清理DISKs={disks}"))
