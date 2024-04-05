# https://pve.proxmox.com/pve-docs/api-viewer/index.html
import json
import logging

from cg_utils import func, execute

LOG = logging.getLogger(__name__)


class Nodes:
    def __init__(self, node_name=None):
        self.node_name = node_name or func.get_current_node_hostname()

    def stop_vm(self, vmid):
        # pvesh create /nodes/{node}/qemu/{vmid}/status/stop
        cmd = f'pvesh create /nodes/{self.node_name}/qemu/{vmid}/status/stop'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'stop vm vmid={vmid}', content)

    def set_node_config(self, vmid, key, value):
        # pvesh set /nodes/host055/qemu/105/config --hostpci0 0000:04:00.0,pcie=1,x-vga=1,romfile=vbios_1002_1638.bin.bin
        node_config_dict  = self.get_node_config(vmid)
        if key == 'hostpci':
            for i in range(10):
                if f'hostpci{i}' not in node_config_dict:
                    key = f'hostpci{i}'
                    break
        if value:
            cmd = f'pvesh create /nodes/{self.node_name}/qemu/{vmid}/config --{key} "{value}"'
        else:
            cmd = f'pvesh set /nodes/{self.node_name}/qemu/{vmid}/config --delete {key}'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, f'set node_config key={key}, value={value}', content)

    def get_node_config(self, vmid):
        """
        {
            "bios" : "ovmf",
            "boot" : "order=scsi0",
            "cores" : 4,
            "cpu" : "host",
            "digest" : "9a88f47382c6fbc32fa58a701b4d61400e422a21",
            "efidisk0" : "local:105/vm-105-disk-0.qcow2,efitype=4m,pre-enrolled-keys=1,size=528K",
            "hostpci0" : "0000:04:00.0,pcie=1,x-vga=1,romfile=vbios_1002_1638.bin",
            "hostpci1" : "0000:04:00.1,romfile=AMDGopDriver.rom",
            "ide0" : "local:iso/virtio-win-0.1.229.iso,media=cdrom,size=522284K",
            "ide2" : "local:iso/windows_10_business_LTSC_2021_x64.ISO,media=cdrom,size=4925988K",
            "machine" : "pc-q35-8.1",
            "memory" : "8192",
            "meta" : "creation-qemu=8.1.5,ctime=1711186432",
            "name" : "win10-gpu-1.157",
            "net0" : "virtio=BC:24:11:70:FB:DF,bridge=vmbr0,firewall=1",
            "numa" : 0,
            "onboot" : 1,
            "ostype" : "win10",
            "parent" : "gpu-ok-157",
            "scsi0" : "local:105/vm-105-disk-1.qcow2,iothread=1,size=100G",
            "scsihw" : "virtio-scsi-single",
            "smbios1" : "uuid=41204869-8bae-4113-b2cc-0469552d8ba7",
            "sockets" : 1,
            "usb0" : "host=25a7:fa23",
            "usb1" : "host=1c4f:0049",
            "vga" : "none",
            "vmgenid" : "8f4194c2-2df9-4379-abc3-4492c863f9b2"
        }
        """
        cmd = f'pvesh get /nodes/{self.node_name}/qemu/{vmid}/config --output-format json'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, 'get node_config', content)
        try:
            return json.loads(content)
        except Exception as e:
            execute.completed(1, 'json loads node_config')

    def qemu_list(self):
        """
        [
            {
                "cpu" : 0,
                "cpus" : 6,
                "disk" : 0,
                "diskread" : 0,
                "diskwrite" : 0,
                "maxdisk" : 150323855360,
                "maxmem" : 8589934592,
                "mem" : 0,
                "name" : "win10-1.156",
                "netin" : 0,
                "netout" : 0,
                "status" : "stopped",
                "uptime" : 0,
                "vmid" : 101
            },
        ]
        """
        cmd = f'pvesh get /nodes/{self.node_name}/qemu --output-format json'
        flag, content = execute.execute_command(cmd)
        execute.completed(flag, 'get qemu_list', content)
        try:
            return json.loads(content)
        except Exception as e:
            execute.completed(1, 'json loads qemu_list')
