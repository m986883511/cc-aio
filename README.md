## 说明

目前已经支持pve的7.4和8.1版本，我在7.4-3和8.1.4上测试通过。

## 使用说明
下载安装，下载地址请从qq群内(776589605)获取最新，github的release更新可能不及时。

解压压缩包，然后执行：
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
1. bin 做cc-aio.bin版本包的
2. cc_driver 驱动
3. cc_utils 通用函数
4. hostadmin click写的命令行代码，jsonrpclib提供rpc接口
5. pvetui urwid写的tui界面，提供用户交互

