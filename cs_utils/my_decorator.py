def only_run_once(func):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            wrapper.result = func(*args, **kwargs)
        return wrapper.result

    wrapper.has_run = False
    wrapper.result = None
    return wrapper


@only_run_once
def my_func():
    print("This function will only execute once.")
    return 42


if __name__ == '__main__':
    print(my_func())  # Output: This function will only execute once. 42
    print(my_func())  # Output: 42
