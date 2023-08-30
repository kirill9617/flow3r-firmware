"""
Settings framework for flow3r badge.

We call settings 'tunables', trying to emphasize that they are some kind of
value that can be changed.

Settings are persisted in /flash/settings.json, loaded on startup and saved on
request.
"""

import json

from st3m import InputState, Responder, logging
from st3m.goose import (
    ABCBase,
    abstractmethod,
    Any,
    Dict,
    List,
    Optional,
    Callable,
)
from st3m.ui.view import ViewManager
from st3m.utils import lerp, ease_out_cubic, reduce
from ctx import Context

log = logging.Log(__name__, level=logging.INFO)


class Tunable(ABCBase):
    """
    Base class for all settings. An instance of a Tunable is some kind of
    setting with some kind of value. Each setting has exactly one instance of
    Tunable in memory that represents its current configuration.

    Other than a common interface, this also implements a mechanism for
    downstream consumers to subscribe to tunable changes, and allows notifying
    them.
    """

    def __init__(self) -> None:
        self._subscribers: List[Callable[[], None]] = []

    def subscribe(self, s: Callable[[], None]) -> None:
        """
        Subscribe to be updated when this tunable value's changes.
        """
        self._subscribers.append(s)

    def notify(self) -> None:
        """
        Notify all subscribers.
        """
        for s in self._subscribers:
            s()

    @abstractmethod
    def name(self) -> str:
        """
        Human-readable name of this setting.
        """
        ...

    @abstractmethod
    def get_widget(self) -> "TunableWidget":
        """
        Widget that will be used to render this setting in menus.
        """
        ...

    @abstractmethod
    def save(self) -> Dict[str, Any]:
        """
        Return dictionary that contains this setting's persistance data. Will be
        merged with all other tunable's results.
        """
        ...

    @abstractmethod
    def load(self, d: Dict[str, Any]) -> None:
        """
        Load in-memory state from persisted data.
        """
        ...


class TunableWidget(Responder):
    """
    A tunable's widget as rendered in menus.
    """

    @abstractmethod
    def press(self, vm: Optional[ViewManager]) -> None:
        """
        Called when the menu item is 'pressed', ie. selected/activated. A widget
        should react to this as the primary way to let the users manipulate the
        value of the tunable from a menu.
        """
        ...


class UnaryTunable(Tunable):
    """
    Basic implementation of a Tunable for single values. Most settings will be
    UnaryTunables, with notable exceptions being things like lists or optional
    settings.

    UnaryTunable implements persistence by always being saved/loaded to same
    json.style.path (only traversing nested dictionaries).
    """

    def __init__(self, name: str, key: str, default: Any):
        """
        Create an UnaryTunable with a given human-readable name, some
        persistence key and some default value.
        """
        super().__init__()
        self.key = key
        self._name = name
        self.value: Any = default

    def name(self) -> str:
        return self._name

    def set_value(self, v: Any) -> None:
        """
        Call to set value in-memory and notify all listeners.
        """
        self.value = v
        self.notify()

    def save(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        sub = res

        parts = self.key.split(".")
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                sub[part] = self.value
            else:
                sub[part] = {}
                sub = sub[part]
        return res

    def load(self, d: Dict[str, Any]) -> None:
        def _get(v: Dict[str, Any], k: str) -> Any:
            if k in v:
                return v[k]
            else:
                return {}

        path = self.key.split(".")
        k = path[-1]
        d = reduce(_get, path[:-1], d)
        if k in d:
            self.value = d[k]


class OnOffTunable(UnaryTunable):
    """
    OnOffTunable is a UnaryTunable that has two values: on or off, and is
    rendered accordingly as a slider switch.
    """

    def __init__(self, name: str, key: str, default: bool) -> None:
        super().__init__(name, key, default)

    def get_widget(self) -> TunableWidget:
        return OnOffWidget(self)

    def press(self, vm: Optional[ViewManager]) -> None:
        if self.value == True:
            self.set_value(False)
        else:
            self.set_value(True)


class OnOffWidget(TunableWidget):
    """
    OnOffWidget is a TunableWidget for OnOffTunables. It renders a slider
    switch.
    """

    def __init__(self, tunable: "OnOffTunable") -> None:
        self._tunable = tunable

        # Value from 0 to animation_duration indicating animation progress
        # (starts at animation_duration, ends at 0).
        self._animating: float = 0

        # Last and previous read value from tunable.
        self._state = tunable.value == True
        self._prev_state = self._state

        # Value from 0 to 1, representing desired animation position. Linear
        # between both. 1 represents rendering _state, 0 represents render the
        # opposite of _state.
        self._progress = 1.0

    def think(self, ins: InputState, delta_ms: int) -> None:
        animation_duration = 0.2

        self._state = self._tunable.value == True

        if self._prev_state != self._state:
            # State switched.

            # Start new animation, making sure to take into consideration
            # whatever animation is already taking place.
            self._animating = animation_duration - self._animating
        else:
            # Continue animation.
            self._animating -= delta_ms / 1000
            if self._animating < 0:
                self._animating = 0

        # Calculate progress value.
        self._progress = 1.0 - (self._animating / animation_duration)
        self._prev_state = self._state

    def draw(self, ctx: Context) -> None:
        value = self._state
        v = self._progress
        v = ease_out_cubic(v)
        if not value:
            v = 1.0 - v

        ctx.rgb(lerp(0, 0.4, v), lerp(0, 0.6, v), lerp(0, 0.4, v))

        ctx.round_rectangle(0, -10, 40, 20, 5)
        ctx.line_width = 2
        ctx.fill()

        ctx.round_rectangle(0, -10, 40, 20, 5)
        ctx.line_width = 2
        ctx.gray(lerp(0.3, 1, v))
        ctx.stroke()

        ctx.gray(1)
        ctx.round_rectangle(lerp(2, 22, v), -8, 16, 16, 5)
        ctx.fill()

    def press(self, vm: Optional[ViewManager]) -> None:
        self._tunable.set_value(not self._state)


class StringTunable(UnaryTunable):
    """
    StringTunable is a UnaryTunable that has a string value
    """

    def __init__(self, name: str, key: str, default: Optional[str]) -> None:
        super().__init__(name, key, default)

    def get_widget(self) -> TunableWidget:
        return StringWidget(self)

    def press(self, vm: Optional[ViewManager]) -> None:
        # Text input not supported at the moment
        pass


class StringWidget(TunableWidget):
    """
    StringWidget is a TunableWidget for StringTunables. It renders a string.
    """

    def __init__(self, tunable: StringTunable) -> None:
        self._tunable = tunable

    def think(self, ins: InputState, delta_ms: int) -> None:
        # Nothing to do here
        pass

    def draw(self, ctx: Context) -> None:
        ctx.text_align = ctx.LEFT
        ctx.text(str(self._tunable.value) if self._tunable.value else "")

    def press(self, vm: Optional[ViewManager]) -> None:
        # Text input not supported at the moment
        pass


# TODO: invert Tunable <-> Widget dependency to be able to define multiple different widget renderings for the same underlying tunable type
class ObfuscatedStringTunable(UnaryTunable):
    """
    ObfuscatedStringTunable is a UnaryTunable that has a string value that should not be revealed openly.
    """

    def __init__(self, name: str, key: str, default: Optional[str]) -> None:
        super().__init__(name, key, default)

    def get_widget(self) -> TunableWidget:
        return ObfuscatedValueWidget(self)

    def press(self, vm: Optional[ViewManager]) -> None:
        # Text input not supported at the moment
        pass


class ObfuscatedValueWidget(TunableWidget):
    """
    ObfuscatedValueWidget is a TunableWidget for UnaryTunables. It renders three asterisks when the tunable contains a truthy value, otherwise nothing.
    """

    def __init__(self, tunable: UnaryTunable) -> None:
        self._tunable = tunable

    def think(self, ins: InputState, delta_ms: int) -> None:
        # Nothing to do here
        pass

    def draw(self, ctx: Context) -> None:
        ctx.text_align = ctx.LEFT
        if self._tunable.value:
            ctx.text("***")

    def press(self, vm: Optional[ViewManager]) -> None:
        # Text input not supported at the moment
        pass


# Actual tunables / settings.
onoff_button_swap = OnOffTunable("Swap Buttons", "system.swap_buttons", False)
onoff_show_fps = OnOffTunable("Show FPS", "system.show_fps", False)
onoff_debug = OnOffTunable("Debug Overlay", "system.debug", False)
onoff_debug_touch = OnOffTunable("Touch Overlay", "system.debug_touch", False)
onoff_show_tray = OnOffTunable("Show Icons", "system.show_icons", True)
onoff_wifi = OnOffTunable("Enable WiFi on Boot", "system.wifi.enabled", False)
onoff_wifi_preference = OnOffTunable(
    "Let apps change WiFi", "system.wifi.allow_apps_to_change_wifi", True
)
str_wifi_ssid = StringTunable("WiFi SSID", "system.wifi.ssid", "Camp2023-open")
str_wifi_psk = ObfuscatedStringTunable("WiFi Password", "system.wifi.psk", None)
str_hostname = StringTunable("Hostname", "system.hostname", "flow3r")
str_auto_boot_app = StringTunable("Auto Boot App", "system.auto_boot_app", None)

# List of all settings to be loaded/saved
load_save_settings: List[UnaryTunable] = [
    onoff_show_tray,
    onoff_button_swap,
    onoff_debug,
    onoff_debug_touch,
    onoff_wifi,
    onoff_wifi_preference,
    onoff_show_fps,
    str_wifi_ssid,
    str_wifi_psk,
    str_hostname,
    str_auto_boot_app,
]


def load_all() -> None:
    """
    Load all settings from flash.
    """
    global settings_loaded
    data = {}
    try:
        with open("/flash/settings.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        log.warning("Could not load settings: " + str(e))
        return

    log.info("Loaded settings from flash")
    for setting in load_save_settings:
        setting.load(data)


def _update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursive update dictionary.
    """
    for k, v in u.items():
        if type(v) == type({}):
            d[k] = _update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def save_all() -> None:
    """
    Save all settings to flash.
    """
    res: Dict[str, Any] = {}
    for setting in load_save_settings:
        res = _update(res, setting.save())
    try:
        with open("/flash/settings.json", "w") as f:
            json.dump(res, f)
    except Exception as e:
        log.warning("Could not save settings: " + str(e))
        return

    log.info("Saved settings to flash")


load_all()
