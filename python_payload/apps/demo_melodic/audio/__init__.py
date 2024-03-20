
import bl00mbox
import os
import sys

class AudioModuleCollection:
    def __init__(self, name, app_path, sub_paths = None):
        self.module_list = []
        if sub_paths is None:
            sub_paths = f"/modules/{name}/"
        if type(sub_paths) == str:
            sub_paths = [sub_paths]
        self.name = name
        self.sub_paths = sub_paths
        self.app_path = app_path

    def update(self):
        modules = []
        module_paths = ["/".join([self.app_path, s]) for s in self.sub_paths]
        path = list(sys.path)

        for module_path in module_paths:
            # relative imports don't work so we have to jump hoops
            sys.path.append(self.app_path)
            sys.path.append(module_path)
            module_files = os.listdir(module_path)
            module_files = [
                x[:-3] for x in module_files if x.endswith(".py") and not x.startswith("_")
            ]
            for module_file in module_files:
                try:
                    mod = __import__(module_file)
                    for attrname in dir(mod):
                        if attrname.startswith("_") or attrname in [
                            "bl00mbox",
                            "center_notch",
                        ]:
                            continue
                        attr = getattr(mod, attrname, None)
                        if isinstance(attr, type) and issubclass(attr, bl00mbox.Patch) and attr not in modules:
                            print(f"module collection {self.name}: discovered {attrname} in {module_file}.py")
                            modules += [attr]
                except:
                    print("failed to import " + module_file + ".py")

            # can't write directly
            sys.path.clear()
            for p in path:
                sys.path.append(p)

        self.module_list = list(set(modules))

    def _get_module_data_by_name(self, name):
        module_index = None
        module_type = None
        for x, module_t in enumerate(module_list):
            if module_t.name == name:
                module_type = module_t
                module_index = x
                break
        return module_index, module_type

    def get_module_index_by_name(self, name):
        ret, _ = self._get_module_data_by_name(name)
        return ret

    def get_module_by_name(self, name):
        _, ret = self._get_module_data_by_name(name)
        return ret
