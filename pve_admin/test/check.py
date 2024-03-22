from pve_admin import business
from pve_admin import pve_cli

def check_lost_func():
    all_end_points = [name for name in dir(business) if name.endswith('EndPoint')]
    all_cli_func_names = [name for name in dir(pve_cli) if callable(getattr(pve_cli, name))]
    flag = True
    for endpoint in all_end_points:
        MyClass = getattr(business, endpoint)
        # print(MyClass)
        method_names = [name for name in dir(MyClass) if callable(getattr(MyClass, name)) and not name.startswith("_")]
        # print(method_names)
        for method_name in method_names:
            if method_name not in all_cli_func_names:
                flag = False
                err_msg = f'{method_name} in {endpoint} but not in pve_cli, check it!'
                print(err_msg)
    if flag:
        msg = f'not found lost functions, check successfully'
        print(msg)

if __name__ == '__main__':
    check_lost_func()
