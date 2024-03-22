from hostadmin.business import Usage

installed_env_hosts = [f'host{i+1:0>3}' for i in range(20)]

hostcli_disk_device_list_dec = {
    'name':"盘符",
    'size':'容量',
    'media':'介质',
    'model':'型号',
    'rate':'转速',
    'form':'尺寸',
    'osd': 'osd'
}

hostcli_disk_device_list = [
    {
        'name':f'sd{i}',
        'model':'INTELSSDSC2KG96',
        'media':'HDD',
        'rate':'',
        'form':'2.5',
        'size_gb':'1024',
        'size_str':'255GB',
        'osd':"osd.1" or '',
    } for i in 'abcdefg'
]

hostcli_disk_cache_list_dec = {
    'name':"盘符",
    'size':'容量',
    'media':'介质',
    'model':'型号',
    'backends': '后端数量',
    'backends_detail': '后端详情'
}

hostcli_disk_cache_list = [
    {
        'name':f'sd{i}',
        'model':'INTELSSDSC2KG96',
        'media':'SSD',
        'size':'1024',
        'size_str':'255GB',
        'backends':{
            'osd.0': {
                'osd': 'osd.0',
                'bcache_part': '/dev/sdb1',
                'bcache_size': 107374182400,
                'data_disk': '/dev/sda',
                'db_part': '/dev/sdb2',
                'db_size': 42949672960
            },
        }
    } for i in 'abcdefg'
]

hostcli_disk_osd_list_dec = {
    'osd':'osd',
    'data_disk':'盘符',
    'size':'容量',
    'media':'介质',
    'bcache_part':'bcache分区',
    'db_part':'db分区',
    'data_lv': 'data逻辑卷',
	'db_lv': 'db逻辑卷',
}

hostcli_disk_osd_list = {
    'osd.0': {
		'fs_id': '3711e4aa-ae98-11ee-b0f6-3cecef87406b',
		'data_lv': 'at_bcache0-at_lv',
		'db_lv': 'at_sdb2-at_lv',
		'data_disk': '/dev/sda',
		'db_part': '/dev/sdb2',
		'bcache_part': '/dev/sdb1',
		'media': 'HDD',
		'size': 1000204886016
	},
    'osd.1': {
		'fs_id': '3711e4aa-ae98-11ee-b0f6-3cecef87406b',
		'data_lv': 'at_bcache1-at_lv',
		'db_lv': 'at_sdb4-at_lv',
		'data_disk': '/dev/sdc',
		'db_part': '/dev/sdb4',
		'bcache_part': '/dev/sdb3',
		'media': 'HDD',
		'size': 1000204886016
	},
}

hostcli_network_list_dec = {
		'name': '网口名',
		'driver': '驱动',
		'speed': '速率',
		'link': '状态',
		'ip': '地址',
		'bond': 'Bond名称',
		'bond_mode': 'Bond模式',
        'usage':'用途'
}
                           			                         
hostcli_network_list = [
    {
		'name': f'eth{i}',
		'driver': 'ggg',
		'speed': '1000mbs',
		'link': 'yes',
		'ip': ['192.222.1.44/24'],
		'bond': 'mgt-nic',
		'bond_mode': 'balance-lcd',
		'vlan': 1,
        'usage':[Usage.mgt, Usage.access]
	} for i in range(4)
]

network_config_menu = {
    '查看网络配置': Usage.mgt,
    '配置Ceph集群网络': Usage.ceph_cluster,
    '配置Ceph访问网络': Usage.ceph_public,
    '配置业务网络': Usage.vm, 
    '配置外部网络': Usage.ext,
    '配置接入网络': Usage.access,
}
