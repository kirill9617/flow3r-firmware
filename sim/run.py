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


projectpath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

import random
import pygame
import cmath
import wasmer
import wasmer_compiler_cranelift

try:
    import requests
except ImportError:
    print("Warning: `requests` is missing so no `urequests` mock will exist")


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
    os.path.join(projectpath, "python_payload"),
    os.path.join(projectpath, "components", "micropython", "frozen"),
    os.path.join(projectpath, "sim", "fakes"),
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


os.listdir = _mkmock(os.listdir)
os.stat = _mkmock(os.stat)
builtins.open = _mkmock(builtins.open)

orig_stat = os.stat


def _stat(path):
    res = orig_stat(path)
    # lmao
    return os.stat_result((res.st_mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))


os.stat = _stat


def sim_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--screenshot",
        action="store_true",
        default=False,
        help="Generate a flow3r.png screenshot.",
    )
    parser.add_argument(
        "override_app",
        nargs="?",
        help="Bundle to start instead of the main menu. "
        + "This is the `app.name` from flow3r.toml.",
    )
    args = parser.parse_args()

    import _sim

    _sim.SCREENSHOT = args.screenshot

    if args.override_app is not None:
        import st3m.run

        st3m.run.override_main_app = args.override_app

    import main


if __name__ == "__main__":
    sim_main()
