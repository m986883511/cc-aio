import logging

from cs_utils import func

LOG = logging.getLogger(__name__)


def get_hostrpc_what_error(err_msg: str, dec=''):
    if 'connection refused' in err_msg.lower():
        result = 'hostrpc服务无法连接, 请检查hostrpc.service服务状态'
    elif 'Server error:' in err_msg:
        if 'completed' in err_msg.lower():
            temp = func.get_string_split_list(err_msg, split_flag='Exception:')[-1]
            result = f'命令执行报错, 错误:{temp}'
        else:
            temp = func.get_string_split_list(err_msg, split_flag='Server error:')[-1]
            result = f'代码执行报错, 错误:{temp}'
    else:
        result = f'未知报错, 请联系开发者, 原始错误:{err_msg}'
    
    if dec:
        result = f'{result}, 补充说明:{dec}'
    LOG.error(result)
    return result
