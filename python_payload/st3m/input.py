from st3m.goose import List, Optional, Enum, Tuple

import sys_buttons
import captouch
import imu
from st3m.power import Power

power = Power()


class IMUState:
    """
    State of the Inertial Measurement Unit

    Acceleration in m/s**2, roation rate in deg/s, pressure in Pascal
    """

    __slots__ = ("acc", "gyro", "pressure")

    def __init__(
        self,
        acc: Tuple[float, float, float],
        gyro: Tuple[float, float, float],
        pressure: float,
    ) -> None:
        self.acc = acc
        self.gyro = gyro
        self.pressure = pressure


class InputButtonState:
    """
    State of the tri-state switches/buttons on the shoulders of the badge.

    If you want to detect edges, use the stateful InputController.

    By default, the left shoulder button is the 'app' button and the right
    shoulder button is the 'os' button. The user can switch this behaviour in
    the settings menu.

    The 'app' button can be freely used by applicaton code. The 'os' menu has
    fixed functions: volume up/down and back.

    In cases you want to access left/right buttons independently of app/os
    mapping (for example in applications where the handedness of the user
    doesn't matter), then you can use _left and _right to access their state
    directly.

    'app_is_left' is provided to let you figure out on which side of the badge
    the app button is, eg. for use when highlighting buttons on the screen or
    with LEDs.
    """

    __slots__ = ("app", "os", "_left", "_right", "app_is_left")

    PRESSED_LEFT = sys_buttons.PRESSED_LEFT
    PRESSED_RIGHT = sys_buttons.PRESSED_RIGHT
    PRESSED_DOWN = sys_buttons.PRESSED_DOWN
    NOT_PRESSED = sys_buttons.NOT_PRESSED

    def __init__(self, app: int, os: int, app_is_left: bool):
        self.app = app
        self.os = os
        self.app_is_left = app_is_left


class InputState:
    """
    Current state of inputs from badge user. Passed via think() to every
    Responder.

    If you want to detect edges, use the stateful InputController.
    """

    def __init__(self) -> None:
        self._captouch = None
        self._buttons = None
        self._imu = None
        self._temperature = None
        self._battery_voltage = None
        self._pressure = None

    @property
    def captouch(self):
        if self._captouch is None:
            self._captouch = captouch.read()
        return self._captouch

    @property
    def buttons(self):
        if self._buttons is None:
            app = sys_buttons.get_app()
            os = sys_buttons.get_os()
            app_is_left = sys_buttons.app_is_left()
            self._buttons = InputButtonState(app, os, app_is_left)
        return self._buttons

    @property
    def imu(self):
        if self._imu is None:
            acc = imu.acc_read()
            gyro = imu.gyro_read()
            if self._pressure is None:
                self._pressure, self._temperature = imu.pressure_read()
            self._imu = IMUState(acc, gyro, self._pressure)
        return self._imu

    @property
    def battery_voltage(self):
        if self._battery_voltage is None:
            self._battery_voltage = power.battery_voltage
        return self._battery_voltage

    @property
    def temperature(self):
        if self._temperature is None:
            self._pressure, self._temperature = imu.pressure_read()
        return self._temperature


class RepeatSettings:
    def __init__(self, first: float, subsequent: float) -> None:
        self.first = first
        self.subsequent = subsequent


class PressableState(Enum):
    PRESSED = "pressed"
    REPEATED = "repeated"
    RELEASED = "released"
    DOWN = "down"
    UP = "up"


class Pressable:
    """
    A pressable button or button-acting object (like captouch petal in button
    mode).

    Carries information about current and previous state of button, allowing to
    detect edges (pressed/released) and state (down/up). Additionally implements
    button repeating.
    """

    PRESSED = PressableState.PRESSED
    REPEATED = PressableState.REPEATED
    RELEASED = PressableState.RELEASED
    DOWN = PressableState.DOWN
    UP = PressableState.UP

    def __init__(self, state: bool) -> None:
        self._state = state
        self._prev_state = state
        self._repeat: Optional[RepeatSettings] = RepeatSettings(400, 200)

        self._pressed_at: Optional[float] = None
        self._repeating = False
        self._repeated = False

        self._ignoring = 0

    def repeat_enable(self, first: int = 400, subsequent: int = 200) -> None:
        """
        Enable key repeat functionality. Arguments are amount to wait in ms
        until first repeat is emitted and until subsequent repeats are emitted.

        Repeat is enabled by default on Pressables.
        """
        self._repeat = RepeatSettings(first, subsequent)

    def repeat_disable(self) -> None:
        """
        Disable repeat functionality on this Pressable.
        """
        self._repeat = None

    def _update(self, ts: int, state: bool) -> None:
        if self._ignoring > 0:
            self._ignoring -= 1

        self._prev_state = self._state
        self._state = state
        self._repeated = False

        if state == False:
            self._pressed_at = None
            self._repeating = False
        else:
            if self._pressed_at is None:
                self._pressed_at = ts

        repeat = self._repeat
        if state and repeat is not None and self._pressed_at is not None:
            if not self._repeating:
                if ts > self._pressed_at + repeat.first:
                    self._repeating = True
                    self._repeated = True
                    self._prev_state = False
                    self._pressed_at = ts
            else:
                if ts > self._pressed_at + repeat.subsequent:
                    self._prev_state = False
                    self._pressed_at = ts
                    self._repeated = True

    @property
    def state(self) -> PressableState:
        """
        Returns one of PressableState.{UP,DOWN,PRESSED,RELEASED,REPEATED}.
        """
        prev = self._prev_state
        cur = self._state

        if self._ignoring > 0:
            return self.UP

        if self._repeated:
            return self.REPEATED

        if cur and not prev:
            return self.PRESSED
        if not cur and prev:
            return self.RELEASED
        if cur and prev:
            return self.DOWN
        return self.UP

    @property
    def pressed(self) -> bool:
        """
        True if the button has just been pressed.
        """
        return self.state == self.PRESSED

    @property
    def repeated(self) -> bool:
        """
        True if the button has been held long enough that a virtual 'repeat'
        press should be acted upon.
        """
        return self.state == self.REPEATED

    @property
    def released(self) -> bool:
        """
        True if the button has just been released.
        """
        return self.state == self.RELEASED

    @property
    def down(self) -> bool:
        """
        True if the button is held down, after first being pressed.
        """
        return self.state in (self.DOWN, self.REPEATED)

    @property
    def up(self) -> bool:
        """
        True if the button is currently not being held down.
        """
        return self.state == self.UP

    def _ignore_pressed(self) -> None:
        """
        Pretend the button isn't being pressed for the next two update
        iterations. Used to prevent spurious presses to be routed to apps that
        have just been foregrounded.
        """
        self._ignoring = 2
        self._repeating = False
        self._repeated = False

    def __repr__(self) -> str:
        return "<Pressable: " + str(self.state) + ">"


class TouchableState(Enum):
    UP = "up"
    BEGIN = "begin"
    RESTING = "resting"
    MOVED = "moved"
    ENDED = "ended"


class Touchable:
    """
    A Touchable processes incoming captouch positional state into higher-level
    simple gestures.

    The Touchable can be in one of four states:

        UP: not currently being interacted with
        BEGIN: some gesture has just started
        MOVED: a gesture is continuing
        ENDED: a gesture has just ended

    The state can be retrieved by calling phase().

    The main API for consumers is current_gesture(), which returns a
    Touchable.Gesture defining the current state of the gesture, from the
    beginning of the touch event up until now (or until the end, if the current
    phase is ENDED).

    Under the hood, the Touchable keeps a log of recent samples from the
    captouch petal position, and processes them to eliminate initial noise from
    the beginning of a gesture.

    All positional output state is the same format/range as in the low-level
    CaptouchState.
    """

    UP = TouchableState.UP
    BEGIN = TouchableState.BEGIN
    MOVED = TouchableState.MOVED
    ENDED = TouchableState.ENDED

    class Gesture:
        """
        A simple captouch gesture, currently definined as a movement between two
        points: the beginning of the gesture (when the user touched the petal)
        and to the current state. If the gesture is still active, the current
        state is averaged/filtered to reduce noise. If the gesture has ended,
        the current state is the last measured position.
        """

        def __init__(self, dis, vel):
            self._dis = tuple([x * 35000 for x in dis])
            self._vel = tuple([x * 35000 for x in vel])

        @property
        def distance(self) -> Tuple[float, float]:
            """
            Distance traveled by this gesture.
            """
            return self._dis

        @property
        def velocity(self) -> Tuple[float, float]:
            """
            Velocity vector of this gesture.
            """
            return self._vel

    def __init__(self, pos: tuple[float, float] = (0.0, 0.0)) -> None:
        # What the beginning of the gesture is defined as. This is ampled a few
        # entries into the log as the initial press stabilizes.
        self._start: Optional[Touchable.Entry] = None

        # Current and previous 'pressed' state from the petal, used to begin
        # gesture tracking.
        self._pressed = False
        self._prev_pressed = self._pressed

        self._dis = None
        self._vel = None
        self._ref_start = None

        self._state = self.UP

    def _get_data(self, petal, smooth=2, drop_first=0, drop_last=1):
        """
        Append an Entry to the log based on a given CaptouchPetalState.
        """
        rad = petal.get_rad(smooth=smooth, drop_first=drop_first, drop_last=drop_last)
        phi = petal.get_phi(smooth=smooth, drop_first=drop_first, drop_last=drop_last)
        if rad is None:
            return None
        if phi is None:
            phi = 0
        return (rad, phi)

    def _update(self, ts: int, petal: captouch.CaptouchPetalState) -> None:
        """
        Called when the Touchable is being processed by an InputController.
        """
        self._last_ts = ts
        self._prev_pressed = self._pressed
        self._pressed = petal.pressed

        if not self._pressed:
            if not self._prev_pressed:
                self._state = self.UP
                self._start = None
                self._ref_start = None
                self._dis = None
                self._vel = None
            else:
                self._state = self.ENDED
                rad, phi = petal.get_rad_raw(), petal.get_phi_raw()
                start = 0
                while rad[start] is None:
                    start += 1
                num = 1
                while ((start + num) < len(rad)) and (rad[start + num] is not None):
                    num += 1
                if num > 1:
                    # if num > 2:
                    #    start += 1
                    #    num -= 1
                    print("\nNEW ESCAPE!!")
                    lines = [""] * 11
                    head_line = "rad" + (num + 1) * " " + "phi"

                    print_this = rad[start : start + num]
                    min_print = min(print_this)
                    max_print = max(print_this)
                    print_range = 10 / (max_print - min_print)
                    x = [int((p - min_print) * print_range) for p in print_this]
                    for j in range(11):
                        line = "|"
                        for i in range(num):
                            if x[i] == j:
                                line += "X"
                            else:
                                line += "."
                        line += "|  "
                        lines[j] += line

                    print_this = phi[start : start + num]
                    min_print = min(print_this)
                    max_print = max(print_this)
                    print_range = 10 / (max_print - min_print)
                    x = [int((p - min_print) * print_range) for p in print_this]

                    for j in range(11):
                        line = "|"
                        for i in range(num):
                            if x[i] == j:
                                line += "X"
                            else:
                                line += "."
                        line += "|  "
                        lines[j] += line

                    for j in range(11):
                        print(lines[10 - j])

                    if num > 4:
                        num = 4
                    rad = rad[start : start + num]
                    phi = phi[start : start + num]
                    # linear regression, least squares
                    x = [-0.018 * x for x in range(num)]
                    sum_x = sum(x)
                    div = (num * sum([_x * _x for _x in x])) - sum_x * sum_x

                    y = rad
                    k = (num * sum([x[i] * y[i] for i in range(num)])) - sum_x * sum(y)
                    rad_vel = k / div

                    y = phi
                    k = (num * sum([x[i] * y[i] for i in range(num)])) - sum_x * sum(y)
                    phi_vel = k / div

                    lin_reg = (rad_vel, phi_vel)
                    print(f"linreg{num}: {lin_reg}")
                    self._vel = lin_reg
            return

        if self._start is None:
            self._start = not None  # :3
            self._state = self.BEGIN
        else:
            self._state = self.MOVED

        if self._ref_start is None:
            self._ref_start = self._get_data(petal, drop_first=1, drop_last=1)
        else:
            data = self._get_data(petal, drop_last=1)
            if data is not None:
                self._dis = [data[x] - self._ref_start[x] for x in range(2)]

        if self._ref_start is None:
            swipe_drop_last = 0
            swipe_smooth = 0
        else:
            swipe_drop_last = 2
            swipe_smooth = 2
        data_now = self._get_data(petal, smooth=swipe_smooth, drop_last=swipe_drop_last)
        data_prev = self._get_data(
            petal, smooth=swipe_smooth, drop_last=swipe_drop_last + 1
        )
        if data_now is not None and data_prev is not None:
            # hardcoded driver cycle time of 18ms for now. not pretty but
            # accurate for now.
            self._vel = [(data_now[x] - data_prev[x]) / 0.018 for x in range(2)]

    def phase(self) -> TouchableState:
        """
        Returns the current phase of a gesture as tracked by this Touchable (petal).
        """
        return self._state

    def current_gesture(self) -> Optional[Gesture]:
        if self._start is None:
            return None
        params = [self._dis, self._vel]
        for x, p in enumerate(params):
            if p is None:
                p = (0, 0)
            else:
                p = tuple(p)
            params[x] = p
        return self.Gesture(*params)


class PetalState:
    def __init__(self, ix: int) -> None:
        self.ix = ix
        self._whole = Pressable(False)
        self._gesture = Touchable()
        self._whole_updated = False
        self._gesture_updated = False
        self._ts = None
        self._petal = None

    def _update(self, ts: int, petal: captouch.CaptouchPetalState) -> None:
        self._ts = ts
        self._petal = petal
        self._whole_updated = False
        self._gesture_updated = False

    @property
    def whole(self):
        if self._petal and not self._whole_updated:
            self._whole._update(self._ts, self._petal.pressed)
            self._whole_updated = True
        return self._whole

    @property
    def pressure(self):
        if not self._petal:
            return 0
        return self._petal.pressure

    @property
    def gesture(self):
        if self._petal and not self._gesture_updated:
            self._gesture._update(self._ts, self._petal)
            self._gesture_updated = True
        return self._gesture


class CaptouchState:
    """
    State of capacitive touch petals.

    The petals are indexed from 0 to 9 (inclusive). Petal 0 is above the USB-C
    socket, then the numbering continues clockwise.
    """

    def __init__(self) -> None:
        self._petals = [PetalState(i) for i in range(10)]
        self._ins = None
        self._ts = None
        self._updated = False

    def _update(self, ts: int, ins: InputState) -> None:
        self._ins = ins
        self._ts = ts
        self._updated = False

    @property
    def petals(self):
        if self._ins and not self._updated:
            for i, petal in enumerate(self._petals):
                petal._update(self._ts, self._ins.captouch.petals[i])
            self._updated = True
        return self._petals

    def _ignore_pressed(self) -> None:
        for petal in self._petals:
            petal.whole._ignore_pressed()


class TriSwitchState:
    """
    State of a tri-stat shoulder button
    """

    __slots__ = ("left", "middle", "right")

    def __init__(self) -> None:
        self.left = Pressable(False)
        self.middle = Pressable(False)
        self.right = Pressable(False)

    def _update(self, ts: int, st: int) -> None:
        self.left._update(ts, st == -1)
        self.middle._update(ts, st == 2)
        self.right._update(ts, st == 1)

    def _ignore_pressed(self) -> None:
        self.left._ignore_pressed()
        self.middle._ignore_pressed()
        self.right._ignore_pressed()


class ButtonsState:
    """
    Edge-trigger detection for input button state.

    See  InputButtonState for more information about the meaning of app, os,
    _left, _right and app_is_left.
    """

    __slots__ = ("app", "os", "_left", "_right", "app_is_left", "_app_is_left_prev")

    def __init__(self) -> None:
        self.app = TriSwitchState()
        self.os = TriSwitchState()

        # Defaults. Real data coming from _update will change this to the
        # correct values from an InputState.
        self._left = self.app
        self._right = self.os
        self.app_is_left = True
        self._app_is_left_prev = self.app_is_left

    def _update(self, ts: int, hr: InputState) -> None:
        # Check whether we swapped left/right buttons. If so, carry over changes
        # from buttons as mapped previously, otherwise we get spurious presses.
        self.app_is_left = hr.buttons.app_is_left
        if self._app_is_left_prev != self.app_is_left:
            # BUG(q3k): if something is holding on to controller button
            # references, then this will break their code.
            self.app, self.os = self.os, self.app

        self.app._update(ts, hr.buttons.app)
        self.os._update(ts, hr.buttons.os)
        self._app_is_left_prev = self.app_is_left

        if self.app_is_left:
            self._left = self.app
            self._right = self.os
        else:
            self._left = self.os
            self._right = self.app

    def _ignore_pressed(self) -> None:
        self.app._ignore_pressed()
        self.os._ignore_pressed()


class InputController:
    """
    A stateful input controller. It accepts InputState updates from the Reactor
    and allows a Responder to detect input events, like a button having just
    been pressed.

    To use, instantiate within a Responder and call think() from your
    responder's think().

    Then, access the captouch/left_shoulder/right_shoulder fields.
    """

    __slots__ = (
        "captouch",
        "buttons",
        "_ts",
    )

    def __init__(self) -> None:
        self.captouch = CaptouchState()
        self.buttons = ButtonsState()
        self._ts = 0

    def think(self, hr: InputState, delta_ms: int) -> None:
        self._ts += delta_ms
        self.captouch._update(self._ts, hr)
        self.buttons._update(self._ts, hr)

    def _ignore_pressed(self) -> None:
        """
        Pretend input buttons aren't being pressed for the next two update
        iterations. Used to prevent spurious presses to be routed to apps that
        have just been foregrounded.
        """
        self.captouch._ignore_pressed()
        self.buttons._ignore_pressed()
