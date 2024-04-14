## 说明
这是出版本包的项目。会下载很多文件，并通过makeself打成一个bin包

目前只能支持pve8.1版本，我使用的是最新的8.1.4，建议和我一样。

## 使用说明
下载安装，下载地址请从群内获取最新，github的release更新可能不及时。
```shell
bash cc-aio-*.bin
```

然后使用`cc-aio`通过界面操作
```shell
cc-aio
```

视频演示： https://www.bilibili.com/video/BV1mx4y1h7E8/

文档参考： [ALL-IN-ONE说明](doc/ALL-IN-ONE说明.md)

### 目录说明
bin 做cc-aio.bin版本包的
cc_driver 驱动
cc_utils 通用函数
hostadmin click写的命令行代码，jsonrpclib提供rpc接口

