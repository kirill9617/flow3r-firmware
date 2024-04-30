from st3m.ui.view import (
    BaseView,
    ViewTransitionSwipeLeft,
    ViewManager,
)
from st3m.ui.menu import MenuItem
from st3m.input import InputState
import st3m.wifi
from st3m.goose import Optional, List, Dict
from st3m.logging import Log
from st3m.utils import is_simulator
from st3m import settings
from ctx import Context
import leds
import time
import json

import toml
import io
import os
import os.path
import stat
import sys
import random
import time
from math import sin

log = Log(__name__)


class ApplicationContext:
    """
    Container for application context.

    Further envisioned are: path to bundle data,
    path to a data directory, etc...
    """

    _bundle_path: str
    _bundle_metadata: dict

    def __init__(self, bundle_path: str = "", bundle_metadata: dict = None) -> None:
        self._bundle_path = bundle_path
        self._bundle_metadata = bundle_metadata

    @property
    def bundle_path(self) -> str:
        return self._bundle_path

    @property
    def bundle_metadata(self) -> str:
        return self._bundle_metadata


def setup_for_app(app_ctx: Optional[ApplicationContext]) -> None:
    if app_ctx and app_ctx.bundle_metadata and settings.onoff_wifi_preference.value:
        wifi_preference = app_ctx.bundle_metadata["app"].get("wifi_preference")
        if wifi_preference is True and not st3m.wifi.is_connected():
            st3m.wifi.setup_wifi()
        elif wifi_preference is False:
            st3m.wifi.disable()
    leds.set_slew_rate(settings.num_leds_speed.value)


class Application(BaseView):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        self.app_ctx = self._app_ctx = app_ctx
        super().__init__()


class BundleLoadException(BaseException):
    MSG = "failed to load"

    def __init__(
        self, msg: Optional[str] = None, orig_exc: Optional[Exception] = None
    ) -> None:
        res = self.MSG
        if msg is not None:
            res += ": " + msg
        self.msg = res
        self.orig_exc = orig_exc
        super().__init__(res)


class BundleMetadataNotFound(BundleLoadException):
    MSG = "flow3r.toml not found"


class BundleMetadataCorrupt(BundleLoadException):
    MSG = "flow3r.toml corrupt"


class BundleMetadataBroken(BundleLoadException):
    MSG = "flow3r.toml broken"


class BundleMetadata:
    """
    Collects data from a flow3r.toml-defined 'bundle', eg. a redistribuable app.

    A flow3r.toml file contains the following sections:

       [app]
       # Required, displayed in the menu.
       name = "Name of the application"
       # One of "Apps", "Badge", "Music", "Games", "Media". Picks which menu
       # the bundle's class will be loadable from.
       category = "Apps"

       [entry]
       # Required for app to actually load. Defines the name of the class that
       # will be imported from the __init__.py next to flow3r.toml. The class
       # must inherit from st3m.application.Application.
       class = "DemoApp"

       # Optional, but recommended. Might end up getting displayed somewhere in
       # a distribution web page or in system menus.
       [metadata]
       author = "Hans Acker"
       # A SPDX-compatible license identifier.
       license = "..."
       url = "https://example.com/demoapp"

    This data is used to discover bundles and load them as applications.
    """

    __slots__ = ["path", "name", "menu", "_metadata", "version", "ctx"]

    def __init__(self, path: str, metadata: dict = None) -> None:
        self.path = path.rstrip("/")

        if not metadata:
            self._metadata = load_toml(self.path + "/flow3r.toml")
        else:
            self._metadata = metadata
        self.process_metadata()

    def process_metadata(self):
        if not isinstance(self._metadata.get("app"), dict):
            raise BundleMetadataBroken("missing app section")

        app = self._metadata["app"]
        if not isinstance(app.get("name"), str):
            raise BundleMetadataBroken("missing app.name key")
        self.name = app["name"]
        if not isinstance(app.get("category"), str):
            if not isinstance(app.get("menu"), str):
                raise BundleMetadataBroken("missing app.category key")
            self.menu = app["menu"]
        else:
            self.menu = app["category"]

        version = 0
        if not isinstance(self._metadata.get("metadata"), dict):
            version = self._metadata["metadata"].get("version", 0)
        self.version = version

        self.ctx = ApplicationContext(self.path, self._metadata)

    @staticmethod
    def _sys_path_set(v: List[str]) -> None:
        # Can't just assign to sys.path in Micropython.
        sys.path.clear()
        for el in v:
            sys.path.append(el)

    def _load_class(self, class_entry: str) -> Application:
        # Micropython doesn't have a good importlib-like API for doing dynamic
        # imports of modules at custom paths. That means we have to, for now,
        # resort to good ol' sys.path manipulation.
        #
        # TODO(q3k): extend micropython to make this less messy
        old_sys_path = sys.path[:]

        log.info(f"Loading {self.name} via class entry {class_entry}...")
        containing_path = os.path.dirname(self.path)
        package_name = os.path.basename(self.path)

        if is_simulator():
            # We are in the simulator. Hack around to get this to work.
            prefix = "/flash/sys"
            if containing_path.startswith(prefix):
                containing_path = containing_path.replace(prefix, sys.path[1])
            else:
                containing_path = containing_path.replace("/flash", "/tmp/flow3r-sim")

        new_sys_path = old_sys_path + [containing_path]
        self._sys_path_set(new_sys_path)
        try:
            m = __import__(package_name)
            self._sys_path_set(old_sys_path)
            log.info(f"Loaded {self.name} module: {m}")
            klass = getattr(m, class_entry)
            log.info(f"Loaded {self.name} class: {klass}")
            inst = klass(self.ctx)
            log.info(f"Instantiated {self.name} class: {inst}")
            return inst  # type: ignore
        except Exception as e:
            self._sys_path_set(old_sys_path)
            raise BundleLoadException(f"load error: {e}", e)

    def load(self) -> Application:
        """
        Return Application loaded form this bundle.

        Raises a BundleMetadataException if something goes wrong.
        """
        entry = self._metadata.get("entry", None)
        if entry is None:
            return self._load_class("App")
        if isinstance(entry.get("class"), str):
            class_entry = entry["class"]
            return self._load_class(class_entry)

        raise BundleMetadataBroken("no valid entry method specified")

    def menu_kinds(self) -> List[str]:
        """
        Returns a list of menu kinds this bundle places its entries in.
        """
        return [self.menu]

    def menu_entries(self, kind: str) -> List["MenuItemAppLaunch"]:
        """
        Returns MenuItemAppLauch entries for this bundle for a given menu kind.
        """
        if self.menu != kind:
            return []
        return [MenuItemAppLaunch(self)]

    @property
    def source(self) -> str:
        return os.path.dirname(self.path)

    @property
    def id(self) -> str:
        return os.path.basename(self.path)

    def __repr__(self) -> str:
        return f"<BundleMetadata: {self.id} at {self.path}>"


class LoadErrorView(BaseView):
    def __init__(self, e: BaseException) -> None:
        super().__init__()
        self.e = e
        self.header = "oh no"

        self.lines: List[List[str]] = []

        stringio = io.StringIO()
        sys.print_exception(self.e, stringio)
        msg = stringio.getvalue()

        for line in msg.split("\n"):
            for word in line.split():
                if len(self.lines) == 0:
                    self.lines.append([word])
                    continue
                lastline = self.lines[-1][:]
                lastline.append(word)
                if sum(len(l) for l in lastline) + len(lastline) - 1 > 35:
                    self.lines.append([word])
                else:
                    self.lines[-1].append(word)
            self.lines.append([])

        self.scroll_pos = 0
        self.max_lines = 9
        self.scroll_max = len(self.lines) - self.max_lines

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        self.header = random.choice(
            [
                "oh no",
                "aw shucks",
                "whoopsie",
                "ruh-roh",
                "aw crud",
            ]
        )

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)

        direction = ins.buttons.app

        if direction == ins.buttons.PRESSED_LEFT or ins.captouch.petals[0].pressed:
            self.scroll_pos = max(0, self.scroll_pos - delta_ms / 100)
        elif direction == ins.buttons.PRESSED_RIGHT or ins.captouch.petals[5].pressed:
            self.scroll_pos = min(self.scroll_max, self.scroll_pos + delta_ms / 100)

    def draw(self, ctx: Context) -> None:
        ctx.rgb(0.8, 0.1, 0.1)
        ctx.rectangle(-120, -120, 240, 240)
        ctx.fill()

        ctx.gray(1)
        ctx.font_size = 20
        ctx.font = "Camp Font 1"
        ctx.text_align = ctx.MIDDLE
        ctx.move_to(0, -70)
        ctx.text(self.header)

        ctx.gray(0)
        ctx.rectangle(-120, -60, 240, 240).fill()
        y = -40
        ctx.gray(1)
        ctx.font_size = 15
        ctx.font = "Arimo Regular"
        ctx.text_align = ctx.LEFT

        view_start = max(0, int(self.scroll_pos))
        view_end = min(len(self.lines), view_start + self.max_lines)

        for line in self.lines[view_start:view_end]:
            ctx.move_to(-100, y)
            ctx.text(" ".join(line))
            y += 15

        ctx.font = "Material Icons"
        ctx.text_align = ctx.CENTER

        animation = ((time.ticks_ms() / 69) % 20) - 10
        if animation < 10:
            animation = -animation
        animation *= animation / 10
        animation = 10 - animation

        if view_end < len(self.lines):
            ctx.move_to(0, 120 - animation / 2)
            ctx.text("\ue5db")

        if view_start > 0:
            ctx.move_to(0, -105 + animation / 2)
            ctx.text("\ue5d8")


class MenuItemAppLaunch(MenuItem):
    """
    A MenuItem which launches an app from a BundleMetadata.

    The underlying app class is imported and instantiated on first use.
    """

    def __init__(self, bundle: BundleMetadata):
        self._bundle = bundle
        self._instance: Optional[Application] = None
        self._scroll_pos = 0.0
        self._highlighted = False

    def press(self, vm: Optional[ViewManager]) -> None:
        if vm is None:
            log.warning(f"Could not launch {self.label()} as no ViewManager is present")
            return

        if self._instance is None:
            try:
                self._instance = self._bundle.load()
            except BundleLoadException as e:
                log.error(f"Could not load {self.label()}: {e}")
                if getattr(e, "orig_exc"):
                    e = e.orig_exc
                sys.print_exception(e)
                err = LoadErrorView(e)
                vm.push(err)
                return
        assert self._instance is not None

        setup_for_app(self._bundle.ctx)
        vm.push(self._instance, ViewTransitionSwipeLeft())

    def label(self) -> str:
        return self._bundle.name

    def highlight(self, active: bool) -> None:
        self._highlighted = active
        self._scroll_pos = 0.0

    def draw(self, ctx: Context) -> None:
        ctx.save()
        if self._highlighted and (width := ctx.text_width(self.label())) > 220:
            ctx.translate(sin(self._scroll_pos) * (width - 220) / 2, 0)
        super().draw(ctx)
        ctx.restore()

    def think(self, ins: InputState, delta_ms: int) -> None:
        if self._highlighted:
            self._scroll_pos += delta_ms / 1000


class BundleManager:
    """
    The BundleManager maintains information about BundleMetadata at different
    locations in the badge filesystem.

    It also manages updating/reloading bundles.
    """

    def __init__(self) -> None:
        self.bundles: Dict[str, BundleMetadata] = {}

    @staticmethod
    def _source_trumps(a: str, b: str) -> bool:
        prios = {
            "/flash/sys/apps": 200,
            "/sd/apps": 120,
            "/flash/apps": 100,
        }
        prio_a = prios.get(a, 0)
        prio_b = prios.get(b, 0)
        return prio_a > prio_b

    def _discover_at(self, path: str) -> None:
        path = path.rstrip("/")
        try:
            appdirs = os.listdir(path)
        except Exception as e:
            log.warning(f"Could not discover bundles in {path}: {e}")
            return

        cache_path = path + "/toml_cache.json"

        if not os.path.exists(cache_path):
            toml_cache = {}
        else:
            with open(cache_path) as f:
                toml_cache = json.load(f)

        toml_cache_modified = False

        load_start = time.time_ns()
        for dirname in appdirs:
            dirpath = path + "/" + dirname
            toml_path = dirpath + "/flow3r.toml"
            try:
                toml_stat = os.stat(toml_path)
                if not stat.S_ISREG(toml_stat[0]):
                    continue
            except Exception:
                continue

            if (
                dirpath in toml_cache
                and toml_cache[dirpath].get("_toml_size") == toml_stat[6]
                and toml_cache[dirpath].get("_toml_change") == toml_stat[8]
            ):
                metadata = toml_cache[dirpath]
            else:
                try:
                    metadata = load_toml(toml_path)
                except BundleLoadException as e:
                    log.error(f"Failed to bundle from {dirpath}: {e}")
                    continue
                toml_cache_modified = True
                toml_cache[dirpath] = metadata
                toml_cache[dirpath]["_toml_size"] = toml_stat[6]
                toml_cache[dirpath]["_toml_change"] = toml_stat[8]
                log.info(f"Adding {dirpath} to JSON cache.")

            try:
                bundle = BundleMetadata(dirpath, metadata)
            except BundleLoadException as e:
                log.error(f"Failed to load BundleMetadata: {e}")
                continue

            bundle_name = bundle.name
            if bundle_name not in self.bundles:
                self.bundles[bundle_name] = bundle
                continue
            ex = self.bundles[bundle_name]

            # Do we have a newer version?
            if bundle.version > ex.version:
                self.bundles[bundle_name] = bundle
                continue
            # Do we have a higher priority source?
            if self._source_trumps(bundle.source, ex.source):
                self.bundles[bundle_name] = bundle
                continue
            log.warning(
                f"Ignoring {bundle_name} at {bundle.source} as it already exists at {ex.source}"
            )

        if toml_cache_modified:
            with open(cache_path, "w") as f:
                json.dump(toml_cache, f)
        log.info(f"load time for {path}, {(time.time_ns() - load_start) / 1000000}ms")

    def update(self) -> None:
        self._discover_at("/flash/sys/apps")
        self._discover_at("/flash/apps")
        self._discover_at("/sd/apps")


def load_toml(toml_path):
    if not os.path.exists(toml_path):
        raise BundleMetadataNotFound()

    with open(toml_path) as f:
        try:
            return toml.load(f)
        except toml.TomlDecodeError as e:
            raise BundleMetadataCorrupt(str(e))
        except Exception as e:
            raise BundleMetadataCorrupt(str(e))


def viewmanager_is_in_application(vm):
    """
    Temporary band-aid until the OS can provide this information properly.

    Estimates whether the viewmanager is in an application right now.
    Intended to be used with the viewmanager of the OS menu, otherwise
    probably of limited usefulness and accuracy.

    There's no perfect way to do this as of yet as applications
    can go wild with the vm history. In the wild, false negatives
    may occur, but false positives are unlikely unless somebody is
    actively trying to mess with the OS.
    """
    stack = list(vm._history)
    # the stack of views is technically vm._history.append(vm._incoming).
    # however there is one execution order caveat:
    #
    # we're only using this rn to pop us one-by-one backwards
    # thru the stack until we're outside of any application.
    # the viewmanager doesn't process pop requests upon arrival,
    # but waits until its next think:
    #
    # self._incoming will not be replaced before that, but its planned
    # successor is stored in vm._pending, which is reset to None
    # after it has been processed.
    if vm._pending is None:
        stack += [vm._incoming]
    else:
        stack += [vm._pending]

    for view in stack:
        if isinstance(view, Application):
            return True
    return False
