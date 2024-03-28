FROM debian:12
RUN apt update
RUN apt install ca-certificates -y
RUN rm -rf /etc/apt/sources.list.d
RUN echo 'deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free\n\
deb-src https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free\n\
deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free\n\
deb-src https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free\n\
deb https://mirrors.ustc.edu.cn/debian/ bookworm-backports main contrib non-free\n\
deb-src https://mirrors.ustc.edu.cn/debian/ bookworm-backports main contrib non-free\n\
deb https://mirrors.ustc.edu.cn/debian-security/ stable-security main contrib non-free\n\
deb-src https://mirrors.ustc.edu.cn/debian-security/ stable-security main contrib non-free\n'\
> /etc/apt/sources.list
RUN apt update
RUN apt install dpkg-dev -y
RUN echo 'dpkg-scanpackages /tmp/apt/ /dev/null | gzip> /tmp/apt/Packages.gz' > /generate_apt_source.sh
# docker build -f dpkg-dev_debian.dockerfile -t debian:dpkg-dev --network host .
