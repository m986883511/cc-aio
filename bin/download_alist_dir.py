#!/usr/bin/env python
import argparse
import os
import copy
import json
import subprocess
import logging
from urllib import request, parse

import download_alist

def get_string_split_list(string, split_flag=','):
    return [i.strip() for i in string.split(split_flag) if i.strip()]


class DownloadDebs():

    def __init__(self, alist_url, download_txt_path, save_dir):
        self.alist_url = alist_url
        self.download_txt_path = download_txt_path
        self.save_dir = save_dir
        self.deb_dict = self.read_deb_txt()

    def read_deb_txt(self):
        with open(self.download_txt_path) as f:
            content_list = f.readlines()
        
        content_list = [i.strip() for i in content_list if i.strip()]
        deb_dict = {}
        temp_list=[]
        name=''
        for line in content_list:
            if line.startswith('#'):
                if name:
                    deb_dict[name] = temp_list
                    temp_list = []
                name=line[1:]
            else:
                temp_list.append(line)
        deb_dict[name] = temp_list
        return deb_dict
    
    def download_debs(self):
        for name, deb_list in self.deb_dict.items():
            deb_list = [parse.quote(file) for file in deb_list]
            alist_url = f'{self.alist_url}/{name}'
            urls = download_alist.get_download_file_urls(alist_url, deb_list)
            download_alist.use_wget_download(urls, self.save_dir)


def check_path_exist(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Invalid path: {path} is not exist!")
    return path


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('alist_url', help='alist url', type=download_alist.validate_alist_url)
    parser.add_argument('download_txt_path', help='download.txt path', type=check_path_exist)
    parser.add_argument('save_dir', help='save dir', type=check_path_exist)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_arguments()
    print(f'args is {args}')
    dd = DownloadDebs(args.alist_url, args.download_txt_path, args.save_dir)
    dd.download_debs()
 