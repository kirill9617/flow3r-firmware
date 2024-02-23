import bl00mbox
import os
import sys

osc_list = []


def update_oscs(app_path, osc_paths=[]):
    oscs = []
    if type(osc_paths) is str:
        osc_paths = [osc_paths]
    osc_paths += [app_path + "/audio/oscs"]
    path = list(sys.path)

    for osc_path in osc_paths:
        # relative imports don't work so we have to jump hoops
        sys.path.append(app_path)
        sys.path.append(osc_path)
        osc_files = os.listdir(osc_path)
        osc_files = [
            x[:-3] for x in osc_files if x.endswith(".py") and not x.startswith("_")
        ]
        for osc_file in osc_files:
            try:
                mod = __import__(osc_file)
                for attrname in dir(mod):
                    if attrname.startswith("_") or attrname in [
                        "bl00mbox",
                        "center_notch",
                    ]:
                        continue
                    attr = getattr(mod, attrname, None)
                    if isinstance(attr, type) and issubclass(attr, bl00mbox.Patch):
                        print(
                            "discovered oscillator in " + osc_file + ".py: " + attrname
                        )
                        oscs += [attr]
            except:
                print("failed to import " + osc_file + ".py")

        # can't write directly
        sys.path.clear()
        for p in path:
            sys.path.append(p)

    global osc_list
    osc_list = list(set(oscs))


def get_osc_by_name(name):
    osc_type = None
    for osc_t in osc_list:
        if osc_t.name == name:
            osc_type = osc_t
            break
    return osc_type
