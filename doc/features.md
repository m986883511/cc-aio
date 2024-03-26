# PVE TUI v1.0 功能清单

## 系统架构
	基于OpenStack Zed版本
	基于Rocky9或Kylin Server作为HostOS
	基于Kolla的容器化部署
	基于KVM计算虚拟化
	基于OVN网络虚拟化
	基于Ceph Quincy存储虚拟化
	基于Skyline的管理界面
	基于GPE的监控告警系统

## 安装部署
	支持在Intel、AMD、海光X86服务器，鲲鹏ARM服务器上部署
	支持OpenStack云计算云平台的界面化部署，添加和移除计算节点，与Ceph对接
	支持Ceph分布式存储系统的界面化部署，添加和移除OSD
	支持管理网络、存储网络、业务网络、外部网路、接入网络的界面化配置，包括Bond配置和VLAN配置
	支持设置和更新云平台参数配置，包括资源超分配置、资源预留配置、外部时钟源配置
	支持单台服务器的最小化部署、支持3台及以上服务器的超融合部署、支持不超过240台服务器的大规模部署
	支持3台服务器组成控制节点集群，提供虚拟IP接入管理
	支持分布式存储采用3副本，单台服务器故障数据不丢失
	支持分布式存储的SSD全闪部署，SSD+HDD带缓存盘的混合部署
	支持部署操作中断后、再次重复继续部署

## 管理界面
	支持管理界面的多语言切换，支持中文和英文
	支持在对象列表中通过关键属性进行过滤搜索
	支持列表中部分列的自定义、支持列表的下载导出、支持开启和关闭自动刷新
	支持面包屑和跳转
	支持各种ID的界面快速复制
	支持侧边菜单栏的展开和折叠
	支持(系统控制台)管理平台、(项目)控制台，登录后若权限允许，可以在系统控制台和项目控制台之间切换、在多个项目间切换
	支持用户登录和退出登录、支持登录后修改用户密码
	支持通过应用凭证，采用API方式访问云平台，创建应用凭证时可通过选择角色控制权限、可设置有效期

## 首页
	支持平台概况、虚拟资源用量、虚拟资源总览、关键服务状态展示
	支持项目概况、项目配额使用情况展示

## 计算
	云主机
		支持CPU云主机、直通GPU云主机、虚拟GPU云主机的统一管理
		支持云主机的向导式创建，选择和设置可用域、(规格)云主机类型、启动源、系统盘的类型和大小、数据盘的类型和大小、网络、端口、安全组、名称、SSH密钥对
		支持云主机的批量创建，创建云主机时可指定批量创建的云主机数量，批量创建的云主机能够自动按序号命名
		支持基于镜像创建云主机、基于云主机快照创建云主机、基于可启动云硬盘创建云主机
		支持创建云主机时选择系统盘、数据盘是否跟随云主删除而删除
		支持创建云主机时选择调度策略，包括智能调度、手动指定计算节点
		支持创建云主机时选择是否加入某云主机组
		支持创建云主机时配置用户自定义数据，配合cloud-init进行云主机内部的自动初始化和配置
		支持云主机的状态管理，包括开机、关机、(硬)重启、软重启、锁定、解锁、挂起、暂停、恢复、归档、取消归档
		支持云主机的资源动态关联，包括挂载网卡、卸载网卡、挂载云硬盘、卸载云硬盘、绑定浮动IP、管理安全组
		支持云主机的配置变更，包括修改云主机类型、修改密码、重建云主机
		支持云主机的名称修改、打标签、删除
		支持云主机的(冷)迁移、热迁移、重置状态
		支持云主机的控制台访问，支持发送Ctrl+Alt+Del的组合键
		支持在云主机详情中，进行云主机的云硬盘、云主机快照、网卡、浮动IP、安全组、操作日志的查看和管理
	云主机快照
		支持基于云主机创建云主机快照
		支持基于云主机快照创建云主机
		支持将云主机快照转换成云硬盘，用于从云硬盘启动云主机
		支持云主机快照的编辑和删除
	云主机类型
		支持按X86架构、异构计算、自定义来分栏管理云主机类型
		支持云主机类型的创建，选择和设置架构、类型、名称、CPU核数、内存容量、内网带宽、NUMA节点、内存页
		支持直通GPU和虚拟GPU的云主机规格创建，设置GPU型号和GPU数量
		支持多种自定义规格在部署阶段的预创建
		支持自定义云主机类型的访问控制，是否公有，限定允许访问的项目列表
		支持自定义云主机类型的元数据管理，包括自定义元数据、看门狗、CPU拓扑、CPU模式、CPU绑核、随机数生成器、CPU/磁盘/网络性能限制、是否开启启动菜单、是否开启内存加密等
		支持云主机类型的删除
	云主机组
		支持(强制)亲和组、(强制)反亲和组、非强制亲和组、非强制反亲和组等调度策略的云主机组的管理，包括创建和删除
		支持云主机组内的云主机管理
	镜像
		支持通过管理页面进行镜像文件上传、支持通过URL进行镜像上传，支持通过sftp将镜像文件上传到服务器后通过命令行脚本进行镜像上传
		支持QCOW2、RAW、ISO等镜像格式
		支持创建镜像时，选择和设置操作系统类型、系统版本、镜像的默认用户、最小系统盘、最小内存、是否受保护
		支持创建镜像时，对镜像的访问范围进行控制，包括公有（所有项目可用）、私有（归属项目可用）、共享（列表项目可用）
		支持将镜像分栏展示，分为当前项目镜像、公有镜像、共享镜像、全部镜像
		支持创建镜像时，可选择镜像的使用类型，包括云主机、裸机等
		支持创建镜像时，设置镜像的高级属性，包括是否启用QGA、选择CPU策略、CPU线程策略等
		支持镜像编辑和删除，受保护的镜像禁止删除，需要先取消保护
		支持镜像的元数据管理，包括自定义元数据、OS类型、OS发行版、OS管理用户、OS密码、是否启用QGA、是否挂载云主机元数据光盘、看门狗、CPU拓扑、CPU模式、CPU绑核、随机数生成器、是否开启启动菜单、是否开启内存加密等
	秘钥
		支持创建秘钥、导入秘钥、下载私钥、查看公钥、删除秘钥
		支持通过秘钥ssh访问Linux云主机
	虚拟机管理器
		支持在虚拟机管理器的详情中，进行该计算节点上的虚拟机的查看和管理
		支持禁用和启用计算节点，在禁用时可填写禁用的原因，在计算节点列表处展示禁用的原因，被禁用的计算节点在新建云主机时会被调度屏蔽掉
	主机集合
		支持云主机集合，包括创建和删除云主机集合，给云主机集合添加和移除计算节点
		支持可用域，包括创建和删除可用域，给可用域添加和移除计算节点
		支持云主机集合和可用域的元数据管理，包括自定义元数据、计算节点能力、计算节点上最大云主机数量限制、IOPS最大值、磁盘超分系数等

## 存储
	云硬盘
		支持云硬盘的创建，选择和设置可用域、数据源、云硬盘类型、容量、名称
		支持云硬盘的批量创建，创建云硬盘时可指定批量创建的云硬盘数量，批量创建的云硬盘能够自动按序号命名
		支持创建空白云硬盘、基于镜像创建云硬盘、基于云硬盘快照创建云硬盘
		支持基于云硬盘创建云硬盘快照、基于云硬盘创建云硬盘备份、基于云硬盘创建镜像、基于云硬盘克隆云硬盘、基于云硬盘快照恢复云硬盘
		支持调整云硬盘是否可启动的属性，支持将云硬盘挂载到云主机
		支持系统管理员更改云硬盘的状态
		支持调整云硬盘的类型、支持对云硬盘进行扩容
		支持将云硬盘在项目间进行转让
		支持云硬盘的编辑和删除
	云硬盘备份
		支持云硬盘备份的创建，选择和设置名称、备份方式、来源的云硬盘，支持全量备份和增量备份
		支持基于硬盘备份的恢复
		支持云硬盘备份的编辑和删除
	云硬盘快照
		支持基云硬盘创建云硬盘快照
		支持基于硬盘快照创建云硬盘
		支持云硬盘快照的编辑和删除
	云硬盘类型
		支持云硬盘类型的访问管理，可设置为公有（所有项目可用）、私有（限定可用的项目列表）
		支持云硬盘类型的QoS控制，可设置控制点在前端、后端或前后端，可设置读IOPS、写IOPS、总IOPS、读带宽、写带宽、总带宽等控制指标
		支持云硬盘类型的加密配置
		支持云硬盘类型的编辑和删除
	存储后端
		支持列表展示存储后端，包括名称、协议、后端名称，以及存储已用量和总量

## 网络
	网络
		支持租户网络的创建，设置网络名称、描述、MTU、是否共享、是否启用端口安全，可选随创建网络一并创建子网
		支持系统管理员创建供应商网络，设置网络名称、描述、MTU、是否共享、是否启用端口安全、是否外部网络，可选随创建网络一并创建子网，供应商网络的类型包括vlan、vxlan、flat、gre
		支持将网络分栏展示，分为当前项目网络、共享网络、外部网络、所有网络
		支持网络编辑，包括名称、描述、会否共享、是否启用端口安全
		支持网络的子网管理，包括子网的创建、编辑和删除，支持IPv4子网和IPv6子网，支持配置子网名称、地址段、地址池、是否启用DHCP、是否启用网关、网关地址、DNS、主机路由
		支持网络的编辑和删除
	端口
		支持虚拟网卡的创建，选择和设置名称、描述、所属网络、自动分配或手工指定MAC地址、是否启用端口安全、安全组、QoS策略
		支持给虚拟网卡绑定浮动IP
		支持虚拟网卡的QoS策略配置，禁用QoS策略或关联选择QoS策略
		支持虚拟网卡的安全组配置，禁用端口安全或关联选择安全组
		支持虚拟网卡的编辑，包括编辑名称、描述、自动分配或手工指定MAC地址，支持虚拟网卡的删除
	QoS策略
		支持网络QoS策略控制，可设置出方向、入方向的带宽限制和突发带宽限制
		支持将网络QoS分栏展示，分为当前项目QoS策略、共享QoS策略、所有QoS策略
		支持网络QoS策略的编辑和删除
	路由器
		支持虚拟路由器的创建，选择和设置名称、描述、是否开启公网网关、关联的外部网络
		支持虚拟路由器开启公网网关，接通与外部网络的连接
		支持虚拟路由器关闭公网网关，断开与外部网络的连接
		支持虚拟路由器连接虚拟网络的子网，支持断开与子网的连接
		支持虚拟路由器的编辑和删除
	浮动IP
		支持浮动IP的申请，选择外部供应商网络、子网、关联的网络QoS策略，支持批量申请，支持指定浮动IP地址申请
		支持将浮动IP关联到指定云主机的指定虚拟网卡，将浮动IP直接关联到虚拟网卡
		支持浮动IP的编辑，包括描述和调整网络QoS，支持浮动IP的释放
	网络拓扑
		支持项目的网络拓扑图展示，包括网络、路由器、云主机等，选中路由器和云主机时展示基本信息
		支持选择网络拓扑上是否展示云主机，支持路由器、网络、云主机的快速创建按钮
	安全组
		支持安全组的创建，安全规则的创建和删除管理
		支持按照协议（TCP、UDP、ICMP、其他）、流量方向（入口或出口）、以太网类型（IPv4或IPv6）、端口范围、远端方式（CIDR或安全组）创建安全规则
		支持系统默认安全组，在项目创建时，系统会为新项目自动生成默认安全组
		支持安全组的编辑和删除

## 身份管理
	域
		支持域的创建，项目、用户和用户组均归属于域，在用户登录时需要填写所登录的域
		支持系统默认域，且不可删除
		支持域的编辑、启用、禁用和删除
	项目
		支持项目的创建，选择和设置名称、描述、所属的域、是否启用
		支持项目的配额管理，包括计算资源配额、网络资源配额、存储资源配额
		支持创建各种资源对象时动态计算和展示项目的配额使用情况、总量情况
		支持项目内用户和用户组的管理，将用户、用户组添加到项目时可设置其项目角色
		支持项目的启用和禁用
		支持给项目打标签
		支持项目的编辑和删除
	用户
		支持用户的创建，选择和设置用户名称、描述、密码、姓名、邮箱、手机号、是否启用、所属的域
		支持创建用户时，选择用户所加入的项目及项目角色，选择用户所加入的用户组
		支持用户的系统角色设置，包括管理员角色或者只读角色
		支持用户密码的修改
		支持用户的启用和禁用
		支持用户的编辑和删除
	用户组
		支持用户组的创建，选择和设置名称、描述、所属的域
		支持用户组内的用户成员的管理，添加用户、移除用户
		支持用户组的编辑和删除
	角色
		支持角色的创建、编辑和删除
		支持系统默认角色，且不可编辑和删除

## 监控中心
	监控概览
		支持展示CPU、内存使用率超门限告警、展示最近一周告警趋势
		支持展示CPU、内存、存储的资源使用量
		支持展示计算节点的状态
		支持展示Top3的主机CPU利用率、内存利用率、读写存储IOPS、收发网络流量
		支持展示存储集群的状态、资源使用率、IOPS
	物理节点
		支持展示节点的CPU核数、总内存大小、系统运行时长、文件系统可用空间
		支持展示节点的CPU利用率、内存用量、各磁盘的IOPS、各磁盘的空间利用率、系统负载
		支持展示节点的网络流量、TCP连接数、网络错误数、网络丢包率
	存储集群
		支持展示存储集群状态、MON/PG/OSD的数量和状态、存储集群的使用率
		支持展示存储池的容量使用情况、OSD延迟、IOPS、带宽
		支持存储池列表展示、OSD列表展示
	OpenStack服务
		支持展示OpenStack的计算、网络、存储服务状态
		支持展示数据库服务、消息服务、缓存服务的状态
	其他服务
		支持数据库服务的详情展示，包括已连接的线程、慢查询、线程活动趋势、MySQL操作数趋势
		支持缓存服务的详情展示，包括当前连接数趋势、连接总数趋势、读/写/删趋势、缓存条目数趋势
		支持消息服务的详情展示，包括服务状态、已连接的线程、队列/交换/消费者总数、消息收发趋势、通道数趋势

## 平台配置
	系统信息
		支持OpenStack的系统服务接入点的列表展示
		支持计算、网络、存储在各节点上服务状态展示，可以对服务进行禁用和启用
	系统配置
		支持系统配置信息的查看和修改，包括云主机类型、GPU型号
	元数据定义
		支持导入新的元数据定义
		支持编辑云数据定义是否公有、是否受保护
	许可证
		支持许可证的申请和导入
		支持对管理的计算节点服务器数量进行授权许可