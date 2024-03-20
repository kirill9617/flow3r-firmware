import bl00mbox
import os
import sys

fx_list = []

def update_fx(app_path, fx_paths=[]):
    fx = []
    if type(fx_paths) is str:
        fx_paths = [fx_paths]
    fx_paths += [app_path + "/audio/fx"]
    path = list(sys.path)

    for fx_path in fx_paths:
        # relative imports don't work so we have to jump hoops
        sys.path.append(app_path)
        sys.path.append(fx_path)
        fx_files = os.listdir(fx_path)
        fx_files = [
            x[:-3] for x in fx_files if x.endswith(".py") and not x.startswith("_")
        ]
        for fx_file in fx_files:
            try:
                mod = __import__(fx_file)
                for attrname in dir(mod):
                    if attrname.startswith("_") or attrname in [
                        "bl00mbox",
                        "center_notch",
                    ]:
                        continue
                    attr = getattr(mod, attrname, None)
                    if isinstance(attr, type) and issubclass(attr, bl00mbox.Patch):
                        print(
                            "discovered fx unit in " + fx_file + ".py: " + attrname
                        )
                        fx += [attr]
            except:
                print("failed to import " + fx_file + ".py")

        # can't write directly
        sys.path.clear()
        for p in path:
            sys.path.append(p)

    global fx_list
    fx_list = list(set(fx))


def get_fx_by_name(name):
    fx_type = None
    for fx_t in fx_list:
        if fx_t.name == name:
            fx_type = fx_t
            break
    return fx_type
