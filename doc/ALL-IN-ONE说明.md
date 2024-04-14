#cc-aio #doc 

# 快速访问

| 什么        | 地址                           |
| --------- | ---------------------------- |
| pve管理界面   | http://YOUR_PVE_ADDRESS:8006 |
| alist管理界面 | http://YOUR_PVE_ADDRESS:5244 |

# 摘要

## 前言

当前零刻，铭凡等众多小主机越来越多，功耗也不高，非常适合做一台家用的服务器。当一个下载机，htpc，smb服务器，文件服务器，科学上网代理是一个很好的选择。例如性价比之王，零刻SER5 Pro 5800H为例，我将以此为例搭建all-in-one服务器。

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409094024-tmp.png)

## 网络架构图
```text
                  +-----------+
                  |   互联网   |
                  +-----+-----+
                        |
+--------+        +-----+----+        +---------------+
| 交换机  |        | 运营商光猫 |        |好点的无线路由器  |
|        |--------| 关闭无线网 |--------|关闭DHCP纯AP使用 |
+--+--+--+        +----------+        +-----+---------+
   |  |                                     |
   |  +------------+                        |
   |               |                        |
+------------+  +--+----------+       +-----+------+
| PVE        |  |电视，台式电脑 |       |手机平板笔记本 |
| all-in-one |  |各种有线设备   |       |各种无线设备  |
+------------+  +-------------+       +------------+
```

## 实现目标

1. 5分钟搞定源设置，samba存储，alist网盘，vpn部署，ddns，dns设置，删除local-lvm，grub修改，硬盘格式化和挂载smb
2. 机器内的物理sata盘作为共享盘使用
3. 核显直通

我的all-in-one方案，参考网络架构图，会发现与别人有所不同，结构很简单

### 主要区别

| 区别         | 别人用的原因                             | 我不用的原因                                                    |
| ---------- | ---------------------------------- | --------------------------------------------------------- |
| 没有爱快       | 光猫改为桥接，由爱快实现拨号，并在爱快里面获取公网ip，实现ddns | 光猫不动正常拨号，公网地址在pve上以服务获取，ddns在pve上以服务实现                    |
| 光猫不改桥接     | 让爱快来当主路由                           | 怕boom，家里断网                                                |
| 没有黑群晖      | 当存储了                               | 一块硬盘还套一层黑群晖，boom了之后，读取数据还是得靠linux指令，不如直接挂载到samba，boom了也不怕 |
| 没有jellyfin | 影音播放管理                             | 不喜欢看管理界面，我没几个电影资源要管理的，我用网络播放器直接播放samba存储里面的               |
| 公网ip绑定到nas | 在外面直接访问家里nas的资料                    | 把nas暴露在公网是很危险的行为，看过有人中招被锁nas资料了                           |
|            |                                    |                                                           |

### 方案优点

| 优点         | 原因                                           |
| ---------- | -------------------------------------------- |
| 网络很稳       | 没动运营商路由器，网络很稳                                |
| sata硬盘数据很稳 | 除非硬盘坏了，不然随便接到个linux都能读出里面的数据                 |
| 共享数据方便     | sata硬盘的数据挂载到samba，可以共享给所有的虚拟机以及你的实体笔记本，电视机等  |
| 外面访问家里设备方便 | 我用公网ip为你搭建了VPN隧道，数据安全，当然也能访问nas数据了           |
| ==安装方便快捷== | 如果不要核显直通，5分钟就能部署完成，加上核显直通也就15分钟（拷贝文件费时间）     |
| 依赖设备少      | 不要爱快前置路由，没有交换机pve直接接到路由器也没问题，无线路由器不改纯AP问题也不大 |

# 功能介绍

## cc-aio

由B站UP主吵吵博士开发的all-in-one部署工具，只支持pve8.1版本！（我用的是8.1.4）旨在快速搭建好PVE的ALL-IN-ONE场景，cc是吵吵的缩写，aio是ALL-IN-ONE的缩写，通过ssh登录到pve节点，然后输入

先安装版本
```shell
bash cc-aio-1.999.xx.bin
```

即可打开操作界面，用方向键操作，也可以用鼠标点击
```shell
cc-aio
```

宗旨：把用户当傻子，减少一切用户输入命令，编辑文件的操作

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409114506-tmp.png)

### ALL-IN-ONE服务
服务的意思是他是以守护进程或者cron定时任务形式
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409115229-tmp.png)

### ALL-IN-ONE配置

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409124120-tmp.png)
## 共享存储

由samba一起实现，通过把独立的sata3硬盘挂载到smb服务中，你将获得一个超大的共享存储！

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409123758-tmp.png)

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409123951-tmp.png)

## 浏览器网盘

通过alist实现，你还可以接入第三方的网盘，能实现浏览器上看视频、文档

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409123601-tmp.png)

## 公网ip

这里的公网ip是运营商给到家庭的临时公网ip地址，所以才需要开启变更检查服务。
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409115307-tmp.png)

### 用ipv4还是ipv6

==一句话，尽量使用ipv4！==

| 区别   | 公网ipv4                       | 公网ipv6             |
| ---- | ---------------------------- | ------------------ |
| 获取难度 | 只有电信和联通有，但也是早2年办理的宽带才会有      | 轻松获取，但需要超级管理员密码    |
| 安全   | 通过端口映射给wireguard实现vpn，没有安全问题 | 家中所有设备都将暴露公网，有安全问题 |

超级管理员密码获取方式：问客服要，不给就去烦安装师傅。

这是pve的桥接口，这个240开头的就是公网ipv6地址。
```shell
root@host056:~# ip a s vmbr0
5: vmbr0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 7c:83:34:b9:d1:e3 brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.56/24 scope global vmbr0
       valid_lft forever preferred_lft forever
    inet6 240e:3a1:c58:****:7e83:34ff:feb9:d1e3/64 scope global dynamic mngtmpaddr
       valid_lft 259171sec preferred_lft 172771sec
    inet6 fe80::7e83:34ff:feb9:d1e3/64 scope link
       valid_lft forever preferred_lft forever
```

若你使用临时公网ipv6，你家所有的设备都会分到公网ipv6地址，而且防火墙等级改为低了，等于你家所有的设备都暴露在公网了，会有安全问题，你需要安全加固。针对性的安全加固请联系B站UP主吵吵博士。

## VPN隧道

玩笑话：会搭vpn隧道的起码也是高玩了，而现在居然可以自动部署了！

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409121818-tmp.png)

用到的技术是wireguard，比zerotier，ipsec等等速度都要快，非对称加密，绝对安全！在公司ping家里的路由器延迟5-10个毫秒！！！

有手机和电脑客户端，建立链接后，直接可以访问家里的局域网中的所有设备。

需要我向你演示在外面用低功耗13寸轻薄笔记本，连接家里直通显卡的虚拟机，玩csgo吗？

## 硬盘配置

目前提供了格式化和挂载的配置
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409125505-tmp.png)

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409125518-tmp.png)


## 核显配置

目前仅支持amd的cpu，如果我的版本没有内置你的rom文件，你也可以自己填写，如果成功直通，还希望你能共享出来，我集成进版本中，方便其他人
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240409125602-tmp.png)

配置直通和删除直通都只能在虚拟机stopped的状态下操作，将自动为你设置hostpci的配置。
# 未支持功能

- [ ] pve8.1上windows核显直通会遇到q35的问题，没搞定
- [ ] 主机名修改后，repair指令未实现
- [ ] 家用nvidia显卡的vgpu实现

# 鸣谢

| name      | 链接                                                     | 说明               |
| --------- | ------------------------------------------------------ | ---------------- |
| 爱折腾的老高    | [B站主页](https://space.bilibili.com/455976991)           | 直通核显教程视频         |
| 李晓流       | [B站主页](https://space.bilibili.com/565938745)           | intel4-13直通rom文件 |
| gangqizai | [仓库地址](https://github.com/gangqizai/igd)               | intel12代以上直通文件   |
| angristan | [仓库地址](https://github.com/angristan/wireguard-install) | wireguard快速部署脚本  |
| alist-org | [仓库地址](https://github.com/alist-org/alist)             | alist快速部署脚本      |
| ivanhao   | [仓库地址](https://github.com/ivanhao/pvetools)            | pvetools工具    |
