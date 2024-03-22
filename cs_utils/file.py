import os
import base64
import configparser


def add_suffix_to_file(filepath, suffix, connector='-'):
    # 拆分文件路径和文件名
    filepath = os.path.abspath(filepath)
    dirname, filename = os.path.split(filepath)

    # 拆分文件名和后缀
    basename, extension = os.path.splitext(filename)

    # 添加后缀
    new_basename = f"{basename}{connector}{suffix}"

    # 重组文件名和后缀
    new_filename = f"{new_basename}{extension}"

    # 重组文件路径和文件名
    new_filepath = os.path.join(dirname, new_filename)

    return new_filepath


def read_yaml(filepath) -> dict:
    import yaml
    with open(filepath, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data


def read_ini(filepath) -> dict:
    config = configparser.ConfigParser()
    config.read(filepath)
    return config


def read_file_list(filepath, mode='rb') -> list:
    with open(filepath, mode=mode) as f:
        content = f.readlines()
    return content


def read_file_content(filepath, mode='rb', encoding='utf-8') -> str:
    with open(filepath, mode=mode, encoding=encoding) as f:
        content = f.read()
    return content


def write_file_content(filepath, content, mode='w'):
    with open(filepath, mode=mode) as f:
        content = f.write(content)


def write_file_list(contents: list, filepath, mode='wb'):
    with open(filepath, mode=mode) as f:
        f.writelines(contents)


def ini_obj_to_dict(config) -> dict:
    assert isinstance(config, configparser.RawConfigParser), f'ini_obj_to_dict input need be config, but is {type(config)}'
    ini_dict = {}
    for section in config.sections():
        ini_dict[section] = {}
        for option in config.options(section):
            value = config.get(section, option)
            ini_dict[section][option] = value
    if config.defaults():
        ini_dict['DEFAULT'] = config.defaults()
    return ini_dict


def ini_string_to_dict(config_string):
    assert isinstance(config_string, str), f'ini_string_to_dict input need be str, but is {type(config_string)}'
    decoded_bytes = base64.b64decode(config_string)
    buf = decoded_bytes.decode()
    config = configparser.RawConfigParser()
    config.read_string(buf)
    return ini_obj_to_dict(config)


def ini_file_to_dict(file_path, strict=True):
    config = configparser.RawConfigParser(strict=strict)
    config.read(file_path)
    return ini_obj_to_dict(config)
