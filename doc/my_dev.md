下载离线包
```shell
apt-get --download-only install python3-pip
ls /var/cache/apt/archives/
```

我的push
```shell
export http_proxy='socks5://192.168.1.31:1080'
export https_proxy='socks5://192.168.1.31:1080'
git push https://m986883511:$GITHUB_TOKEN@github.com/m986883511/cc-aio.git
```