#!/usr/bin/env python3

import importlib
import importlib.abc
import importlib.machinery
from importlib.machinery import PathFinder, BuiltinImporter
import importlib.util
import os
import sys
import builtins
import argparse
import traceback


projectpath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

import random
import pygame
import cmath
import gzip
import wasmer
import wasmer_compiler_cranelift

try:
    import config
except:
    pass

try:
    import requests
except ImportError:
    print("Warning: `requests` is missing so no `urequests` mock will exist")

try:
    import mad
except ImportError:
    print("Warning: `mad` is missing, MP3 support in `media` mock will be limited")

sys_path_orig = sys.path


class UnderscoreFinder(importlib.abc.MetaPathFinder):
    def __init__(self, builtin, pathfinder):
        self.builtin = builtin
        self.pathfinder = pathfinder

    def find_spec(self, fullname, path, target=None):
        if fullname == "_time":
            return self.builtin.find_spec("time", path, target)
        if fullname in ["random", "math"]:
            return self.builtin.find_spec(fullname, path, target)
        if fullname in ["json", "tarfile"]:
            sys_path_saved = sys.path
            sys.path = sys_path_orig
            res = self.pathfinder.find_spec(fullname, path, target)
            sys.path = sys_path_saved
            return res


# sys.meta_path.insert(0, Hook())

sys.path = [
    os.path.join(projectpath, "sim", "fakes"),
    os.path.join(projectpath, "python_payload"),
    os.path.join(projectpath, "components", "micropython", "frozen"),
]

builtin = BuiltinImporter()
pathfinder = PathFinder()
underscore = UnderscoreFinder(builtin, pathfinder)
sys.meta_path = [pathfinder, underscore]

# Clean up whatever might have already been imported as `time`.
import time

importlib.reload(time)

sys.path_importer_cache.clear()
importlib.invalidate_caches()

sys.modules["time"] = time

simpath = "/tmp/flow3r-sim"
print(f"Using {simpath} as /flash mount")
try:
    os.mkdir(simpath)
except:
    pass


def _path_replace(p):
    if p.startswith("/flash/sys"):
        p = p[len("/flash/sys") :]
        p = projectpath + "/python_payload" + p
        return p
    if p.startswith("/flash"):
        p = p[len("/flash") :]
        p = simpath + p
        return p

    return p


def _mkmock(fun):
    orig = fun

    def _wrap(path, *args, **kwargs):
        path = _path_replace(path)
        return orig(path, *args, **kwargs)

    return _wrap


def _mkmock2(fun):
    orig = fun

    def _wrap(path1, path2, *args, **kwargs):
        path1 = _path_replace(path1)
        path2 = _path_replace(path2)
        return orig(path1, path2, *args, **kwargs)

    return _wrap


os.listdir = _mkmock(os.listdir)
os.rename = _mkmock2(os.rename)
os.stat = _mkmock(os.stat)
os.statvfs = _mkmock(os.statvfs)
os.mkdir = _mkmock(os.mkdir)
os.rmdir = _mkmock(os.rmdir)
os.unlink = _mkmock(os.unlink)
os.remove = _mkmock(os.remove)
builtins.open = _mkmock(builtins.open)

orig_stat = os.stat


def _stat(path):
    res = orig_stat(path)
    # lmao
    return os.stat_result((res.st_mode, 0, 0, 0, 0, 0, res.st_size, 0, res.st_mtime, 0))


os.stat = _stat


sys.print_exception = lambda x: print(traceback.format_exc())


def sim_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--screenshot",
        action="store_true",
        default=False,
        help="Generate a flow3r.png screenshot.",
    )
    parser.add_argument(
        "--full-screen",
        dest="full_screen",
        action="store_true",
        default=False,
        help="Run the simulator as full-screen OLED display.",
    )
    parser.add_argument("--oled-size", dest="oled_size", default=240)
    parser.add_argument("--oled-aspect", dest="oled_aspect", default=1)
    parser.add_argument("--oled-scale", dest="oled_scale", default=1)
    parser.add_argument(
        "override_app",
        nargs="?",
        help="Bundle to start instead of the main menu. "
        + "This is the `app.name` from flow3r.toml.",
    )
    args = parser.parse_args()

    os.environ["SIM_FULL_SCREEN"] = "1" if args.full_screen else "0"
    os.environ["SIM_OLED_SIZE"] = str(args.oled_size)
    os.environ["SIM_OLED_ASPECT"] = str(args.oled_aspect)
    os.environ["SIM_OLED_SCALE"] = str(args.oled_scale)
    import _sim

    _sim.SCREENSHOT = args.screenshot

    if args.override_app is not None:
        import st3m.run

        st3m.run.override_main_app = args.override_app

    import main


if __name__ == "__main__":
    sim_main()
