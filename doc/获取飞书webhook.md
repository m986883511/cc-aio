#feishu

下载windows客户端 [下载飞书 App 及桌面客户端 - 飞书官网 (feishu.cn)](https://www.feishu.cn/download) （手机飞书无法获取webhook）

安装过程省略。。。

![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531193816-tmp.png)

群名称写一下
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531193905-tmp.png)


点击右上角的三个点，再点击设置
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194033-tmp.png)


点击群机器人
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194214-tmp.png)

点击添加机器人
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194255-tmp.png)


点击自定义机器人
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194316-tmp.png)


设置下机器人人名称和描述，点击添加
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194409-tmp.png)

勾选仅群主，点击复制按钮，点击完成
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194511-tmp.png)


安全设置没啥用，你不泄露就好，点击暂不配置就好
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194617-tmp.png)


可以看到群众有一个机器人了
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531194840-tmp.png)

刚刚的webhook为
```shell
https://open.feishu.cn/open-apis/bot/v2/hook/2a08a648-20cc-42a1-b897-059db9d2ab4c
```

将最后的那个uud复制下来，填到cc-aio的配置文件中， 可以使用下面的命令设置上去，记得用你的uuid
```shell
crudini --set /etc/cc/aio.conf public_ip feishu_webhook_uuid 2a08a648-20cc-42a1-b897-059db9d2ab4c
```

试一试把，执行这两个命令，将立即发送一次公网ip到你的群里
```shell
rm -rf /tmp/public_ip.txt
/usr/local/bin/report_public_ip_if_changed_robot.sh
```

群里收到了你的公网ip
![image.png](https://gitee.com/m986883511/picture-bed/raw/master/PyPicGo/cs-20240531195534-tmp.png)
