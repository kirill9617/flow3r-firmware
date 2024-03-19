import os


def dicts_match_recursive(dict1, dict2):
    return dict_contains_dict(dict1, dict2) and dict_contains_dict(dict2, dict1)


def dict_contains_dict(container, containee):
    for key in containee:
        if key not in container:
            return False
        elif isinstance(containee[key], dict):
            if not dict_contains_dict(container[key], containee[key]):
                return False
        elif container[key] != containee[key]:
            # print(f"change in {key} from {container[key]} to {containee[key]}")
            return False
    return True


def fakemakedirs(path, exist_ok=False):
    # ugh
    dirs = path.strip("/").split("/")
    path_acc = ""
    exists = True
    for d in dirs:
        path_acc += "/" + d
        if not os.path.exists(path_acc):
            exists = False
            os.mkdir(path_acc)
    if exists and not exist_ok:
        raise OSError("exist_not_ok!!")
